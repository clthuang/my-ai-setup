#!/usr/bin/env bash
# inject-secretary-context.sh - Inject secretary awareness at session start (aware mode only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# detect_project_root returns PWD if no project markers found
PROJECT_ROOT="$(detect_project_root)"
IFLOW_CONFIG="${PROJECT_ROOT}/.claude/iflow.local.md"
CONFIG_FILE="${PROJECT_ROOT}/.claude/secretary.local.md"

# Check YOLO mode from iflow config
YOLO=$(read_local_md_field "$IFLOW_CONFIG" "yolo_mode" "false")
if [ "$YOLO" = "true" ]; then
  cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Secretary in YOLO MODE. Use: /secretary orchestrate <desc> for full autonomous workflow, or /secretary <request> for intelligent routing."
  }
}
EOF
  exit 0
fi

# Check secretary aware mode from secretary config
if [ ! -f "$CONFIG_FILE" ]; then
  exit 0
fi
MODE=$(grep "^activation_mode:" "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | tr -d ' ' || echo "manual")
if [ "$MODE" != "aware" ]; then
  exit 0
fi

# Output hook context
cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Secretary agent available for orchestrating complex requests. For vague or multi-step tasks, consider: Task({ subagent_type: 'iflow:secretary', prompt: <user_request> })"
  }
}
EOF
