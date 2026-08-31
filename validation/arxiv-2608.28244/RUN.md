# Validation run manifest

- Target: `https://arxiv.org/abs/2608.28244`
- arXiv submitted date: 2026-08-28
- Source endpoint: `https://arxiv.org/e-print/2608.28244`
- Source SHA-256: `dd12fdbf576d8c9a9f7e068e4924ce2243eb761e7186bbbfad53df1527c7aeed`
- Root: `main.tex` (single root)
- Mode: public preprint, no venue tier, no fixes applied

## Commands

```bash
python3 bin/collect.py <source-dir> -o <out-dir>
python3 bin/authorship.py <source-dir> -o <out-dir>
python3 bin/validate_report.py validation/arxiv-2608.28244
```

Independent software check at public commit `feeccfb10fb424beaac3c6da4530128fc9cff585`:

```bash
PYTHONPATH=src python3 -m pytest -q
# 439 passed, 1 failed, 22 subtests passed
```

The remaining failure calls macOS `/usr/bin/xcrun` while the test patches the platform to Darwin on a Linux host; it was treated as an environment-mismatch check, not evidence against a scientific claim.

## Collector summary

- 1519 flattened lines, 7 TeX files, 28 sections, 14 floats
- clean 24-page PDF; no LaTeX errors, undefined refs/cites, or >5pt overfull boxes
- 9 parsed tables, 327 prose numbers, 64 distinct table values
- 11 numeric-anchor candidates, all traced; the apparent group was a nearest-reference false positive
- 1 explicit AI-writing disclosure section; 0 high-specificity generation leaks
