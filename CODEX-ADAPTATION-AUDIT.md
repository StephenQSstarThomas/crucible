# Codex adaptation and logic audit

## Baseline findings

1. **The repository was Claude-shaped, not Codex-ready.** `install.sh` targeted `~/.claude`, usage examples invoked `/crucible`, and reviewer roles existed only as Markdown agent manifests. Codex requires discoverable skills plus TOML custom agents in `.codex/agents` or `~/.codex/agents`.
2. **Collector failures could be reported as success.** `render.py` exited zero even when no PDF was produced, and `collect.py` printed required-stage failures but always returned zero. The smoke test further masked the command status with `|| true`.
3. **No authorship-provenance lane existed.** The previous pipeline reviewed build, consistency, rigor, claims, novelty, figures, and venue rules, but had no structured evidence collection or report contract for the requested three-way writing-origin assessment.
4. **The report shape was prompt-only.** Nothing machine-checked that a required section appeared, appeared first, or used one of the allowed labels.
5. **Deterministic numeric anchoring is deliberately heuristic.** It is high-yield but can bind a paragraph to an older nearby table. The arXiv validation produced 11 such candidates; adversarial review refuted the group. Collector output must remain candidate evidence, never an automatic finding.
6. **Stylometry is not a reliable AI detector.** Section statistics can support a human review, but style cannot distinguish human prose, AI rewriting, or heavily edited AI drafts. Direct disclosure and provenance must dominate.

## Implemented adaptation

- Default installer now targets Codex, with `--claude` retained as an explicit compatibility mode.
- Sixteen `.codex/agents/*.toml` files are generated from the portable `agents/*.md` source through `bin/sync_codex_agents.py`; `--check` detects drift.
- The orchestrator uses Codex skill invocation (`$crucible`) and Codex custom-agent names.
- `AGENTS.md` records repository invariants and verification commands.
- `bin/authorship.py`, `rubrics/A-AUTHORSHIP.md`, an assessor role, and a JSON schema implement the three-label evidence lane.
- `bin/validate_report.py` enforces that the first report section is the authorship assessment and that its label is exactly `人类主导`, `AI深度参与`, or `全AI`.
- Required collector failures now propagate nonzero; failed TeX compilation is no longer silently marked successful.
- Smoke and unit tests cover collector exit status, topic-vs-writing disclosure, wrapped TeX disclosure, full-generation wording, agent sync, installation, and report ordering.

## Remaining boundaries

- The final three-way label is an evidence-backed model judgment, not a calibrated statistical detector; no percentage is emitted.
- `--evidence` makes experiment artifacts available and inventories them, but scientific reconciliation still requires the integrity agent to inspect the actual records. Artifact filenames alone do not prove or disprove fabrication.
- Novelty and closest-work checks require current primary-source web research; deterministic scripts cannot establish novelty.
- A source-only run with `--skip-render` is supported but cannot validate page layout, figure legibility, PDF metadata, or final-artifact omissions. A complete report must disclose those missing lanes.
- P2/P3 judgments depend on domain context and must retain evidence, counterevidence, and uncertainty; schemas and tests cannot make those judgments deterministic.

## Verification evidence

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 7 passed.
- `python3 bin/sync_codex_agents.py --check`: 16 agents in sync.
- Both skills pass the Codex skill validator.
- Isolated `${CODEX_HOME}` copy-install succeeds with two skills and sixteen agents.
- Real TeX smoke test with venue facts passes every collector and structural invariant.
- arXiv:2608.28244 compiles cleanly to 24 pages; its report, authorship assessment, and 13 structured findings pass their contracts.
