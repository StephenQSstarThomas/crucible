from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def finding(fid, severity="major", verdict="CONFIRMED", **extra):
    tier = fid.rsplit("-", 1)[0]
    base = {
        "id": fid, "tier": tier, "severity": severity, "category": "test",
        "title_zh": "测试", "summary_zh": "测试",
        "locations": [{"file": "main.tex", "line": 1}],
        "evidence": {"collector": "agent-read"}, "verdict": verdict,
    }
    base.update(extra)
    return base


class ReportContractTests(unittest.TestCase):
    def make_output(self, first_heading="写作来源判断（非取证结论）",
                    findings=None, plan=None, report_extra=""):
        temporary = tempfile.TemporaryDirectory()
        out = Path(temporary.name)
        (out / "authorship_assessment.json").write_text(json.dumps({
            "label": "AI深度参与",
            "summary_zh": "当前证据更符合 AI 深度参与。",
            "supporting_signals": [],
            "counter_signals": [],
            "unavailable_evidence": ["manuscript history"],
            "limitations_zh": "终稿文风不能可靠识别来源。",
        }, ensure_ascii=False), encoding="utf-8")
        (out / "REPORT.md").write_text(
            "# Report\n\n"
            f"## {first_heading}\n\n"
            "**档位：AI深度参与**\n\n"
            "支持信号：有。\n\n反对信号：有。\n\n"
            "缺失证据：有。\n\n方法限制：有。\n\n"
            "## 摘要\n" + report_extra,
            encoding="utf-8",
        )
        if findings is None:
            findings = [finding("P0-INTEG-001", "blocker"),
                        finding("P1-CLAIM-001", "major", "REFUTED")]
        (out / "findings.json").write_text(
            json.dumps(findings, ensure_ascii=False), encoding="utf-8")
        if plan is None:
            plan = "# 修改建议\n\n1. P0-INTEG-001：改正文数字。\n"
        (out / "REVISION_PLAN.md").write_text(plan, encoding="utf-8")
        return temporary, out

    def run_validator(self, out: Path):
        return subprocess.run(
            [sys.executable, str(ROOT / "bin" / "validate_report.py"), str(out)],
            capture_output=True, text=True)

    def test_valid_report(self):
        temporary, out = self.make_output()
        with temporary:
            result = self.run_validator(out)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_authorship_must_be_first(self):
        temporary, out = self.make_output("摘要")
        with temporary:
            result = self.run_validator(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("first level-2 heading", result.stderr)

    def test_plan_must_cover_open_blockers(self):
        temporary, out = self.make_output(plan="# 修改建议\n\n暂无。\n")
        with temporary:
            result = self.run_validator(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("P0-INTEG-001", result.stderr)

    def test_auto_applied_fix_need_not_be_planned(self):
        findings = [finding("P0-SURF-001", "major",
                            fix={"kind": "mechanical", "auto_applied": True})]
        temporary, out = self.make_output(findings=findings, plan="# 修改建议\n")
        with temporary:
            result = self.run_validator(out)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_plan_must_not_cite_refuted(self):
        temporary, out = self.make_output(
            plan="# 修改建议\n\nP0-INTEG-001\n\nP1-CLAIM-001\n")
        with temporary:
            result = self.run_validator(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REFUTED", result.stderr)

    def test_report_must_not_list_refuted(self):
        temporary, out = self.make_output(report_extra="\n### [P1-CLAIM-001] x\n")
        with temporary:
            result = self.run_validator(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REFUTED", result.stderr)

    def test_panel_items_must_be_marked_as_prediction(self):
        temporary, out = self.make_output()
        with temporary:
            (out / "panel").mkdir()
            (out / "panel" / "ac.md").write_text("# AC\n", encoding="utf-8")
            result = self.run_validator(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("预测，非事实", result.stderr)


class MergeFindingsTests(unittest.TestCase):
    def run_merge(self, out: Path):
        return subprocess.run(
            [sys.executable, str(ROOT / "bin" / "merge_findings.py"), str(out)],
            capture_output=True, text=True)

    def write(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_merges_shards_verdicts_and_downgrades_plausible(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write(out / "candidates" / "P0-SURF.part-0.json",
                       [finding("P0-SURF-001", "minor")])
            self.write(out / "candidates" / "P0-SURF.part-1.json",
                       [finding("P0-SURF-101", "major")])
            self.write(out / "candidates" / "P2-RIGOR.json",
                       [finding("P2-RIGOR-001", "major")])
            self.write(out / "verdicts" / "P0-SURF-001.json",
                       {"id": "P0-SURF-001", "verdict": "REFUTED",
                        "refutation_attempt": "专有名词，不是拼写错误。"})
            self.write(out / "verdicts" / "P0-SURF-101.json",
                       {"id": "P0-SURF-101", "verdict": "PLAUSIBLE",
                        "refutation_attempt": "依赖稿件用途。"})
            result = self.run_merge(out)
            self.assertEqual(result.returncode, 0, result.stderr)
            merged = {f["id"]: f for f in
                      json.loads((out / "findings.json").read_text())}
            counts = json.loads((out / "finding_counts.json").read_text())
        self.assertEqual(merged["P0-SURF-001"]["verdict"], "REFUTED")
        self.assertEqual(merged["P0-SURF-101"]["severity"], "minor")
        self.assertEqual(merged["P2-RIGOR-001"]["verdict"], "PLAUSIBLE")
        self.assertEqual(merged["P2-RIGOR-001"]["severity"], "major")
        self.assertEqual(counts["n_refuted"], 1)

    def test_p0_without_verdict_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write(out / "candidates" / "P0-INTEG.json",
                       [finding("P0-INTEG-001")])
            result = self.run_merge(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verifier verdict", result.stderr)

    def test_duplicate_ids_across_shards_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write(out / "candidates" / "P2-RIGOR.part-0.json",
                       [finding("P2-RIGOR-001")])
            self.write(out / "candidates" / "P2-RIGOR.part-1.json",
                       [finding("P2-RIGOR-001")])
            result = self.run_merge(out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate id", result.stderr)

    def test_fix_counts_as_applied_only_after_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write(out / "candidates" / "P2-RIGOR.json",
                       [finding("P2-RIGOR-001"), finding("P2-RIGOR-002")])
            self.write(out / "fixes" / "round-1.json", {"applied": [
                {"id": "P2-RIGOR-001"}, {"id": "P2-RIGOR-002"}]})
            self.write(out / "fixes" / "audit-round-1.json", {"verdicts": [
                {"id": "P2-RIGOR-001", "outcome": "addressed"},
                {"id": "P2-RIGOR-002", "outcome": "partial"}]})
            result = self.run_merge(out)
            self.assertEqual(result.returncode, 0, result.stderr)
            merged = {f["id"]: f for f in
                      json.loads((out / "findings.json").read_text())}
        self.assertTrue(merged["P2-RIGOR-001"]["fix"]["auto_applied"])
        self.assertFalse(merged["P2-RIGOR-002"]["fix"]["auto_applied"])


if __name__ == "__main__":
    unittest.main()
