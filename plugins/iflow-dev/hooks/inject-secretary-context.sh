#!/usr/bin/env bash
# inject-secretary-context.sh - Inject secretary awareness at session start (aware mode only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# detect_project_root returns PWD if no project markers found
PROJECT_ROOT="$(detect_project_root)"
CONFIG_FILE="${PROJECT_ROOT}/.claude/secretary.local.md"

# Default to manual if no config - silent exit
if [ ! -f "$CONFIG_FILE" ]; then
  exit 0
fi

# Read activation_mode (default: manual)
MODE=$(grep "^activation_mode:" "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | tr -d ' ' || echo "manual")

# Only output for aware mode
if [ "$MODE" != "aware" ]; then
  exit 0
fi

# Output hook context
cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Secretary agent available for orchestrating complex requests. For vague or multi-step tasks, consider: Task({ subagent_type: 'iflow-dev:secretary', prompt: <user_request> })"
  }
}
EOF
