"""Shared helpers for CRUCIBLE collectors.

Collectors gather FACTS only. They never decide what is a defect -- that is an
agent's job (Axiom 4). Everything here must be deterministic: same input, same
bytes out, so the fix loop can diff two runs and prove it did no harm.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


# --------------------------------------------------------------------------
# comment handling
# --------------------------------------------------------------------------

def strip_comment(line: str) -> tuple[str, str]:
    """Split a TeX line into (code, comment).

    A '%' escaped as '\\%' is literal. A '%' preceded by an even number of
    backslashes starts a comment.
    """
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "%":
            bs = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                return line[:i], line[i:]
        i += 1
    return line, ""


VERBATIM_ENVS = {"verbatim", "lstlisting", "minted", "Verbatim", "alltt"}


# --------------------------------------------------------------------------
# flattened document model
# --------------------------------------------------------------------------

@dataclass
class Line:
    """One source line, after \\input resolution and comment stripping."""
    vline: int          # 1-based index into the flattened document
    file: str           # repo-relative path
    lineno: int         # 1-based line number inside that file
    code: str           # comment-stripped text
    comment: str        # the stripped comment, kept for TODO/FIXME scanning
    raw: str            # original untouched line
    in_verbatim: bool = False

    def loc(self) -> str:
        return f"{self.file}:{self.lineno}"


@dataclass
class Doc:
    """A flattened LaTeX document plus the repo it came from."""
    root: str
    repo: str
    lines: list[Line] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    missing_inputs: list[dict] = field(default_factory=list)
    empty_inputs: list[dict] = field(default_factory=list)

    def text(self) -> str:
        return "\n".join(l.code for l in self.lines)

    def at(self, vline: int) -> Line | None:
        idx = vline - 1
        return self.lines[idx] if 0 <= idx < len(self.lines) else None

    def find_all(self, pattern: str, flags=0, skip_verbatim=True):
        """Yield (Line, re.Match) for every match, line by line."""
        rx = re.compile(pattern, flags)
        for l in self.lines:
            if skip_verbatim and l.in_verbatim:
                continue
            for m in rx.finditer(l.code):
                yield l, m


INPUT_RX = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")


def _resolve_tex(repo: Path, name: str, relative_to: Path) -> Path | None:
    name = name.strip()
    cands = []
    for base in (relative_to.parent, repo):
        cands.append(base / name)
        if not name.endswith(".tex"):
            cands.append(base / (name + ".tex"))
    for c in cands:
        if c.is_file():
            return c
    return None


def flatten(root_tex: Path, repo: Path, _seen: set | None = None,
            _doc: Doc | None = None) -> Doc:
    """Resolve \\input/\\include recursively into one flat line list."""
    if _doc is None:
        _doc = Doc(root=str(root_tex.relative_to(repo)), repo=str(repo))
    if _seen is None:
        _seen = set()

    key = str(root_tex.resolve())
    if key in _seen:
        return _doc
    _seen.add(key)

    rel = str(root_tex.relative_to(repo))
    _doc.files.append(rel)

    try:
        raw_lines = root_tex.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return _doc

    verb_env = None
    for i, raw in enumerate(raw_lines, start=1):
        code, comment = strip_comment(raw)

        # track verbatim regions so we never lint code samples as prose
        if verb_env is None:
            mb = re.search(r"\\begin\{(" + "|".join(VERBATIM_ENVS) + r")\}", code)
            if mb:
                verb_env = mb.group(1)
        else:
            me = re.search(r"\\end\{" + re.escape(verb_env) + r"\}", code)
            if me:
                verb_env = None

        _doc.lines.append(Line(
            vline=len(_doc.lines) + 1, file=rel, lineno=i,
            code=code, comment=comment, raw=raw,
            in_verbatim=verb_env is not None,
        ))

        if verb_env is not None:
            continue

        for m in INPUT_RX.finditer(code):
            child = _resolve_tex(repo, m.group(1), root_tex)
            if child is None:
                _doc.missing_inputs.append(
                    {"file": rel, "line": i, "target": m.group(1)})
                continue
            # an included file that renders to nothing is a real defect (S4.1)
            body = child.read_text(encoding="utf-8", errors="replace")
            substantive = [
                ln for ln in body.splitlines()
                if strip_comment(ln)[0].strip()
            ]
            if not substantive:
                _doc.empty_inputs.append({
                    "file": rel, "line": i,
                    "target": str(child.relative_to(repo)),
                    "bytes": len(body),
                })
            flatten(child, repo, _seen, _doc)

    return _doc


# --------------------------------------------------------------------------
# brace matching
# --------------------------------------------------------------------------

def match_braces(s: str, start: int) -> int:
    """Given index of '{', return index just past its matching '}' (or -1)."""
    if start >= len(s) or s[start] != "{":
        return -1
    depth = 0
    i = start
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def arg_after(s: str, cmd_end: int) -> tuple[str, int]:
    """Read a {...} argument starting at/after cmd_end. Returns (body, end)."""
    i = cmd_end
    while i < len(s) and s[i] in " \t":
        i += 1
    if i < len(s) and s[i] == "[":
        j = s.find("]", i)
        if j != -1:
            i = j + 1
        while i < len(s) and s[i] in " \t":
            i += 1
    if i >= len(s) or s[i] != "{":
        return "", cmd_end
    end = match_braces(s, i)
    if end == -1:
        return "", cmd_end
    return s[i + 1:end - 1], end


# --------------------------------------------------------------------------
# environment blocks spanning multiple lines
# --------------------------------------------------------------------------

@dataclass
class Block:
    env: str
    start_vline: int
    end_vline: int
    body: str
    file: str
    start_line: int


def find_blocks(doc: Doc, envs: set[str]) -> list[Block]:
    """Find \\begin{env}...\\end{env} blocks, handling nesting of same env."""
    out: list[Block] = []
    stack: list[tuple[str, int, int, str]] = []
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in re.finditer(r"\\(begin|end)\s*\{([^}]*)\}", l.code):
            kind, env = m.group(1), m.group(2).rstrip("*")
            if env not in envs:
                continue
            if kind == "begin":
                stack.append((env, l.vline, l.lineno, l.file))
            else:
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == env:
                        e, sv, sl, sf = stack.pop(k)
                        body = "\n".join(
                            doc.lines[i].code
                            for i in range(sv - 1, min(l.vline, len(doc.lines)))
                        )
                        out.append(Block(env=e, start_vline=sv, end_vline=l.vline,
                                         body=body, file=sf, start_line=sl))
                        break
    out.sort(key=lambda b: b.start_vline)
    return out


# --------------------------------------------------------------------------
# macro expansion (single-level, for \system{} style aliases)
# --------------------------------------------------------------------------

NEWCOMMAND_RX = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\s*\*?\s*\{?\\([A-Za-z@]+)\}?\s*(?:\[(\d+)\])?")


def collect_macros(doc: Doc) -> dict[str, str]:
    """Map zero-argument macro name -> its literal expansion."""
    macros: dict[str, str] = {}
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in NEWCOMMAND_RX.finditer(l.code):
            name, nargs = m.group(1), m.group(2)
            if nargs:
                continue
            body, _ = arg_after(l.code, m.end())
            if body:
                macros[name] = body
    return macros


# Symbols that carry meaning in result tables. Reducing \ding{55} to bare "55"
# would inject a phantom number 55 into the numeric ledger, so these are mapped
# to real glyphs before any numeric parsing happens.
DING_MAP = {
    "51": "\u2713", "52": "\u2714", "53": "\u2717", "55": "\u2717",
    "56": "\u2718", "54": "\u2718",
}

# \cmd{keep}{...} -> keep the semantically meaningful argument
UNWRAP_LAST = ["textbf", "textit", "emph", "mathbf", "underline", "texttt",
               "textsc", "text", "mathrm", "textrm", "boldsymbol"]
UNWRAP_SECOND = ["textcolor", "colorbox"]   # \textcolor{red}{X} -> X


def latex_to_plain(s: str, depth: int = 4) -> str:
    """Reduce formatting macros to the text they render, keeping content."""
    s = re.sub(r"\\ding\s*\{(\d+)\}",
               lambda m: DING_MAP.get(m.group(1), "\u25a0"), s)
    s = re.sub(r"\\(?:checkmark|cmark)\b", "\u2713", s)
    s = re.sub(r"\\(?:xmark|ding55)\b", "\u2717", s)

    for _ in range(depth):
        before = s
        for cmd in UNWRAP_SECOND:
            m = re.search(r"\\" + cmd + r"\s*(\[[^\]]*\])?\s*\{", s)
            if m:
                _, after_first = arg_after(s, m.end() - 1)
                body, end = arg_after(s, after_first)
                if end > after_first:
                    s = s[:m.start()] + body + s[end:]
        for cmd in UNWRAP_LAST:
            m = re.search(r"\\" + cmd + r"\s*\{", s)
            if m:
                body, end = arg_after(s, m.end() - 1)
                if end > m.end() - 1:
                    s = s[:m.start()] + body + s[end:]
        if s == before:
            break
    return s


def demacro(s: str, macros: dict[str, str], depth: int = 3) -> str:
    """Expand zero-arg macros so prose and table checks see rendered content."""
    for _ in range(depth):
        before = s
        for name, body in macros.items():
            plain = latex_to_plain(body)
            plain = re.sub(r"\\[a-zA-Z]+\s*", "", plain)
            plain = plain.replace("{", "").replace("}", "").strip()
            if not plain:
                continue
            s = re.sub(r"\\" + re.escape(name) + r"(\{\}|\b)", plain, s)
        if s == before:
            break
    return latex_to_plain(s)


# --------------------------------------------------------------------------
# prose extraction
# --------------------------------------------------------------------------

MATH_PATTERNS = [
    (r"\$\$.*?\$\$", " "),
    (r"\\\[.*?\\\]", " "),
    (r"\$[^$]*\$", " "),
    (r"\\\(.*?\\\)", " "),
]

DROP_ARG_CMDS = [
    "cite", "citep", "citet", "citealp", "citeauthor", "citeyear", "nocite",
    "ref", "cref", "Cref", "autoref", "eqref", "pageref", "label",
    "includegraphics", "input", "include", "bibliography", "bibliographystyle",
    "usepackage", "documentclass", "url", "href", "path", "verb",
    "newcommand", "renewcommand", "providecommand", "DeclareMathOperator",
    "graphicspath", "setlength", "vspace", "hspace", "addtolength",
]


def to_prose(text: str) -> str:
    """Strip math, macros, and citation keys so only readable words remain."""
    s = text
    for pat, rep in MATH_PATTERNS:
        s = re.sub(pat, rep, s, flags=re.DOTALL)
    for env in ("equation", "align", "gather", "eqnarray", "multline",
                "tabular", "tabularx", "tabular*", "array"):
        s = re.sub(r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}",
                   " ", s, flags=re.DOTALL)
    for cmd in DROP_ARG_CMDS:
        s = re.sub(r"\\" + cmd + r"\s*\*?\s*(\[[^\]]*\])?\s*\{[^{}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z@]+\s*\*?", " ", s)
    s = re.sub(r"[{}~^_&]", " ", s)
    s = re.sub(r"\\\\", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False,
                               sort_keys=False, default=str), encoding="utf-8")


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_repo_and_root(target: str) -> tuple[Path, Path]:
    """Accept a repo dir or a .tex file; return (repo, root_tex)."""
    p = Path(target).expanduser().resolve()
    if p.is_file() and p.suffix == ".tex":
        return p.parent, p
    if not p.is_dir():
        raise SystemExit(f"crucible: not a directory or .tex file: {p}")
    roots = detect_roots(p)
    if not roots:
        raise SystemExit(f"crucible: no \\documentclass found under {p}")
    return p, roots[0]


def detect_roots(repo: Path) -> list[Path]:
    """Every .tex containing \\documentclass, best candidate first.

    Ranking matters: a repo with both main.tex and main-nips.tex is itself a
    finding (V5.7), but we still have to pick one to compile.
    """
    found = []
    for tex in sorted(repo.rglob("*.tex")):
        if any(part.startswith(".") for part in tex.parts):
            continue
        try:
            head = tex.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"^\s*\\documentclass", head, re.M):
            score = 0
            if tex.parent == repo:
                score -= 2
            if tex.stem.lower() in ("main", "paper", "root", "manuscript"):
                score -= 3
            score += len(tex.parts)
            found.append((score, tex))
    found.sort(key=lambda t: (t[0], str(t[1])))
    return [t[1] for t in found]


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
