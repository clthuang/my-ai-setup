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
            # Only consider features with explicit active status
            # Note: planned features are excluded here — only active features are surfaced
            status = meta.get('status')
            if status == 'active':
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
with open('$meta_file') as f:
    meta = json.load(f)
    print(meta.get('id', 'unknown'))
    print(meta.get('slug', meta.get('name', 'unknown')))
    print(meta.get('mode', 'Standard'))
    print(meta.get('branch', ''))
    print(meta.get('project_id', ''))
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
        *) echo "/finish" ;;
    esac
}

# Check if current branch matches expected feature branch
check_branch_mismatch() {
    local expected_branch="$1"

    # Skip check if no branch defined
    if [[ -z "$expected_branch" ]]; then
        return 1
    fi

    # Get current branch
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null) || return 1

    # Compare branches
    if [[ "$current_branch" != "$expected_branch" ]]; then
        return 0  # Mismatch
    fi

    return 1  # Match
}

# Check if claude-md-management plugin is available
check_claude_md_plugin() {
    local cache_dir="$HOME/.claude/plugins/cache"
    # Check if any marketplace has claude-md-management cached
    if compgen -G "${cache_dir}/*/claude-md-management" > /dev/null 2>&1; then
        return 0  # Found
    fi
    return 1  # Not found
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
            local id name mode branch phase next_cmd current_branch
            id=$(echo "$meta_output" | sed -n '1p')
            name=$(echo "$meta_output" | sed -n '2p')
            mode=$(echo "$meta_output" | sed -n '3p')
            branch=$(echo "$meta_output" | sed -n '4p')
            project_id=$(echo "$meta_output" | sed -n '5p')
            phase=$(detect_phase "$feature_dir")
            next_cmd=$(get_next_command "$phase")

            context="You're working on feature ${id}-${name} (${mode} mode).\n"
            context+="Current phase: ${phase}\n"

            # Show project affiliation if present
            if [[ -n "$project_id" ]]; then
                local project_slug
                project_slug=$(python3 -c "
import os, json, glob, sys
dirs = glob.glob(os.path.join(sys.argv[1], 'docs/projects', sys.argv[2] + '-*/'))
if dirs:
    with open(os.path.join(dirs[0], '.meta.json')) as f:
        print(json.load(f).get('slug', 'unknown'))
else:
    print('unknown')
" "$PROJECT_ROOT" "$project_id" 2>/dev/null)
                context+="Project: ${project_id}-${project_slug}\n"
            fi

            # Check branch mismatch and add warning
            if [[ -n "$branch" ]]; then
                context+="Branch: ${branch}\n"
                if check_branch_mismatch "$branch"; then
                    current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
                    context+="\n⚠️  WARNING: You are not on the feature branch.\n"
                    context+="   Current branch: ${current_branch}\n"
                    context+="   Feature branch: ${branch}\n"
                    context+="   Consider: git checkout ${branch}\n"
                fi
            fi

            # Add next command suggestion
            context+="\nNext suggested command: ${next_cmd}\n"
        fi
    fi

    # Always include workflow overview
    context+="\nAvailable commands: /brainstorm → /specify → /design → /create-plan → /create-tasks → /implement → /finish (/create-feature, /create-project as alternatives)"

    # Check optional dependency
    if ! check_claude_md_plugin; then
        context+="\n\nNote: claude-md-management plugin not installed. Install it from claude-plugins-official marketplace for automatic CLAUDE.md updates during /finish."
    fi

    if [[ -z "$meta_file" ]]; then
        context+="\n\nNo active feature. Use /brainstorm to start exploring ideas, or /create-feature to skip brainstorming."
    fi

    echo "$context"
}

# Build memory context from knowledge bank entries
build_memory_context() {
    local config_file="${PROJECT_ROOT}/.claude/iflow.local.md"
    local enabled
    enabled=$(read_local_md_field "$config_file" "memory_injection_enabled" "true")
    if [[ "$enabled" != "true" ]]; then
        return
    fi

    local limit
    limit=$(read_local_md_field "$config_file" "memory_injection_limit" "20")
    [[ "$limit" =~ ^-?[0-9]+$ ]] || limit="20"

    local timeout_cmd=""
    if command -v gtimeout >/dev/null 2>&1; then
        timeout_cmd="gtimeout 3"
    elif command -v timeout >/dev/null 2>&1; then
        timeout_cmd="timeout 3"
    fi

    # stderr suppressed: memory.py errors must not corrupt hook JSON output
    local memory_output
    memory_output=$($timeout_cmd python3 "${SCRIPT_DIR}/lib/memory.py" \
        --project-root "$PROJECT_ROOT" \
        --limit "$limit" \
        --global-store "$HOME/.claude/iflow/memory" 2>/dev/null) || memory_output=""
    echo "$memory_output"
}

# Main
main() {
    local memory_context=""
    memory_context=$(build_memory_context)

    local context
    context=$(build_context)

    # Prepend memory before workflow state
    local full_context=""
    if [[ -n "$memory_context" ]]; then
        full_context="${memory_context}\n\n${context}"
    else
        full_context="$context"
    fi

    local escaped_context
    escaped_context=$(escape_json "$full_context")

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
