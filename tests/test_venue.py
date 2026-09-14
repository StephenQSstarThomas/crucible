from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VenueRuleTests(unittest.TestCase):
    def venue_facts(self, preamble: str, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "paper"
            out = Path(tmp) / "out"
            paper.mkdir()
            (paper / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\usepackage{iclr2027_conference}\n" + preamble +
                "\\begin{document}\n" + body + "\n\\end{document}\n",
                encoding="utf-8",
            )
            for script, extra in (("ingest.py", []),
                                  ("venue.py", ["--venue", "iclr-2027"])):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "bin" / script), str(paper),
                     "-o", str(out), *extra],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            facts = json.loads((out / "facts" / "venue.json").read_text())
        return {h["id"]: h for h in facts["high_frequency_failures"]}

    def test_active_finalcopy_and_missing_statement_hit(self):
        hits = self.venue_facts("\\iclrfinalcopy\n", "\\section{Intro}\nText.")
        self.assertTrue(hits["finalcopy-enabled"]["hit"])
        self.assertTrue(hits["missing-ai-use-statement"]["hit"])

    def test_commented_finalcopy_and_present_statement_pass(self):
        hits = self.venue_facts(
            "% \\iclrfinalcopy\n",
            "\\section{Intro}\nText.\n\\section*{AI Use Statement}\nNone.")
        self.assertFalse(hits["finalcopy-enabled"]["hit"])
        self.assertFalse(hits["missing-ai-use-statement"]["hit"])


if __name__ == "__main__":
    unittest.main()
