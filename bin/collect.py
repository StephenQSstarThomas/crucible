#!/usr/bin/env python3
"""Run every collector in dependency order and write a fact summary.

This is the deterministic half of CRUCIBLE (Axiom 4). It produces facts only;
no finding is created here. Re-running it after a fix produces a byte-comparable
result, which is how the fix loop proves it introduced no regression.

    python3 bin/collect.py <repo-or-tex> -o crucible-out [--venue neurips-2026]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from crucible_lib import load_json, write_json

HERE = Path(__file__).resolve().parent

# order matters: refs/numbers/figures/forensics read earlier outputs
STAGES = [
    ("ingest",    ["ingest.py"],    True),
    ("render",    ["render.py"],    False),   # needs a TeX engine; optional
    ("tables",    ["tables.py"],    True),
    ("refs",      ["refs.py"],      True),
    ("numbers",   ["numbers.py"],   True),
    ("figures",   ["figures.py"],   False),
    ("forensics", ["forensics.py"], True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("-o", "--out", default="crucible-out")
    ap.add_argument("--venue")
    ap.add_argument("--root")
    ap.add_argument("--evidence")
    ap.add_argument("--double-blind", choices=["auto", "yes", "no"],
                    default="auto")
    ap.add_argument("--skip-render", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = {}
    for name, cmd, required in STAGES:
        if name == "render" and args.skip_render:
            results[name] = {"status": "skipped"}
            continue
        argv = [sys.executable, str(HERE / cmd[0]), args.target, "-o", args.out]
        if args.root:
            argv += ["--root", args.root]
        if name == "forensics" and args.evidence:
            argv += ["--evidence", args.evidence]

        t0 = time.time()
        print(f"\n=== {name} " + "=" * (60 - len(name)))
        p = subprocess.run(argv, text=True)
        dt = round(time.time() - t0, 1)
        results[name] = {"status": "ok" if p.returncode == 0 else "failed",
                         "returncode": p.returncode, "seconds": dt}
        if p.returncode != 0 and required:
            print(f"crucible: required collector '{name}' failed", file=sys.stderr)

    if args.venue:
        argv = [sys.executable, str(HERE / "venue.py"), args.target,
                "-o", args.out, "--venue", args.venue,
                "--double-blind", args.double_blind]
        if args.root:
            argv += ["--root", args.root]
        t0 = time.time()
        print(f"\n=== venue " + "=" * 55)
        p = subprocess.run(argv, text=True)
        results["venue"] = {"status": "ok" if p.returncode == 0 else "failed",
                            "returncode": p.returncode,
                            "seconds": round(time.time() - t0, 1)}

    # one small file an agent can read first to orient itself
    facts = out / "facts"
    summary = {"stages": results, "venue": args.venue,
               "evidence_dir": args.evidence}
    try:
        ing = load_json(facts / "ingest.json")
        summary["paper"] = {
            "root_tex": ing["root_tex"],
            "documentclass": ing["documentclass"],
            "title": ing["title_prose"][:200],
            "n_files": len(ing["files"]),
            "n_sections": len(ing["sections"]),
            "n_floats": len(ing["floats"]),
            "n_cites": len(ing["cites"]),
            "multiple_roots": ing["multiple_roots"],
        }
    except Exception:
        pass
    for key, path in (("render", "render.json"), ("refs", "refs.json"),
                      ("numbers", "numbers.json"), ("tables", "tables.json"),
                      ("figures", "figures.json"),
                      ("forensics", "forensics.json"),
                      ("venue", "venue.json")):
        p = facts / path
        if p.is_file():
            summary.setdefault("available_facts", []).append(f"facts/{path}")

    write_json(out / "facts" / "_summary.json", summary)
    print(f"\n=== done " + "=" * 56)
    for k, v in results.items():
        print(f"  {k:10s} {v['status']:8s} {v.get('seconds', '')}s")
    print(f"\nfacts written to {facts}/")


if __name__ == "__main__":
    main()
