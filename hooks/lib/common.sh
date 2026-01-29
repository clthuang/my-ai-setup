#!/usr/bin/env bash
# Shared library for hook utilities
# Source this file at the start of hook scripts:
#   source "${SCRIPT_DIR}/lib/common.sh"

# Detect project root: use PWD (where Claude is running), not PLUGIN_ROOT (cached plugin location)
# This is critical because PLUGIN_ROOT points to ~/.claude/plugins/cache/... which has stale data
detect_project_root() {
    local dir="${PWD}"

    # Walk up to find .git or docs/features (project markers)
    while [[ "$dir" != "/" ]]; do
        if [[ -d "${dir}/.git" ]] || [[ -d "${dir}/docs/features" ]]; then
            echo "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done

    # Fallback to PWD if no markers found
    echo "${PWD}"
}

# Extract working directory from a command string
# Handles patterns like:
#   cd /path && git commit...
#   (cd /path && git commit...)
#   git -C /path commit...
#   git commit... (returns empty, meaning use PWD)
extract_command_workdir() {
    local command="$1"

    # Strip leading parenthesis for subshell commands
    command="${command#(}"

    # Match: cd /path && ... or cd "/path" && ...
    if [[ "$command" =~ ^[[:space:]]*cd[[:space:]]+[\"\']?([^\"\'[:space:]]+)[\"\']?[[:space:]]*\&\& ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    # Match: git -C /path ... or git -C "/path" ...
    if [[ "$command" =~ git[[:space:]]+-C[[:space:]]+[\"\']?([^\"\'[:space:]]+)[\"\']? ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    # No directory prefix found - return empty (caller should use PWD)
    echo ""
}

# Run git command in the appropriate directory for a given command string
# Usage: run_git_in_command_context "$command" rev-parse --abbrev-ref HEAD
run_git_in_command_context() {
    local command="$1"
    shift
    local git_args=("$@")

    local workdir
    workdir=$(extract_command_workdir "$command")

    if [[ -n "$workdir" ]] && [[ -d "$workdir" ]]; then
        git -C "$workdir" "${git_args[@]}" 2>/dev/null
    else
        git "${git_args[@]}" 2>/dev/null
    fi
}

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
