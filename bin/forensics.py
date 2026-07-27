#!/usr/bin/env python3
"""Statistical red flags on reported numbers.

Every output here is a RED FLAG, never a verdict. Fabrication cannot be proven
from digit patterns; it can only be proven by comparing against measurement
records (--evidence). This collector narrows where a human should look.

Emits facts/forensics.json.
"""
from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from crucible_lib import find_repo_and_root, load_json, write_json

BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def chi_square(observed: Counter, expected_p: dict, n: int):
    if n < 20:
        return None
    chi = 0.0
    for k, p in expected_p.items():
        e = n * p
        if e <= 0:
            continue
        chi += (observed.get(k, 0) - e) ** 2 / e
    return round(chi, 3)


def terminal_digits(values) -> dict:
    """Humans inventing numbers under-produce some final digits."""
    digs = Counter()
    for v in values:
        s = f"{v}"
        if "." not in s:
            continue
        frac = s.split(".")[1].rstrip("0")
        if frac:
            digs[int(frac[-1])] += 1
    n = sum(digs.values())
    uniform = {d: 1 / 10 for d in range(10)}
    return {"counts": dict(sorted(digs.items())), "n": n,
            "chi_square_vs_uniform": chi_square(digs, uniform, n),
            "df": 9,
            "critical_chi2_p05": 16.92,
            "note": "n<20 returns null; this is a screen, not a test of fraud"}


def leading_digits(values) -> dict:
    digs = Counter()
    for v in values:
        av = abs(v)
        if av <= 0:
            continue
        s = f"{av:.10f}".replace(".", "").lstrip("0")
        if s:
            digs[int(s[0])] += 1
    n = sum(digs.values())
    return {"counts": dict(sorted(digs.items())), "n": n,
            "chi_square_vs_benford": chi_square(digs, BENFORD, n),
            "df": 8, "critical_chi2_p05": 15.51,
            "applicable": n >= 50,
            "note": "Benford only meaningful for large, multi-magnitude sets"}


def round_number_share(values) -> dict:
    if not values:
        return {"n": 0}
    whole = sum(1 for v in values if abs(v - round(v)) < 1e-9)
    half = sum(1 for v in values if abs(v * 2 - round(v * 2)) < 1e-9)
    return {"n": len(values),
            "whole_share": round(whole / len(values), 4),
            "half_or_whole_share": round(half / len(values), 4)}


def grim_check(mean: float, n: int, decimals: int) -> dict:
    """Can this mean arise from n integer-valued observations? (I3.6)"""
    if n <= 0 or n > 200:
        return {"applicable": False}
    scale = 10 ** decimals
    total = round(mean * n)
    for cand in (total - 1, total, total + 1):
        if abs(round(cand / n * scale) / scale - mean) < 10 ** (-decimals) / 2:
            return {"applicable": True, "consistent": True,
                    "implied_sum": cand}
    return {"applicable": True, "consistent": False,
            "nearest_possible": [round((total + d) / n, decimals)
                                 for d in (-1, 0, 1)]}


def analyse_table(t) -> dict:
    rows = [r for r in t["rows"] if r["kind"] == "data"]
    if len(rows) < 2:
        return {}
    header = [c["clean"] for c in rows[0]["cells"]]
    body = rows[1:]

    # duplicate data rows (I3.7)
    sigs = defaultdict(list)
    for i, r in enumerate(body):
        sig = "|".join(c["clean"] for c in r["cells"][1:])
        if sig.strip("|"):
            sigs[sig].append({"row": i, "label": r["cells"][0]["clean"]})
    dup_rows = [{"cells": k, "rows": v} for k, v in sigs.items() if len(v) > 1]

    # values repeated within one column across different conditions (I3.1)
    col_repeats = []
    for j, name in enumerate(header):
        vals = defaultdict(list)
        for i, r in enumerate(body):
            if j >= len(r["cells"]):
                continue
            c = r["cells"][j]
            if c["number"] is None:
                continue
            # only flag values with real precision; 0 or 1 repeating is normal
            if abs(c["number"] - round(c["number"])) < 1e-9:
                continue
            vals[round(c["number"], 6)].append(r["cells"][0]["clean"])
        for v, labels in vals.items():
            if len(labels) > 1:
                col_repeats.append({"column": name, "value": v,
                                    "rows": labels})

    nums = []
    for r in body:
        for c in r["cells"]:
            if c["number"] is not None and c["kind"] in ("number", "percent"):
                nums.append(c["number"])

    return {
        "label": t.get("label"), "file": t["file"], "line": t["line"],
        "caption": (t.get("caption") or "")[:200],
        "n_data_rows": len(body), "n_numeric_cells": len(nums),
        "duplicate_rows": dup_rows,
        "repeated_values_within_column": col_repeats,
        "terminal_digits": terminal_digits(nums),
        "leading_digits": leading_digits(nums),
        "round_numbers": round_number_share(nums),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--evidence", help="dir of run artifacts (results.json, CSVs)")
    args = ap.parse_args()

    repo, _ = find_repo_and_root(args.target)
    facts = Path(args.out) / "facts"
    tables = load_json(facts / "tables.json")
    numbers = load_json(facts / "numbers.json")

    per_table = [analyse_table(t) for t in tables]
    per_table = [p for p in per_table if p]

    all_nums = []
    for t in tables:
        for r in t["rows"]:
            if r["kind"] != "data":
                continue
            for c in r["cells"]:
                if c["number"] is not None and c["kind"] in ("number", "percent"):
                    all_nums.append(c["number"])

    # GRIM on fraction cells: 'Accept 7/8 (87.5%)' style reporting
    grim = []
    for t in tables:
        for r in t["rows"]:
            if r["kind"] != "data":
                continue
            for c in r["cells"]:
                if c.get("fraction") and c["fraction"][1]:
                    a, b = c["fraction"]
                    if c.get("percent") is not None:
                        exact = 100.0 * a / b
                        if abs(exact - c["percent"]) > 0.051:
                            grim.append({
                                "label": t.get("label"), "cell": c["clean"],
                                "fraction": [a, b],
                                "printed_percent": c["percent"],
                                "exact_percent": round(exact, 4),
                                "file": t["file"], "line": t["line"]})

    # small denominators carrying high-precision claims (R3.5)
    small_n = []
    for t in tables:
        for r in t["rows"]:
            if r["kind"] != "data":
                continue
            for c in r["cells"]:
                if c.get("fraction"):
                    a, b = c["fraction"]
                    if 0 < b <= 12:
                        small_n.append({"label": t.get("label"),
                                        "cell": c["clean"], "n": b,
                                        "row": r["cells"][0]["clean"],
                                        "file": t["file"], "line": t["line"]})

    evidence = None
    if args.evidence:
        ev = Path(args.evidence).expanduser()
        found = []
        if ev.is_dir():
            for pat in ("*.json", "*.csv", "*.jsonl", "*.tsv"):
                found += [str(p.relative_to(ev)) for p in ev.rglob(pat)]
        evidence = {"dir": str(ev), "exists": ev.is_dir(),
                    "artifact_files": sorted(found)[:500],
                    "n_artifacts": len(found)}

    out = {
        "per_table": per_table,
        "corpus": {
            "n_numeric_cells": len(all_nums),
            "terminal_digits": terminal_digits(all_nums),
            "leading_digits": leading_digits(all_nums),
            "round_numbers": round_number_share(all_nums),
        },
        "fraction_percent_mismatches": grim,
        "inline_fraction_mismatches": numbers.get("inline_fraction_mismatches", []),
        "small_denominator_claims": small_n,
        "evidence": evidence,
        "disclaimer": (
            "All entries are screening signals. None of them establishes "
            "fabrication. Assertions of fabrication require an --evidence "
            "directory showing the value is absent from measurement records."
        ),
    }
    write_json(facts / "forensics.json", out)

    c = out["corpus"]
    print(f"forensics: {c['n_numeric_cells']} numeric table cells")
    print(f"  terminal-digit chi2={c['terminal_digits']['chi_square_vs_uniform']} "
          f"(crit 16.92, n={c['terminal_digits']['n']})")
    print(f"  round-number share={c['round_numbers'].get('whole_share')}")
    for p in per_table:
        if p["duplicate_rows"]:
            print(f"  ! {p['label']}: {len(p['duplicate_rows'])} duplicate row(s)")
        if p["repeated_values_within_column"]:
            for rv in p["repeated_values_within_column"][:4]:
                print(f"  ~ {p['label']}: {rv['column']}={rv['value']} "
                      f"repeats across {rv['rows']}")
    if grim:
        print(f"  ! {len(grim)} fraction/percent mismatch(es) in tables")
        for g in grim[:5]:
            print(f"      {g['label']} '{g['cell']}' exact={g['exact_percent']}")
    if small_n:
        print(f"  ~ {len(small_n)} claim(s) rest on n<=12 denominators")
    if evidence:
        print(f"  evidence dir: {evidence['n_artifacts']} artifact file(s)")


if __name__ == "__main__":
    main()
