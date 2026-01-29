#!/usr/bin/env bash
# SessionStart hook: inject workflow context and surface active feature

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_ROOT="$(detect_project_root)"

# Find active feature (most recently modified .meta.json with status=active)
find_active_feature() {
    local features_dir="${PROJECT_ROOT}/docs/features"

    if [[ ! -d "$features_dir" ]]; then
        return 1
    fi

    # Find .meta.json files and check for active status
    # Use portable find + python for cross-platform compatibility (macOS + Linux)
    local latest_meta
    latest_meta=$(python3 -c "
import os
import json
import sys

features_dir = '$features_dir'
active_features = []

for root, dirs, files in os.walk(features_dir):
    if '.meta.json' in files:
        meta_path = os.path.join(root, '.meta.json')
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            # Only consider active features
            if meta.get('status', 'active') == 'active':
                mtime = os.path.getmtime(meta_path)
                active_features.append((mtime, meta_path))
        except:
            pass

if active_features:
    # Sort by modification time, most recent first
    active_features.sort(reverse=True)
    print(active_features[0][1])
" 2>/dev/null)

    if [[ -z "$latest_meta" ]]; then
        return 1
    fi

    echo "$latest_meta"
}

# Parse feature metadata
parse_feature_meta() {
    local meta_file="$1"

    if [[ ! -f "$meta_file" ]]; then
        return 1
    fi

    # Extract fields using python (more reliable than bash JSON parsing)
    python3 -c "
import json
import sys
with open('$meta_file') as f:
    meta = json.load(f)
    print(meta.get('id', 'unknown'))
    print(meta.get('name', 'unknown'))
    print(meta.get('mode', 'Standard'))
    print(meta.get('worktree', ''))
" 2>/dev/null
}

# Detect current phase from existing artifacts
detect_phase() {
    local feature_dir="$1"

    if [[ -f "${feature_dir}/tasks.md" ]]; then
        echo "implementing"
    elif [[ -f "${feature_dir}/plan.md" ]]; then
        echo "creating-tasks"
    elif [[ -f "${feature_dir}/design.md" ]]; then
        echo "creating-plan"
    elif [[ -f "${feature_dir}/spec.md" ]]; then
        echo "designing"
    elif [[ -f "${feature_dir}/brainstorm.md" ]]; then
        echo "specifying"
    else
        echo "brainstorming"
    fi
}

# Get next command suggestion based on current phase
get_next_command() {
    local phase="$1"

    case "$phase" in
        "brainstorming") echo "/brainstorm" ;;
        "specifying") echo "/specify" ;;
        "designing") echo "/design" ;;
        "creating-plan") echo "/create-plan" ;;
        "creating-tasks") echo "/create-tasks" ;;
        "implementing") echo "/implement" ;;
        "verifying") echo "/verify" ;;
        *) echo "/verify" ;;
    esac
}

# Check if cwd matches worktree
check_worktree_mismatch() {
    local worktree="$1"
    local cwd="$2"

    # Skip check if no worktree defined
    if [[ -z "$worktree" ]]; then
        return 1
    fi

    # Resolve worktree to absolute path
    local worktree_abs
    worktree_abs=$(cd "${PROJECT_ROOT}" && cd "${worktree}" 2>/dev/null && pwd) || return 1

    # Compare with cwd
    if [[ "$cwd" != "$worktree_abs" ]]; then
        return 0  # Mismatch
    fi

    return 1  # Match
}

# Build context message
build_context() {
    local context=""
    local meta_file
    local cwd
    cwd=$(pwd)

    meta_file=$(find_active_feature)

    if [[ -n "$meta_file" ]]; then
        local feature_dir
        feature_dir=$(dirname "$meta_file")

        # Parse metadata
        local meta_output
        meta_output=$(parse_feature_meta "$meta_file")

        if [[ -n "$meta_output" ]]; then
            local id name mode worktree phase next_cmd
            id=$(echo "$meta_output" | sed -n '1p')
            name=$(echo "$meta_output" | sed -n '2p')
            mode=$(echo "$meta_output" | sed -n '3p')
            worktree=$(echo "$meta_output" | sed -n '4p')
            phase=$(detect_phase "$feature_dir")
            next_cmd=$(get_next_command "$phase")

            context="You're working on feature ${id}-${name} (${mode} mode).\n"
            context+="Current phase: ${phase}\n"

            # Check worktree mismatch and add warning
            if [[ -n "$worktree" ]]; then
                context+="Worktree: ${worktree}\n"
                if check_worktree_mismatch "$worktree" "$cwd"; then
                    context+="\n⚠️  WARNING: You are not in the feature worktree.\n"
                    context+="   Current directory: ${cwd}\n"
                    context+="   Feature worktree: ${worktree}\n"
                    context+="   Consider: cd ${worktree}\n"
                fi
            fi

            # Add next command suggestion
            context+="\nNext suggested command: ${next_cmd}\n"
        fi
    fi

    # Always include workflow overview
    context+="\nAvailable commands: /brainstorm → /specify → /design → /create-plan → /create-tasks → /implement → /verify → /finish (/create-feature as alternative)"

    if [[ -z "$meta_file" ]]; then
        context+="\n\nNo active feature. Use /brainstorm to start exploring ideas, or /create-feature to skip brainstorming."
    fi

    echo "$context"
}

# Main
main() {
    local context
    context=$(build_context)

    local escaped_context
    escaped_context=$(escape_json "$context")

    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${escaped_context}"
  }
}
EOF

    exit 0
}

main
