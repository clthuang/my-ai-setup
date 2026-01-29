#!/usr/bin/env bash
# SessionStart hook: inject workflow context and surface active feature

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Escape string for JSON output
escape_json() {
    local input="$1"
    local output=""
    local i char
    for (( i=0; i<${#input}; i++ )); do
        char="${input:$i:1}"
        case "$char" in
            '\') output+='\\';;
            '"') output+='\"';;
            $'\n') output+='\n';;
            $'\r') output+='\r';;
            $'\t') output+='\t';;
            *) output+="$char";;
        esac
    done
    printf '%s' "$output"
}

# Find active feature (most recently modified .meta.json)
find_active_feature() {
    local features_dir="${PLUGIN_ROOT}/docs/features"

    if [[ ! -d "$features_dir" ]]; then
        return 1
    fi

    # Find most recently modified .meta.json
    local latest_meta
    latest_meta=$(find "$features_dir" -name ".meta.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

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
    elif [[ -f "${feature_dir}/design.md" ]]; then
        echo "creating-tasks"
    elif [[ -f "${feature_dir}/spec.md" ]]; then
        echo "designing"
    elif [[ -f "${feature_dir}/brainstorm.md" ]]; then
        echo "specifying"
    else
        echo "brainstorming"
    fi
}

# Build context message
build_context() {
    local context=""
    local meta_file

    meta_file=$(find_active_feature)

    if [[ -n "$meta_file" ]]; then
        local feature_dir
        feature_dir=$(dirname "$meta_file")

        # Parse metadata
        local meta_output
        meta_output=$(parse_feature_meta "$meta_file")

        if [[ -n "$meta_output" ]]; then
            local id name mode worktree phase
            id=$(echo "$meta_output" | sed -n '1p')
            name=$(echo "$meta_output" | sed -n '2p')
            mode=$(echo "$meta_output" | sed -n '3p')
            worktree=$(echo "$meta_output" | sed -n '4p')
            phase=$(detect_phase "$feature_dir")

            context="You're working on feature ${id}-${name} (${mode} mode).\n"
            context+="Current phase: ${phase}\n"
            if [[ -n "$worktree" ]]; then
                context+="Worktree: ${worktree}\n"
            fi
            context+="\n"
        fi
    fi

    # Always include workflow overview
    context+="Available commands: /create-feature | /brainstorm → /specify → /design → /create-tasks → /implement → /verify → /finish"

    if [[ -z "$meta_file" ]]; then
        context+="\n\nNo active feature. Use /create-feature to start a structured workflow, or work freely—skills are available on demand."
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
