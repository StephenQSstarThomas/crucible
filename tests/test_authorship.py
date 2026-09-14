from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_collector(script: str, paper: Path, out: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "bin" / script), str(paper), "-o", str(out)],
        capture_output=True,
        text=True,
    )


class AuthorshipCollectorTests(unittest.TestCase):
    def collect(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "paper"
            out = Path(tmp) / "out"
            paper.mkdir()
            (paper / "main.tex").write_text(
                "\\documentclass{article}\n"
                "\\title{A Test}\n"
                "\\begin{document}\n"
                "\\maketitle\n" + body + "\n\\end{document}\n",
                encoding="utf-8",
            )
            ingest = run_collector("ingest.py", paper, out)
            self.assertEqual(ingest.returncode, 0, ingest.stderr)
            auth = run_collector("authorship.py", paper, out)
            self.assertEqual(auth.returncode, 0, auth.stderr)
            return json.loads((out / "facts" / "authorship.json").read_text())

    def test_research_topic_is_not_a_writing_disclosure(self):
        facts = self.collect(
            "\\section{Method}\n"
            "We evaluate ChatGPT and Claude as large language model baselines."
        )
        self.assertEqual(facts["direct_disclosures"], [])
        self.assertTrue(facts["ai_term_contexts"])

    def test_substantial_writing_disclosure_is_collected(self):
        facts = self.collect(
            "\\section{AI Use Statement}\n"
            "The authors used ChatGPT to draft and revise substantial portions "
            "of the manuscript."
        )
        self.assertEqual(len(facts["direct_disclosures"]), 1)
        self.assertFalse(
            facts["direct_disclosures"][0]["full_generation_language"]
        )
        self.assertEqual(len(facts["disclosure_sections"]), 1)

    def test_wrapped_disclosure_is_collected_at_section_level(self):
        facts = self.collect(
            "\\section{AI Use Statement}\n"
            "The authors used ChatGPT to assist with software implementation,\n"
            "debugging, documentation, manuscript drafting, and figure preparation."
        )
        self.assertEqual(len(facts["direct_disclosures"]), 1)
        self.assertTrue(facts["direct_disclosures"][0]["section_level"])

    def test_full_generation_language_is_distinguished(self):
        facts = self.collect(
            "\\section{Generative AI Declaration}\n"
            "The entire manuscript was generated using ChatGPT."
        )
        self.assertEqual(len(facts["direct_disclosures"]), 1)
        self.assertTrue(
            facts["direct_disclosures"][0]["full_generation_language"]
        )


class PipelineExitTests(unittest.TestCase):
    def test_missing_target_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "collect.py"),
                 str(Path(tmp) / "missing"), "-o", str(Path(tmp) / "out"),
                 "--skip-render"],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required collectors failed", result.stderr)

    def test_explicit_root_reaches_every_collector(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "paper"
            paper.mkdir()
            for name in ("main.tex", "alt.tex"):
                (paper / name).write_text(
                    "\\documentclass{article}\n\\begin{document}\n"
                    "\\section{Intro}\nText.\n\\end{document}\n",
                    encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "collect.py"), str(paper),
                 "-o", str(Path(tmp) / "out"), "--root", "alt.tex",
                 "--skip-render"],
                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
