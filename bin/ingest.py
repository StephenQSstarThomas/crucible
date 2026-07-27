#!/usr/bin/env python3
"""Resolve the \\input tree into one flat document and extract its structure.

Facts only. Emits facts/ingest.json with the section tree, float inventory,
macro table, and the line map that lets every later finding cite file:line.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from crucible_lib import (Doc, Line, arg_after, collect_macros, demacro,
                          detect_roots, find_blocks, find_repo_and_root,
                          flatten, to_prose, write_json)

SECTION_CMDS = ["part", "chapter", "section", "subsection", "subsubsection",
                "paragraph", "subparagraph"]

DRAFT_MARKERS = ["TODO", "FIXME", "XXX", "HACK", "REVISIT", "PLACEHOLDER",
                 "lorem ipsum", "Lorem ipsum", "TBD"]

ANNOTATION_CMDS = ["todo", "note", "comment", "fixme", "change", "revise",
                   "hl", "marginpar", "TODO", "NOTE"]


def extract_sections(doc: Doc, macros: dict) -> list[dict]:
    out = []
    rx = re.compile(r"\\(" + "|".join(SECTION_CMDS) + r")\s*\*?\s*(?=[\[{])")
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in rx.finditer(l.code):
            title, _ = arg_after(l.code, m.end())
            out.append({
                "level": m.group(1),
                "title": demacro(title, macros).strip(),
                "title_raw": title,
                "file": l.file, "line": l.lineno, "vline": l.vline,
                "starred": "*" in l.code[m.start():m.end()],
            })
    return out


def extract_labels_refs_cites(doc: Doc) -> dict:
    labels, refs, cites, keyval_labels = [], [], [], []
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in re.finditer(r"\\label\s*\{([^}]*)\}", l.code):
            labels.append({"key": m.group(1).strip(), "file": l.file,
                           "line": l.lineno, "vline": l.vline,
                           "form": "command"})
        # tcolorbox / listings / thmtools declare labels as a key-value option:
        #   \begin{tcolorbox}[..., label={box:foo}, ...]
        # These are real labels. Missing them produces false "undefined \ref"
        # reports, which is the fastest way to make the whole tool untrusted.
        for m in re.finditer(r"(?<!\\)\blabel\s*=\s*\{?([A-Za-z0-9:_\-.]+)\}?",
                             l.code):
            key = m.group(1).strip()
            if key and not l.code[:m.start()].rstrip().endswith("\\"):
                keyval_labels.append({"key": key, "file": l.file,
                                      "line": l.lineno, "vline": l.vline,
                                      "form": "keyval"})
        for m in re.finditer(
                r"\\(ref|cref|Cref|autoref|eqref|pageref|vref)\s*\{([^}]*)\}", l.code):
            for key in m.group(2).split(","):
                key = key.strip()
                if key:
                    refs.append({"key": key, "cmd": m.group(1), "file": l.file,
                                 "line": l.lineno, "vline": l.vline})
        for m in re.finditer(
                r"\\(cite[a-zA-Z]*|nocite)\s*(?:\[[^\]]*\])?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}",
                l.code):
            for key in m.group(2).split(","):
                key = key.strip()
                if key:
                    cites.append({"key": key, "cmd": m.group(1), "file": l.file,
                                  "line": l.lineno, "vline": l.vline})
    return {"labels": labels, "refs": refs, "cites": cites,
            "keyval_labels": keyval_labels}


def extract_floats(doc: Doc, macros: dict) -> list[dict]:
    """Figures and tables, with their caption, label, and graphics."""
    out = []
    for b in find_blocks(doc, {"figure", "table", "figure*", "table*",
                               "wrapfigure", "algorithm"}):
        cap = ""
        mcap = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", b.body)
        if mcap:
            cap, _ = arg_after(b.body, mcap.end() - 1)
        labs = re.findall(r"\\label\s*\{([^}]*)\}", b.body)
        gfx = []
        for m in re.finditer(r"\\includegraphics\s*(\[[^\]]*\])?\s*\{([^}]*)\}",
                             b.body):
            gfx.append({"opts": (m.group(1) or "").strip("[]"),
                        "path": m.group(2).strip()})
        out.append({
            "env": b.env,
            "file": b.file, "line": b.start_line,
            "start_vline": b.start_vline, "end_vline": b.end_vline,
            "labels": [x.strip() for x in labs],
            "caption": demacro(cap, macros).strip(),
            "caption_raw": cap,
            "caption_prose": to_prose(demacro(cap, macros)),
            "graphics": gfx,
            "has_tabular": bool(re.search(r"\\begin\{tabular", b.body)),
        })
    return out


def extract_all_graphics(doc: Doc) -> list[dict]:
    """Every \\includegraphics, including ones outside any float.

    Title logos and inline marks live outside figure environments but are still
    placed images subject to DPI and (for double-blind) identity checks.
    """
    out = []
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in re.finditer(
                r"\\includegraphics\s*(\[[^\]]*\])?\s*\{([^}]*)\}", l.code):
            out.append({"path": m.group(2).strip(),
                        "opts": (m.group(1) or "").strip("[]"),
                        "file": l.file, "line": l.lineno, "vline": l.vline})
    return out


COMMENTED_STRUCTURE_RX = re.compile(
    r"^\s*%+\s*\\(paragraph|subparagraph|section|subsection|subsubsection|"
    r"item|caption|begin\{(?:table|figure|tcolorbox)\})")


def scan_commented_out_content(doc: Doc, min_words: int = 25) -> dict:
    """Find substantive prose that exists in the source but not in the PDF.

    Authors under a page limit routinely comment out material rather than
    delete it. That material is invisible to reviewers but fully visible here,
    and it is often exactly what reviewers then ask for: methodological detail,
    per-topic tables, and honest self-criticism. Surfacing it turns "add a
    limitations discussion" into "uncomment appendix.tex:396-406".
    """
    blocks, cur = [], None
    for l in doc.lines:
        c = l.comment.lstrip("%").strip()
        is_struct = bool(COMMENTED_STRUCTURE_RX.match(l.raw))
        has_prose = len(c.split()) >= 6 and not l.code.strip()

        if is_struct or (cur is not None and has_prose):
            if cur is None or is_struct:
                if cur and cur["words"] >= min_words:
                    blocks.append(cur)
                title = ""
                m = re.search(r"\\(?:sub)*(?:paragraph|section)\s*\{([^}]*)\}",
                              l.raw)
                if m:
                    title = m.group(1)
                cur = {"file": l.file, "line": l.lineno, "title": title,
                       "text": c, "words": len(c.split()),
                       "starts_with_structure": is_struct}
            else:
                cur["text"] += " " + c
                cur["words"] += len(c.split())
        elif cur is not None:
            if cur["words"] >= min_words:
                blocks.append(cur)
            cur = None
    if cur and cur["words"] >= min_words:
        blocks.append(cur)

    for b in blocks:
        b["preview"] = b["text"][:400]
        b.pop("text", None)

    by_file = {}
    for b in blocks:
        by_file[b["file"]] = by_file.get(b["file"], 0) + 1
    return {"blocks": blocks, "n_blocks": len(blocks),
            "total_words": sum(b["words"] for b in blocks),
            "by_file": by_file}


def scan_draft_markers(doc: Doc) -> dict:
    """TODO in a comment is fine. TODO in rendered body is a blocker (B4.1)."""
    in_body, in_comment, annotations = [], [], []
    for l in doc.lines:
        for mk in DRAFT_MARKERS:
            if mk in l.code and not l.in_verbatim:
                in_body.append({"marker": mk, "file": l.file, "line": l.lineno,
                                "text": l.code.strip()[:200]})
            if mk in l.comment:
                in_comment.append({"marker": mk, "file": l.file,
                                   "line": l.lineno,
                                   "text": l.comment.strip()[:200]})
        if l.in_verbatim:
            continue
        for cmd in ANNOTATION_CMDS:
            if re.search(r"\\" + cmd + r"\s*(\[[^\]]*\])?\s*\{", l.code):
                annotations.append({"cmd": cmd, "file": l.file,
                                    "line": l.lineno,
                                    "text": l.code.strip()[:200]})
    return {"in_rendered_body": in_body, "in_comments_only": in_comment,
            "annotation_macros": annotations}


def scan_commented_inputs(repo: Path, doc: Doc) -> list[dict]:
    """A commented-out \\input is invisible to file-existence checks but the
    content simply vanishes from the PDF. This is how a filled-in checklist
    ends up absent from a submission (V4.1)."""
    out = []
    for l in doc.lines:
        if not l.comment:
            continue
        for m in re.finditer(r"\\(?:input|include)\s*\{([^}]+)\}", l.comment):
            target = m.group(1).strip()
            cands = [repo / target, repo / (target + ".tex")]
            exists = next((c for c in cands if c.is_file()), None)
            out.append({
                "file": l.file, "line": l.lineno, "target": target,
                "target_exists": exists is not None,
                "target_bytes": exists.stat().st_size if exists else 0,
                "text": l.comment.strip()[:200],
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="repo dir or root .tex")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--root", help="force a specific root .tex")
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()

    all_roots = detect_roots(repo)
    doc = flatten(root, repo)
    macros = collect_macros(doc)

    sections = extract_sections(doc, macros)
    lr = extract_labels_refs_cites(doc)
    floats = extract_floats(doc, macros)

    docclass, docclass_opts = "", ""
    for l in doc.lines:
        m = re.search(r"\\documentclass\s*(\[[^\]]*\])?\s*\{([^}]*)\}", l.code)
        if m:
            docclass_opts = (m.group(1) or "").strip("[]")
            docclass = m.group(2).strip()
            break

    packages = []
    for l in doc.lines:
        for m in re.finditer(r"\\usepackage\s*(\[[^\]]*\])?\s*\{([^}]*)\}", l.code):
            for name in m.group(2).split(","):
                packages.append({"name": name.strip(),
                                 "opts": (m.group(1) or "").strip("[]"),
                                 "file": l.file, "line": l.lineno})

    # prose per section, so language checks can be scoped
    prose_blocks = []
    bounds = [s["vline"] for s in sections] + [len(doc.lines) + 1]
    for i, s in enumerate(sections):
        chunk = "\n".join(l.code for l in doc.lines[s["vline"]:bounds[i + 1] - 1]
                          if not l.in_verbatim)
        prose_blocks.append({"section": s["title"], "level": s["level"],
                             "file": s["file"], "line": s["line"],
                             "prose": to_prose(demacro(chunk, macros))})

    abstract = ""
    mabs = re.search(r"\\(?:abstract|begin\{abstract\})", doc.text())
    if mabs:
        t = doc.text()
        m2 = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.DOTALL)
        if m2:
            abstract = m2.group(1)
        else:
            m3 = re.search(r"\\abstract\s*\{", t)
            if m3:
                abstract, _ = arg_after(t, m3.end() - 1)

    title = ""
    mt = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", doc.text())
    if mt:
        title, _ = arg_after(doc.text(), mt.end() - 1)

    out = {
        "repo": str(repo),
        "root_tex": str(root.relative_to(repo)),
        "all_documentclass_files": [str(p.relative_to(repo)) for p in all_roots],
        "multiple_roots": len(all_roots) > 1,
        "documentclass": docclass,
        "documentclass_options": docclass_opts,
        "packages": packages,
        "files": doc.files,
        "n_lines": len(doc.lines),
        "missing_inputs": doc.missing_inputs,
        "empty_inputs": doc.empty_inputs,
        "commented_out_inputs": scan_commented_inputs(repo, doc),
        "commented_out_content": scan_commented_out_content(doc),
        "macros": macros,
        "title": title,
        "title_prose": to_prose(demacro(title, macros)),
        "abstract_raw": abstract,
        "abstract_prose": to_prose(demacro(abstract, macros)),
        "sections": sections,
        "labels": lr["labels"],
        "keyval_labels": lr["keyval_labels"],
        "refs": lr["refs"],
        "cites": lr["cites"],
        "floats": floats,
        "graphics_all": extract_all_graphics(doc),
        "draft_markers": scan_draft_markers(doc),
        "prose_by_section": prose_blocks,
        "linemap": [
            {"vline": l.vline, "file": l.file, "line": l.lineno}
            for l in doc.lines
        ],
    }

    outdir = Path(args.out) / "facts"
    write_json(outdir / "ingest.json", out)

    print(f"ingest: root={out['root_tex']} files={len(doc.files)} "
          f"lines={len(doc.lines)} sections={len(sections)} "
          f"floats={len(floats)} cites={len(lr['cites'])} "
          f"labels={len(lr['labels'])}")
    if out["multiple_roots"]:
        print(f"  ! {len(all_roots)} files contain \\documentclass: "
              f"{out['all_documentclass_files']}")
    if doc.empty_inputs:
        print(f"  ! {len(doc.empty_inputs)} \\input target(s) have no content")
    if out["commented_out_inputs"]:
        print(f"  ! {len(out['commented_out_inputs'])} commented-out \\input(s)")
    coc = out["commented_out_content"]
    if coc["n_blocks"]:
        print(f"  ! {coc['n_blocks']} commented-out content block(s), "
              f"{coc['total_words']} words hidden from the PDF: {coc['by_file']}")
        for b in coc["blocks"][:8]:
            t = f" [{b['title']}]" if b["title"] else ""
            print(f"      {b['file']}:{b['line']}{t} ({b['words']}w) "
                  f"{b['preview'][:80]}")


if __name__ == "__main__":
    main()
