from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReportContractTests(unittest.TestCase):
    def make_output(self, first_heading="写作来源判断（非取证结论）"):
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
            "## 摘要\n",
            encoding="utf-8",
        )
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


if __name__ == "__main__":
    unittest.main()
