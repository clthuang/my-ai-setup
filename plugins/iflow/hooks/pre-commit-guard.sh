#!/usr/bin/env bash
# PreToolUse hook: guard git commits

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_ROOT="$(detect_project_root)"

# Read tool input from stdin
read_tool_input() {
    local input
    input=$(cat)

    # Extract command from JSON input
    # Input format: {"tool_name": "Bash", "tool_input": {"command": "..."}}
    echo "$input" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    print(cmd)
except:
    print('')
" 2>/dev/null
}

# Get git branch for the command's target directory
get_branch_for_command() {
    local command="$1"
    run_git_in_command_context "$command" rev-parse --abbrev-ref HEAD || echo ""
}

# Check if on protected branch
is_protected_branch() {
    local branch="$1"
    [[ "$branch" == "main" || "$branch" == "master" ]]
}

# Check if test files exist in the project
has_test_files() {
    local patterns=(
        "test_*.py"
        "*_test.py"
        "*.test.ts"
        "*.test.js"
        "*.test.tsx"
        "*.test.jsx"
        "*_test.go"
        "Test*.java"
        "*Test.java"
        "*_spec.rb"
        "*.spec.ts"
        "*.spec.js"
    )

    for pattern in "${patterns[@]}"; do
        if find "${PROJECT_ROOT}" -name "$pattern" -type f 2>/dev/null | head -1 | grep -q .; then
            return 0
        fi
    done

    return 1
}

# Output: allow the action
output_allow() {
    local context="${1:-Allowed}"
    local escaped
    escaped=$(escape_json "$context")
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "${escaped}"
  }
}
EOF
}

# Output: block the action
output_block() {
    local reason="$1"
    local escaped
    escaped=$(escape_json "$reason")
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "${escaped}"
  }
}
EOF
}

# Main
main() {
    local command
    command=$(read_tool_input)

    # Only process git commit commands
    if [[ ! "$command" =~ git[[:space:]]+commit ]]; then
        output_allow
        exit 0
    fi

    # Check branch for the command's target directory
    local branch
    branch=$(get_branch_for_command "$command")

    if is_protected_branch "$branch"; then
        output_block "Direct commits to ${branch} branch are blocked. Create a feature branch first:
  git checkout -b feature/your-feature-name

Or use /create-feature for the full workflow."
        exit 2
    fi

    # Check for test files and remind
    if has_test_files; then
        output_allow "Reminder: Test files exist in this project. Have you run the tests?"
    else
        output_allow
    fi

    exit 0
}

main
