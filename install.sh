#!/usr/bin/env bash
# Make /createvid and all studio skills available in EVERY Claude Code project on this machine.
# Usage: ./install.sh            (copies skills to ~/.claude/skills and records the studio path)
#        ./install.sh --setup    (also builds the heavy toolchain via setup.sh)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST"
for s in "$ROOT"/.claude/skills/*/; do
  n=$(basename "$s")
  if [ -e "$DEST/$n" ] && [ ! -L "$DEST/$n" ] && [ "$n" != "createvid" ]; then echo "skip $n (already exists)"; continue; fi
  cp -r "$s" "$DEST/$n.tmp.$$" && rm -rf "${DEST:?}/${n:?}" && mv "$DEST/$n.tmp.$$" "$DEST/$n"
done
echo "$ROOT" > "$DEST/createvid/STUDIO_ROOT"
echo "Installed $(ls "$ROOT"/.claude/skills | wc -l) skills into $DEST. Studio root: $ROOT"
[ "$1" = "--setup" ] && bash "$ROOT/setup.sh" && for s in "$ROOT"/.claude/skills/remotion-*/; do [ -d "$s" ] && cp -rn "$s" "$DEST/" ; done
echo "Start any Claude Code chat with:  /createvid <your idea>"
