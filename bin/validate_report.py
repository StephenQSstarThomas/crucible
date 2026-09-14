#!/usr/bin/env python3
"""Validate final CRUCIBLE output invariants that prompts alone cannot ensure."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LABELS = ("人类主导", "AI深度参与", "全AI")
FIRST_HEADING = "写作来源判断（非取证结论）"
FINDING_ID = re.compile(
    r"\b(?:P0-BUILD|P0-INTEG|P0-SURF|P1-CLAIM|P2-RIGOR|P3-DEF|P4-PRES|P5-PANEL|V-VENUE)"
    r"-[0-9]{3}\b")
PREDICTION_NOTE = "预测，非事实"


def fail(message: str) -> None:
    raise SystemExit(f"crucible report validation failed: {message}")


def check_authorship(out: Path, report: str) -> str:
    assessment_path = out / "authorship_assessment.json"
    if not assessment_path.is_file():
        fail("authorship_assessment.json is missing")
    try:
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid authorship_assessment.json: {exc}")
    label = assessment.get("label")
    if label not in LABELS:
        fail(f"label must be exactly one of {LABELS}, got {label!r}")
    for key in ("summary_zh", "supporting_signals", "counter_signals",
                "unavailable_evidence", "limitations_zh"):
        if key not in assessment:
            fail(f"authorship assessment is missing {key}")
    if not assessment["limitations_zh"].strip():
        fail("authorship limitations must not be empty")

    headings = re.findall(r"^##\s+(.+?)\s*$", report, re.M)
    if not headings or headings[0] != FIRST_HEADING:
        got = headings[0] if headings else None
        fail(f"first level-2 heading must be {FIRST_HEADING!r}, got {got!r}")
    start = re.search(r"^##\s+", report, re.M).start()
    nxt = re.search(r"^##\s+", report[start + 3:], re.M)
    first_section = report[start:] if nxt is None else report[start:start + 3 + nxt.start()]
    if label not in first_section:
        fail(f"first report section does not contain assessment label {label}")
    for marker in ("支持", "反对", "缺失证据", "方法限制"):
        if marker not in first_section:
            fail(f"first report section is missing {marker!r}")
    return label


def load_findings(out: Path) -> list[dict]:
    path = out / "findings.json"
    if not path.is_file():
        fail("findings.json is missing (run bin/merge_findings.py)")
    try:
        findings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid findings.json: {exc}")
    if not isinstance(findings, list):
        fail("findings.json must be a JSON array")
    ids = [f.get("id") for f in findings]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        fail(f"duplicate finding ids: {dup}")
    return findings


def check_refuted_absent(report: str, findings: list[dict]) -> None:
    refuted = {f["id"] for f in findings if f.get("verdict") == "REFUTED"}
    leaked = sorted(refuted & set(FINDING_ID.findall(report)))
    if leaked:
        fail(f"REPORT.md mentions REFUTED findings {leaked}; keep them in findings.json only")


def check_revision_plan(out: Path, findings: list[dict]) -> int:
    path = out / "REVISION_PLAN.md"
    if not path.is_file():
        fail("REVISION_PLAN.md is missing")
    plan = path.read_text(encoding="utf-8")
    by_id = {f["id"]: f for f in findings}

    cited = set(FINDING_ID.findall(plan))
    unknown = sorted(cited - set(by_id))
    if unknown:
        fail(f"REVISION_PLAN.md cites unknown findings {unknown}")
    refuted = sorted(i for i in cited if by_id[i].get("verdict") == "REFUTED")
    if refuted:
        fail(f"REVISION_PLAN.md cites REFUTED findings {refuted}")

    required = sorted(
        f["id"] for f in findings
        if f.get("verdict") != "REFUTED"
        and f.get("severity") in ("blocker", "major")
        and not (f.get("fix") or {}).get("auto_applied"))
    missing = [i for i in required if i not in cited]
    if missing:
        fail(f"REVISION_PLAN.md omits open blocker/major findings {missing}")

    if (out / "panel").is_dir() and any((out / "panel").glob("*.md")):
        if PREDICTION_NOTE not in plan:
            fail(f"REVISION_PLAN.md must label panel-derived items as {PREDICTION_NOTE!r}")
    return len(required)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", help="CRUCIBLE output directory")
    args = parser.parse_args()
    out = Path(args.out)

    report_path = out / "REPORT.md"
    if not report_path.is_file():
        fail("REPORT.md is missing")
    report = report_path.read_text(encoding="utf-8")

    label = check_authorship(out, report)
    findings = load_findings(out)
    check_refuted_absent(report, findings)
    n_open = check_revision_plan(out, findings)

    print(f"report contract valid: authorship={label}, "
          f"{len(findings)} findings, {n_open} open blocker/major in revision plan")


if __name__ == "__main__":
    main()
