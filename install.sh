#!/usr/bin/env bash
# One-time machine setup: uv, Graphify CLI + Claude Code skill, graphify-init + research-init on PATH.
#
#   ./install.sh                         # pinned Graphify version
#   GRAPHIFY_VERSION=latest ./install.sh # newest release
#
# Safe to re-run (also how you update after a `git pull`).
set -euo pipefail

GRAPHIFY_VERSION=${GRAPHIFY_VERSION:-0.9.95}
ROOT=$(cd "$(dirname "$0")" && pwd)
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
ORIG_PATH=$PATH
export PATH="$BIN:$PATH"

# 1. uv (Python tool installer, isolated venvs)
if ! command -v uv >/dev/null; then
  echo "[install] installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# 2. Graphify CLI (PyPI package is "graphifyy", repo github.com/Graphify-Labs/graphify)
if [ "$GRAPHIFY_VERSION" = latest ]; then
  uv tool install --upgrade "graphifyy[mcp]"
else
  uv tool install "graphifyy[mcp]==$GRAPHIFY_VERSION"
fi

# 3. /graphify skill for Claude Code (~/.claude/skills/graphify)
graphify install >/dev/null
echo "[install] $(graphify --version | head -1), Claude Code skill installed"

# 4. our scripts -> ~/.local/bin (symlinks, so `git pull` updates them)
for f in "$ROOT"/bin/*; do
  chmod +x "$f"
  ln -sfn "$f" "$BIN/$(basename "$f")"
  echo "[install] linked $(basename "$f") -> $BIN"
done

if ! printf '%s' "$ORIG_PATH" | tr ':' '\n' | grep -qx "$BIN"; then
  echo "[install] NOTE: add $BIN to your PATH, e.g.  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
fi

echo "[install] done. Code map: graphify-init (then /graphify . in Claude Code). Research: research-init"
