#!/usr/bin/env python3
"""Build the numeric ledger: every number, where it lives, and what it should match.

The single highest-yield check in the whole system is anchoring: a number stated
in prose right after "see Table 2" that does not appear anywhere in Table 2.
That is how "CoPilot used 19 interventions" survives next to a table cell
reading 6.

Emits facts/numbers.json.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from crucible_lib import (collect_macros, demacro, find_blocks,
                          find_repo_and_root, flatten, load_json, to_prose,
                          write_json)

NUM_RX = re.compile(
    r"(?<![\w.])"
    r"(?P<num>[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*(?P<suffix>\\?%|pp\b|x\b|×)?")

STOP = set("""the a an of in on at to for and or is are was were be been with by
from as that this these those it its their our we us they he she which who whom
than then when where while such very more most less least each per than into
over under above below between both all any some no not only also both either""".split())

# Numbers that are structural rather than measured. Flagging "Table 2" or
# "Section 4.1" as an unanchored measurement would bury the real findings.
STRUCTURAL_CONTEXT = re.compile(
    r"(?:table|tab\.|figure|fig\.|section|sec\.|appendix|app\.|equation|eq\.|"
    r"algorithm|alg\.|line|step|stage|item|footnote|page|chapter|part|"
    r"theorem|lemma|definition|proposition|corollary|remark|assumption)"
    r"[~\s]*$", re.I)

TABLE_REF_RX = re.compile(r"\\(?:ref|cref|Cref|autoref)\s*\{(tab[^}]*)\}")
FIG_REF_RX = re.compile(r"\\(?:ref|cref|Cref|autoref)\s*\{(fig[^}]*)\}")


def keywords(ctx: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", ctx.lower())
    return [w for w in words if w not in STOP]


def norm(tok: str) -> float | None:
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


def extract_from_prose(doc, macros, sections) -> list[dict]:
    """Every number in body prose, with enough context to judge it."""
    # map vline -> section title
    sec_at = {}
    cur = ""
    sec_by_vline = {s["vline"]: s["title"] for s in sections}
    for l in doc.lines:
        if l.vline in sec_by_vline:
            cur = sec_by_vline[l.vline]
        sec_at[l.vline] = cur

    # vlines inside tabular bodies are handled by tables.py, not here
    tab_spans = set()
    for b in find_blocks(doc, {"tabular", "tabularx", "tabular*", "array",
                               "longtable", "tabulary"}):
        tab_spans.update(range(b.start_vline, b.end_vline + 1))

    out = []
    for l in doc.lines:
        if l.in_verbatim or l.vline in tab_spans:
            continue
        code = l.code
        if not code.strip() or code.strip().startswith("\\usepackage"):
            continue

        # nearest preceding table/figure reference, within this paragraph
        near_tab, near_fig = None, None
        for back in range(l.vline, max(0, l.vline - 12), -1):
            prev = doc.lines[back - 1]
            if prev.file != l.file:
                break
            if not prev.code.strip() and back != l.vline:
                break
            if near_tab is None:
                mt = TABLE_REF_RX.search(prev.code)
                if mt:
                    near_tab = mt.group(1)
            if near_fig is None:
                mf = FIG_REF_RX.search(prev.code)
                if mf:
                    near_fig = mf.group(1)

        rendered = demacro(code, macros)
        for m in NUM_RX.finditer(rendered):
            tok = m.group("num")
            val = norm(tok)
            if val is None:
                continue
            # Skip numbers embedded in hyphenated identifiers: the 5.3 inside
            # "GPT-5.3-codex" is a model version, not a measurement, and
            # reporting it as unanchored buries the real findings.
            s, e = m.start("num"), m.end()
            if s >= 2 and rendered[s - 1] == "-" and rendered[s - 2].isalnum():
                continue
            if e < len(rendered) - 1 and rendered[e] == "-" \
                    and rendered[e + 1].isalpha():
                continue
            lo = max(0, m.start() - 90)
            before = rendered[lo:m.start()]
            after = rendered[m.end():m.end() + 50]

            if STRUCTURAL_CONTEXT.search(to_prose(before)):
                kind = "structural"
            else:
                kind = "measurement"

            suf = (m.group("suffix") or "").replace("\\", "").strip()
            unit = {"%": "percent", "pp": "pp", "x": "x", "×": "x"}.get(suf, "")

            out.append({
                "value": val,
                "token": tok + (suf or ""),
                "unit": unit,
                "kind": kind,
                "file": l.file, "line": l.lineno, "vline": l.vline,
                "section": sec_at.get(l.vline, ""),
                "context_before": to_prose(before)[-80:],
                "context_after": to_prose(after)[:40],
                "keywords": keywords(to_prose(before))[-8:],
                "near_table_ref": near_tab,
                "near_figure_ref": near_fig,
                "in_abstract": sec_at.get(l.vline, "") == "" and l.vline < 200,
            })
    return out


def table_values(tables) -> dict:
    """label -> set of every numeric value appearing in that table."""
    vals = defaultdict(set)
    allv = set()
    for t in tables:
        lab = t.get("label") or f"{t['file']}:{t['line']}"
        for r in t["rows"]:
            if r["kind"] != "data":
                continue
            for c in r["cells"]:
                for n in c.get("numbers") or []:
                    vals[lab].add(round(n, 6))
                    allv.add(round(n, 6))
                if c.get("fraction"):
                    a, b = c["fraction"]
                    vals[lab].add(float(a))
                    vals[lab].add(float(b))
                    allv.add(float(a))
                    allv.add(float(b))
                    if b:
                        pct = round(100.0 * a / b, 4)
                        vals[lab].add(pct)
                        allv.add(pct)
    return {"by_label": {k: sorted(v) for k, v in vals.items()},
            "all": sorted(allv)}


def approx_in(val: float, pool) -> bool:
    for p in pool:
        if abs(p - val) < 1e-6:
            return True
        if abs(p) > 1e-9 and abs(p - val) / abs(p) < 0.002:
            return True
        # a table holding 0.875 backs prose saying 87.5%
        if abs(p * 100 - val) < 0.05 or abs(p / 100 - val) < 5e-5:
            return True
    return False


def inline_fraction_checks(doc, macros) -> list[dict]:
    """'3/8 (38%)' -- deterministic, no judgment needed (I1.6)."""
    out = []
    rx = re.compile(r"(\d+)\s*/\s*(\d+)\s*\(\s*([\d.]+)\s*\\?%\s*\)")
    for l in doc.lines:
        if l.in_verbatim:
            continue
        for m in rx.finditer(demacro(l.code, macros)):
            a, b, pct = int(m.group(1)), int(m.group(2)), float(m.group(3))
            if b == 0:
                continue
            exact = 100.0 * a / b
            if abs(exact - pct) > 0.051:
                out.append({"file": l.file, "line": l.lineno,
                            "text": m.group(0), "fraction": [a, b],
                            "printed_percent": pct,
                            "exact_percent": round(exact, 4),
                            "delta": round(abs(exact - pct), 4)})
    return out


def scan_sidecar_docs(repo: Path) -> list[dict]:
    """Numbers in repo .md files. Stale values here mean the paper's numbers
    changed and the change was not propagated everywhere (I1.7)."""
    out = []
    for md in sorted(repo.rglob("*.md")):
        if any(p.startswith(".") for p in md.parts):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in NUM_RX.finditer(line):
                v = norm(m.group("num"))
                if v is None or v == int(v) and abs(v) < 10:
                    continue
                out.append({"file": str(md.relative_to(repo)), "line": i,
                            "value": v, "token": m.group("num"),
                            "context": line.strip()[:160]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--root")
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()

    facts = Path(args.out) / "facts"
    ing = load_json(facts / "ingest.json")
    tables = load_json(facts / "tables.json")

    doc = flatten(root, repo)
    macros = collect_macros(doc)

    prose = extract_from_prose(doc, macros, ing["sections"])
    tv = table_values(tables)

    # anchoring: does a prose measurement exist in the table it points at?
    unanchored = []
    for n in prose:
        if n["kind"] != "measurement":
            continue
        if not n["near_table_ref"]:
            continue
        pool = tv["by_label"].get(n["near_table_ref"], [])
        if not pool:
            continue
        if not approx_in(n["value"], pool):
            n_any = approx_in(n["value"], tv["all"])
            unanchored.append({**n, "in_referenced_table": False,
                               "in_any_table": n_any})

    # exact-value clusters, so an agent can trace one quantity across the paper
    clusters = defaultdict(list)
    for n in prose:
        if n["kind"] == "measurement":
            clusters[round(n["value"], 6)].append(
                {"file": n["file"], "line": n["line"], "section": n["section"],
                 "token": n["token"], "context": n["context_before"][-50:]})

    repeated = {str(k): v for k, v in clusters.items() if len(v) > 1}

    out = {
        "n_prose_numbers": len(prose),
        "n_measurements": sum(1 for n in prose if n["kind"] == "measurement"),
        "prose_numbers": prose,
        "table_values": tv,
        "unanchored_measurements": unanchored,
        "repeated_values": repeated,
        "inline_fraction_mismatches": inline_fraction_checks(doc, macros),
        "sidecar_doc_numbers": scan_sidecar_docs(repo),
    }
    write_json(facts / "numbers.json", out)

    print(f"numbers: {len(prose)} in prose "
          f"({out['n_measurements']} measurements), "
          f"{len(tv['all'])} distinct table values")
    if unanchored:
        print(f"  ! {len(unanchored)} measurement(s) not found in the table "
              f"they reference:")
        for u in unanchored[:10]:
            print(f"      {u['file']}:{u['line']}  {u['token']:>8s}  "
                  f"-> {u['near_table_ref']}  "
                  f"(elsewhere={u['in_any_table']})  "
                  f"...{u['context_before'][-46:]}")
    if out["inline_fraction_mismatches"]:
        print(f"  ! {len(out['inline_fraction_mismatches'])} inline "
              f"fraction/percent mismatch(es)")
        for f in out["inline_fraction_mismatches"][:6]:
            print(f"      {f['file']}:{f['line']}  {f['text']}  "
                  f"exact={f['exact_percent']}")


if __name__ == "__main__":
    main()
