#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install gh CLI if not present
if ! command -v gh &>/dev/null; then
  echo "Installing gh CLI..."
  apt-get update -qq
  apt-get install -y -qq gh
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$CLAUDE_PROJECT_DIR"
uv sync --group dev
