#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TH="$PROJECT_DIR/.venv/bin/th"
LOG="$PROJECT_DIR/cron.log"

if [ ! -x "$TH" ]; then
  echo "th binary not found at $TH — did you run 'pip install -e .[dev]'?" >&2
  exit 1
fi

for source in github producthunt hackernews; do
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') [$source] ===" >> "$LOG"
  "$TH" run --source "$source" --language chinese --limit 10 >> "$LOG" 2>&1 || true
done
