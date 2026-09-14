#!/usr/bin/env python3
"""Merge parallel review output into one findings.json.

Reviewers write candidates/<TIER>[.part-K].json (arrays of findings with no
verdict). Verifiers write verdicts/<FINDING-ID>.json, one file each, so any
number of them can run at once without editing a shared file. This script does
the bookkeeping only: it checks the contract, attaches verdicts, applies the
PLAUSIBLE downgrade, marks audited mechanical fixes, sorts, and counts. It makes
no judgment of its own.

    python3 bin/merge_findings.py crucible-out
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TIERS = ["P0-BUILD", "P0-INTEG", "P0-SURF", "P1-CLAIM", "P2-RIGOR", "P3-DEF",
         "P4-PRES", "V-VENUE", "P5-PANEL"]
SEVERITIES = ["blocker", "major", "minor", "nit"]
VERDICTS = ["CONFIRMED", "PLAUSIBLE", "REFUTED"]
# every finding in these tiers must carry its own verifier verdict
MUST_VERIFY = {"P0-BUILD", "P0-INTEG", "P0-SURF", "P1-CLAIM", "V-VENUE"}
REQUIRED = ["id", "tier", "severity", "category", "title_zh", "summary_zh",
            "locations", "evidence"]
ID_RX = re.compile(r"^(" + "|".join(TIERS) + r")-[0-9]{3}$")
UNSAMPLED = "未单独验证（不在抽验范围内）。"


def load_array(path: Path, errors: list[str]) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: unreadable ({exc})")
        return []
    if isinstance(data, dict) and isinstance(data.get("findings"), list):
        data = data["findings"]
    if not isinstance(data, list):
        errors.append(f"{path.name}: expected a JSON array of findings")
        return []
    return data


def check_finding(f: dict, source: str, errors: list[str]) -> bool:
    missing = [k for k in REQUIRED if k not in f]
    if missing:
        errors.append(f"{source}: {f.get('id', '?')} missing {missing}")
        return False
    if not ID_RX.match(str(f["id"])):
        errors.append(f"{source}: bad id {f['id']!r}")
        return False
    if not str(f["id"]).startswith(f["tier"] + "-"):
        errors.append(f"{source}: id {f['id']} does not match tier {f['tier']}")
        return False
    if f["severity"] not in SEVERITIES:
        errors.append(f"{source}: {f['id']} bad severity {f['severity']!r}")
        return False
    if not f["locations"] or not all(
            isinstance(l, dict) and l.get("file") and isinstance(l.get("line"), int)
            for l in f["locations"]):
        errors.append(f"{source}: {f['id']} needs file + integer line per location")
        return False
    if not f["evidence"].get("collector"):
        errors.append(f"{source}: {f['id']} evidence.collector is empty")
        return False
    return True


def round_no(path: Path) -> int:
    m = re.search(r"(\d+)", path.stem)
    return int(m.group(1)) if m else 0


def downgrade(severity: str) -> str:
    i = SEVERITIES.index(severity)
    return SEVERITIES[min(i + 1, len(SEVERITIES) - 1)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="CRUCIBLE output directory")
    args = ap.parse_args()
    out = Path(args.out)

    errors: list[str] = []
    findings: dict[str, dict] = {}
    cand_dir = out / "candidates"
    for path in sorted(cand_dir.glob("*.json")) if cand_dir.is_dir() else []:
        for f in load_array(path, errors):
            if not isinstance(f, dict) or not check_finding(f, path.name, errors):
                continue
            if f["id"] in findings:
                errors.append(f"duplicate id {f['id']} ({path.name}); "
                              "shards must use disjoint id ranges")
                continue
            findings[f["id"]] = dict(f)

    verdicts: dict[str, dict] = {}
    verdict_dir = out / "verdicts"
    for path in sorted(verdict_dir.glob("*.json")) if verdict_dir.is_dir() else []:
        try:
            v = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"verdicts/{path.name}: unreadable ({exc})")
            continue
        fid = v.get("id") or path.stem
        if fid not in findings:
            errors.append(f"verdicts/{path.name}: no candidate with id {fid}")
            continue
        if v.get("verdict") not in VERDICTS:
            errors.append(f"verdicts/{path.name}: bad verdict {v.get('verdict')!r}")
            continue
        if not str(v.get("refutation_attempt", "")).strip():
            errors.append(f"verdicts/{path.name}: refutation_attempt is empty")
            continue
        verdicts[fid] = v

    for fid, f in findings.items():
        v = verdicts.get(fid)
        if v is None:
            if f["tier"] in MUST_VERIFY:
                errors.append(f"{fid}: {f['tier']} findings need a verifier verdict")
                continue
            # a reviewer cannot vouch for its own finding
            f["verdict"] = "PLAUSIBLE"
            f["refutation_attempt"] = UNSAMPLED
            continue
        f["verdict"] = v["verdict"]
        f["refutation_attempt"] = v["refutation_attempt"].strip()
        if v["verdict"] == "PLAUSIBLE" and f["severity"] != "nit":
            before = f["severity"]
            f["severity"] = downgrade(before)
            f["refutation_attempt"] += f"（severity 由 {before} 降为 {f['severity']}）"

    # a mechanical fix counts as applied only once the fix auditor has seen it
    fixes_dir = out / "fixes"
    applied, outcome = set(), {}
    if fixes_dir.is_dir():
        for path in sorted(fixes_dir.glob("round-*.json"), key=round_no):
            for a in json.loads(path.read_text(encoding="utf-8")).get("applied", []):
                applied.add(a.get("id"))
        for path in sorted(fixes_dir.glob("audit-round-*.json"), key=round_no):
            for v in json.loads(path.read_text(encoding="utf-8")).get("verdicts", []):
                outcome[v.get("id")] = v.get("outcome")
    for fid, f in findings.items():
        if fid in applied:
            f.setdefault("fix", {})["auto_applied"] = outcome.get(fid) == "addressed"

    if errors:
        for e in errors:
            print(f"merge: {e}", file=sys.stderr)
        raise SystemExit(1)

    order = sorted(findings.values(), key=lambda f: (
        TIERS.index(f["tier"]), SEVERITIES.index(f["severity"]),
        VERDICTS.index(f["verdict"]), f["id"]))
    (out / "findings.json").write_text(
        json.dumps(order, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = {t: {s: 0 for s in SEVERITIES} for t in TIERS}
    refuted = 0
    for f in order:
        if f["verdict"] == "REFUTED":
            refuted += 1
        else:
            counts[f["tier"]][f["severity"]] += 1
    summary = {"n_findings": len(order), "n_refuted": refuted,
               "by_tier": {t: c for t, c in counts.items() if any(c.values())}}
    (out / "finding_counts.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'tier':10s} " + " ".join(f"{s:>7s}" for s in SEVERITIES))
    for t, c in summary["by_tier"].items():
        print(f"{t:10s} " + " ".join(f"{c[s]:7d}" for s in SEVERITIES))
    print(f"merged {len(order)} findings ({refuted} refuted) -> {out / 'findings.json'}")


if __name__ == "__main__":
    main()
