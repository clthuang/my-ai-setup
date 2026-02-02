#!/usr/bin/env bash
# PreToolUse hook: guard git commits

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_ROOT="$(detect_project_root)"

# Read tool input from stdin (with timeout to prevent indefinite blocking)
# Uses gtimeout (macOS with coreutils) or timeout (Linux), falls back to cat
read_tool_input() {
    local input timeout_cmd=""

    # Find available timeout command
    if command -v gtimeout &>/dev/null; then
        timeout_cmd="gtimeout 5"
    elif command -v timeout &>/dev/null; then
        timeout_cmd="timeout 5"
    fi

    if [[ -n "$timeout_cmd" ]]; then
        input=$($timeout_cmd cat || echo '{}')
    else
        # Fallback: read without timeout (stdin from Claude should close promptly)
        input=$(cat)
    fi

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
# Protected: main (releases), master (legacy)
is_protected_branch() {
    local branch="$1"
    [[ "$branch" == "main" || "$branch" == "master" ]]
}

# Check if commit touches protected iflow plugin directory
touches_protected_iflow() {
    local command="$1"
    # Check if any staged files are in plugins/iflow/ (not plugins/iflow-dev/)
    local staged_files
    staged_files=$(run_git_in_command_context "$command" diff --cached --name-only 2>/dev/null || echo "")

    # Check for plugins/iflow/ but not plugins/iflow-dev/
    if echo "$staged_files" | grep -q '^plugins/iflow/' && ! echo "$staged_files" | grep -q '^plugins/iflow-dev/'; then
        return 0
    fi
    # Also check if only iflow (not iflow-dev) files are staged
    if echo "$staged_files" | grep '^plugins/iflow/' | grep -v '^plugins/iflow-dev/' | grep -q .; then
        return 0
    fi
    return 1
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

# Output: ask user to confirm
output_ask() {
    local reason="$1"
    local escaped
    escaped=$(escape_json "$reason")
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
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

    # IFLOW_RELEASE bypass - allow release script to modify protected files
    if [[ "${IFLOW_RELEASE:-}" == "1" ]]; then
        output_allow "Release mode: bypassing iflow protection"
        exit 0
    fi

    # Check if commit touches protected plugins/iflow/ directory
    if touches_protected_iflow "$command"; then
        output_block "Changes to plugins/iflow/ are blocked. The iflow plugin is production-only and updated via release script. Please make your changes in plugins/iflow-dev/ instead. To bypass (release only): IFLOW_RELEASE=1 git commit ..."
        exit 0
    fi

    # Check branch for the command's target directory
    local branch
    branch=$(get_branch_for_command "$command")

    if is_protected_branch "$branch"; then
        output_allow "Reminder: Committing directly to '${branch}'. Consider using a feature branch for larger changes."
        exit 0
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
