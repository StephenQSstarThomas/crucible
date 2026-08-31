#!/usr/bin/env bash
# CRUCIBLE smoke test: run every collector against a paper and assert the
# facts files are well-formed. Does not assert specific findings -- those
# depend on the paper. Asserts the machinery works.
#
#   tests/smoke.sh <paper-repo-or-zip> [venue-slug]
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPER="${1:?usage: tests/smoke.sh <paper> [venue]}"
VENUE="${2:-}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [[ "$PAPER" == *.zip ]]; then
    unzip -q "$PAPER" -d "$WORK/paper"
    PAPER="$WORK/paper"
fi

OUT="$WORK/out"
echo "== collecting =="
if [[ -n "$VENUE" ]]; then
    python3 "$SRC/bin/collect.py" "$PAPER" -o "$OUT" --venue "$VENUE" >"$WORK/log" 2>&1
else
    python3 "$SRC/bin/collect.py" "$PAPER" -o "$OUT" >"$WORK/log" 2>&1
fi
tail -14 "$WORK/log"

echo
echo "== asserting =="
fail=0
ok()   { printf '  ok   %s\n' "$1"; }
bad()  { printf '  FAIL %s\n' "$1"; fail=1; }

need_json() {
    local f="$OUT/facts/$1"
    if [[ ! -f "$f" ]]; then bad "$1 missing"; return; fi
    if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null; then
        ok "$1 is valid JSON"
    else
        bad "$1 is not valid JSON"
    fi
}

for f in ingest.json authorship.json tables.json refs.json numbers.json forensics.json _summary.json; do
    need_json "$f"
done
[[ -n "$VENUE" ]] && need_json venue.json

# render is optional (needs a TeX engine) but if it ran it must be coherent
if [[ -f "$OUT/facts/render.json" ]]; then
    need_json render.json
    if python3 - "$OUT" <<'PY'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
r = json.load(open(out / "facts" / "render.json"))
if not r.get("compiled"):
    sys.exit(1)
pdf = r["pdf"]
assert pdf["n_pages"] > 0, "zero pages"
pngs = list((out / "preview").glob("page-*.png"))
assert len(pngs) == pdf["n_pages"], f"{len(pngs)} previews vs {pdf['n_pages']} pages"
PY
    then ok "render: PDF produced, one preview PNG per page"
    else bad "render: compiled but preview/page count mismatch (or compile failed)"
    fi
else
    echo "  skip render.json (no TeX engine?)"
fi

# structural invariants the collectors must always satisfy
python3 - "$OUT" <<'PY' && ok "structural invariants hold" || bad "structural invariants violated"
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
ing = json.load(open(out / "facts" / "ingest.json"))
tab = json.load(open(out / "facts" / "tables.json"))
num = json.load(open(out / "facts" / "numbers.json"))
auth = json.load(open(out / "facts" / "authorship.json"))

assert ing["n_lines"] > 0, "flattened document is empty"
assert ing["root_tex"], "no root tex recorded"
assert len(ing["linemap"]) == ing["n_lines"], "linemap does not cover the document"
assert auth["source_scope"] == "tex-source", "unexpected authorship evidence scope"
assert isinstance(auth["direct_disclosures"], list)
assert isinstance(auth["generation_artifacts"], list)
assert auth["limitations"], "authorship limitations must be explicit"
# every table row must have cells or be a rule
for t in tab:
    for r in t["rows"]:
        assert r["kind"] in ("data", "rule"), r["kind"]
        if r["kind"] == "data":
            assert r["cells"], "data row with no cells"
# a \ding{55} must never be read as the number 55
for t in tab:
    for r in t["rows"]:
        for c in r.get("cells", []):
            assert c["number"] != 7055, "xmark macro leaked into the numeric ledger"
# anchoring output must reference real tables
labels = {t.get("label") for t in tab}
for u in num["unanchored_measurements"]:
    assert u["near_table_ref"] in labels, f"unknown table {u['near_table_ref']}"
print(f"    {ing['n_lines']} lines, {len(tab)} tables, "
      f"{num['n_measurements']} measurements, "
      f"{len(num['unanchored_measurements'])} unanchored")
PY

echo
if [[ "$fail" == "0" ]]; then
    echo "SMOKE TEST PASSED"
else
    echo "SMOKE TEST FAILED"
    exit 1
fi
