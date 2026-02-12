#!/usr/bin/env bash
set -euo pipefail

echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

echo "Sourcing uv into current shell..."
# shellcheck source=/dev/null
source "$HOME/.local/bin/env"

echo "Installing project dependencies..."
uv sync

echo "Done. You can now run the bot with: uv run python -m src.bot.app"
