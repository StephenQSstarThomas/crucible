#!/usr/bin/env bash
# Install CRUCIBLE into ~/.claude so /crucible works from any Overleaf repo.
#
# Symlinks (not copies) so `git pull` in this repo updates the installed
# version immediately. Use --copy for machines where symlinks are awkward.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MODE="symlink"
[[ "${1:-}" == "--copy" ]] && MODE="copy"

mkdir -p "$DEST/skills" "$DEST/agents"

link() {
    local from="$1" to="$2"
    if [[ -e "$to" || -L "$to" ]]; then
        if [[ -L "$to" && "$(readlink "$to")" == "$from" ]]; then
            echo "  = $(basename "$to") (already linked)"
            return
        fi
        echo "  ! $(basename "$to") exists and is not our link -- skipping"
        echo "    remove it manually if you want CRUCIBLE's version"
        return
    fi
    if [[ "$MODE" == "copy" ]]; then
        cp -r "$from" "$to"
        echo "  + $(basename "$to") (copied)"
    else
        ln -s "$from" "$to"
        echo "  + $(basename "$to")"
    fi
}

echo "CRUCIBLE -> $DEST  ($MODE)"

echo
echo "skills:"
for d in "$SRC"/skills/*/; do
    link "${d%/}" "$DEST/skills/$(basename "${d%/}")"
done

echo
echo "agents:"
for f in "$SRC"/agents/*.md; do
    link "$f" "$DEST/agents/$(basename "$f")"
done

echo
echo "checking dependencies:"
missing=0
for cmd in python3 tectonic; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "  ok  $cmd  ($(command -v "$cmd"))"
    else
        echo "  !!  $cmd  NOT FOUND"
        missing=1
    fi
done
python3 - <<'PY'
mods = {"fitz": "pymupdf", "PIL": "pillow", "yaml": "pyyaml"}
for mod, pkg in mods.items():
    try:
        __import__(mod)
        print(f"  ok  python:{pkg}")
    except ImportError:
        print(f"  !!  python:{pkg}  NOT FOUND  (pip install {pkg})")
PY

if [[ "$missing" == "1" ]]; then
    echo
    echo "tectonic is required to compile the paper. Without it CRUCIBLE can"
    echo "still run source-level tiers, but everything that inspects the"
    echo "rendered PDF (page count, checklist presence, figure DPI) is skipped."
    echo "Install: https://tectonic-typesetting.github.io/"
fi

echo
echo "done. Try:  /crucible ~/path/to/paper --venue neurips-2026"
