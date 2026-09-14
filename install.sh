#!/usr/bin/env bash
# Install CRUCIBLE skills and subagents into Claude Code without the plugin system.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="symlink"
DEST="${CLAUDE_HOME:-$HOME/.claude}"

for arg in "$@"; do
    case "$arg" in
        --copy) MODE="copy" ;;
        --project) DEST="$PWD/.claude" ;;
        -h|--help)
            echo "usage: ./install.sh [--project] [--copy]"
            echo "  --project  install into ./.claude of the current directory"
            echo "  --copy     copy files instead of symlinking"
            exit 0
            ;;
        *)
            echo "unknown option: $arg" >&2
            echo "usage: ./install.sh [--project] [--copy]" >&2
            exit 2
            ;;
    esac
done

mkdir -p "$DEST/skills" "$DEST/agents"

link_one() {
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
    link_one "${d%/}" "$DEST/skills/$(basename "${d%/}")"
done

echo
echo "agents:"
for f in "$SRC"/agents/*.md; do
    link_one "$f" "$DEST/agents/$(basename "$f")"
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
    echo "tectonic is required for rendered-PDF checks. Source-level facts can"
    echo "still be collected with --skip-render, but the report must disclose"
    echo "that build, page, figure, and final-artifact checks were not run."
fi

if [[ "$MODE" == "copy" ]]; then
    echo
    echo "copy mode: the skills still need this repo for bin/ and rubrics/."
    echo "add to your shell profile:  export CRUCIBLE_HOME=\"$SRC\""
fi

echo
echo "done. Restart Claude Code, then try: /crucible ~/path/to/paper --no-fix"
