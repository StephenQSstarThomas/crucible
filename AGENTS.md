# CRUCIBLE repository guidance

- Treat `agents/*.md` as the portable source of truth for reviewer roles. After changing one, run `python3 bin/sync_codex_agents.py` and commit the generated `.codex/agents/*.toml` files.
- Validate both skills with `quick_validate.py`, run `python3 -m unittest discover -s tests -p 'test_*.py'`, then run the smoke test against a real TeX source package.
- Deterministic collectors under `bin/` gather facts only. Scientific judgments, severity, authorship classification, and fixes belong to agents.
- Parallel agents write only their own files (`candidates/<TIER>.json`, `verdicts/<id>.json`, `panel/<role>.md`); `bin/merge_findings.py` does the merge. Do not let two agents edit one file.
- A run is incomplete without `REVISION_PLAN.md`; `bin/validate_report.py` checks it covers every open blocker/major finding and cites no REFUTED one.
- Keep manuscripts and validation runs on third-party papers out of git (`validation/`, root `*.zip` are ignored).
- A report is incomplete unless its first section contains exactly one of `人类主导`, `AI深度参与`, or `全AI`, with supporting evidence, counterevidence, missing provenance, and the non-forensic limitation.
- Never infer fabricated data without experiment artifacts. Never infer fully-AI authorship from style alone.
