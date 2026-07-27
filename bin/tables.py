#!/usr/bin/env python3
"""Parse LaTeX tabulars into addressable grids so table arithmetic can be recomputed.

This is what turns "the Overall column looks wrong" into "0.912*7 + 0.898*3 +
0.489*10 = 13.968, /20 = 0.6984, printed 0.867" (Axiom 2). Without a real grid
you cannot recompute anything, and every numeric finding stays an assertion.

Emits facts/tables.json.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from crucible_lib import (arg_after, collect_macros, demacro, find_blocks,
                          find_repo_and_root, flatten, write_json)

TABULAR_ENVS = {"tabular", "tabularx", "tabular*", "array", "longtable",
                "tabulary", "supertabular"}

RULES = re.compile(r"\\(toprule|midrule|bottomrule|hline|cmidrule|addlinespace|"
                   r"specialrule|cline)\s*(\([^)]*\))?\s*(\{[^}]*\})?")


def clean_cell(s: str, macros: dict) -> str:
    """Strip formatting down to the readable content of one cell."""
    s = RULES.sub(" ", s)
    s = demacro(s, macros)
    # keep the *content* of formatting wrappers, drop the wrapper
    for cmd in ("textbf", "textit", "emph", "mathbf", "underline", "texttt",
                "textsc", "text", "mathrm", "bf", "it"):
        for _ in range(3):
            m = re.search(r"\\" + cmd + r"\s*\{", s)
            if not m:
                break
            body, end = arg_after(s, m.end() - 1)
            s = s[:m.start()] + body + s[end:]
    m = re.search(r"\\multicolumn\s*\{\d+\}\s*\{[^}]*\}\s*\{", s)
    if m:
        body, end = arg_after(s, m.end() - 1)
        s = s[:m.start()] + body + s[end:]
    m = re.search(r"\\multirow\s*\{[^}]*\}\s*(\[[^\]]*\])?\s*\{[^}]*\}\s*\{", s)
    if m:
        body, end = arg_after(s, m.end() - 1)
        s = s[:m.start()] + body + s[end:]
    s = re.sub(r"\\[a-zA-Z@]+\s*\*?", " ", s)
    s = re.sub(r"[{}$~^]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


NUM_RX = re.compile(r"[-+]?(?:\d+\.\d+|\.\d+|\d+)(?:[eE][-+]?\d+)?")
FRAC_RX = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
PCT_RX = re.compile(r"([-+]?[\d.]+)\s*\\?%")


def cell_value(clean: str, raw: str):
    """Best-effort numeric interpretation of a cell.

    Returns dict with kind and value(s). A cell like '7/8 (87.5%)' yields both
    the fraction and the percent so I2.3 can check them against each other.
    """
    out = {"kind": "text", "number": None, "numbers": [],
           "fraction": None, "percent": None, "bold": False}
    out["bold"] = bool(re.search(r"\\(textbf|mathbf|bf)\b", raw))

    nums = [float(x) for x in NUM_RX.findall(clean.replace("%", " "))]
    out["numbers"] = nums

    mf = FRAC_RX.match(clean)
    if mf:
        num, den = int(mf.group(1)), int(mf.group(2))
        out["kind"] = "fraction"
        out["fraction"] = [num, den]
        out["number"] = num / den if den else None
        return out

    mp = PCT_RX.search(raw) or re.search(r"([-+]?[\d.]+)\s*%", clean)
    if mp:
        try:
            out["percent"] = float(mp.group(1))
            out["kind"] = "percent"
            out["number"] = out["percent"]
        except ValueError:
            pass

    mfrac_in = re.search(r"(\d+)\s*/\s*(\d+)", clean)
    if mfrac_in and out["kind"] != "fraction":
        out["fraction"] = [int(mfrac_in.group(1)), int(mfrac_in.group(2))]

    if out["kind"] == "text" and len(nums) == 1:
        # Only call it a number when the cell IS the number. 'AI Scientist v2'
        # contains a 2 but is a row label, not a measurement.
        residue = NUM_RX.sub("", clean)
        residue = re.sub(r"[\s%$()\[\]±+\-*/,.:;✓✗✘■]", "",
                         residue)
        if not residue:
            out["kind"] = "number"
            out["number"] = nums[0]
    return out


def split_rows(body: str) -> list[str]:
    """Split on \\\\ that are not inside braces."""
    rows, depth, cur, i = [], 0, [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body) and body[i + 1] == "\\":
            if depth == 0:
                rows.append("".join(cur))
                cur = []
                i += 2
                # swallow an optional [2pt] spacing arg
                m = re.match(r"\s*\[[^\]]*\]", body[i:])
                if m:
                    i += m.end()
                continue
            cur.append("\\\\")
            i += 2
            continue
        if c == "\\":
            cur.append(body[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        cur.append(c)
        i += 1
    if "".join(cur).strip():
        rows.append("".join(cur))
    return rows


def split_cells(row: str) -> list[str]:
    cells, depth, cur, i = [], 0, [], 0
    while i < len(row):
        c = row[i]
        if c == "\\":
            cur.append(row[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "&" and depth == 0:
            cells.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    cells.append("".join(cur))
    return cells


def parse_tabular(block, macros: dict) -> dict:
    body = block.body
    # longest-first so 'tabular*' wins over 'tabular'
    alts = sorted(TABULAR_ENVS, key=len, reverse=True)
    m = re.search(r"\\begin\{(" + "|".join(re.escape(e) for e in alts) + r")\}",
                  body)
    if not m:
        return {}
    env_name = m.group(1)
    i = m.end()
    # tabularx and tabular* take a width argument before the column spec
    if env_name in ("tabularx", "tabular*", "tabulary"):
        _, i = arg_after(body, i)
    colspec, i = arg_after(body, i)
    end = body.rfind("\\end{")
    inner = body[i:end if end != -1 else len(body)]

    rows_out = []
    for r in split_rows(inner):
        if not r.strip():
            continue
        is_rule_only = not RULES.sub("", r).strip()
        if is_rule_only:
            rows_out.append({"kind": "rule", "cells": []})
            continue
        cells = []
        for craw in split_cells(r):
            cl = clean_cell(craw, macros)
            cells.append({"raw": craw.strip(), "clean": cl,
                          **cell_value(cl, craw)})
        if any(c["clean"] for c in cells):
            rows_out.append({"kind": "data", "cells": cells})
    return {"colspec": colspec, "rows": rows_out}


def column_view(rows: list[dict]) -> dict:
    """Header row + per-column numeric series, addressable by name."""
    data = [r for r in rows if r["kind"] == "data"]
    if not data:
        return {}
    header = [c["clean"] for c in data[0]["cells"]]
    body = data[1:]
    cols = {}
    for j, name in enumerate(header):
        series = []
        for ri, r in enumerate(body):
            if j < len(r["cells"]):
                c = r["cells"][j]
                series.append({"row": ri, "label": r["cells"][0]["clean"],
                               "clean": c["clean"], "number": c["number"],
                               "fraction": c["fraction"],
                               "percent": c["percent"], "bold": c["bold"]})
        cols[name or f"col{j}"] = series
    return {"header": header, "n_data_rows": len(body), "columns": cols}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--root")
    args = ap.parse_args()

    repo, root = find_repo_and_root(args.target)
    if args.root:
        root = (repo / args.root).resolve()
    doc = flatten(root, repo)
    macros = collect_macros(doc)

    floats = find_blocks(doc, {"table", "table*", "figure", "figure*"})
    tabulars = find_blocks(doc, TABULAR_ENVS | {e + "*" for e in TABULAR_ENVS})

    out = []
    for tb in tabulars:
        owner = None
        for f in floats:
            if f.start_vline <= tb.start_vline and tb.end_vline <= f.end_vline:
                owner = f
                break
        cap, label = "", ""
        if owner:
            mc = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", owner.body)
            if mc:
                cap, _ = arg_after(owner.body, mc.end() - 1)
            ml = re.search(r"\\label\s*\{([^}]*)\}", owner.body)
            if ml:
                label = ml.group(1)

        parsed = parse_tabular(tb, macros)
        if not parsed:
            continue
        entry = {
            "label": label,
            "caption": demacro(cap, macros).strip(),
            "env": tb.env,
            "file": tb.file, "line": tb.start_line,
            "start_vline": tb.start_vline, "end_vline": tb.end_vline,
            **parsed,
        }
        entry["view"] = column_view(parsed["rows"])
        out.append(entry)

    write_json(Path(args.out) / "facts" / "tables.json", out)
    print(f"tables: {len(out)} tabular(s)")
    for t in out:
        v = t.get("view", {})
        print(f"  {t['label'] or '(unlabeled)':32s} "
              f"{t['file']}:{t['line']:<5d} "
              f"{len(v.get('header', []))}col x {v.get('n_data_rows', 0)}row")


if __name__ == "__main__":
    main()
