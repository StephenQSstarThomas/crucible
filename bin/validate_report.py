#!/usr/bin/env python3
"""Validate final CRUCIBLE output invariants that prompts alone cannot ensure."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LABELS = ("人类主导", "AI深度参与", "全AI")
FIRST_HEADING = "写作来源判断（非取证结论）"


def fail(message: str) -> None:
    raise SystemExit(f"crucible report validation failed: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", help="CRUCIBLE output directory")
    args = parser.parse_args()
    out = Path(args.out)

    assessment_path = out / "authorship_assessment.json"
    report_path = out / "REPORT.md"
    if not assessment_path.is_file():
        fail("authorship_assessment.json is missing")
    if not report_path.is_file():
        fail("REPORT.md is missing")

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

    report = report_path.read_text(encoding="utf-8")
    headings = re.findall(r"^##\s+(.+?)\s*$", report, re.M)
    if not headings or headings[0] != FIRST_HEADING:
        got = headings[0] if headings else None
        fail(f"first level-2 heading must be {FIRST_HEADING!r}, got {got!r}")
    first_end = re.search(r"^##\s+", report[report.find("\n## ") + 4:], re.M)
    first_section = (report if first_end is None else
                     report[:report.find("\n## ") + 4 + first_end.start()])
    if label not in first_section:
        fail(f"first report section does not contain assessment label {label}")
    for marker in ("支持", "反对", "缺失证据", "方法限制"):
        if marker not in first_section:
            fail(f"first report section is missing {marker!r}")

    print(f"report contract valid: authorship={label}, first section={FIRST_HEADING}")


if __name__ == "__main__":
    main()
