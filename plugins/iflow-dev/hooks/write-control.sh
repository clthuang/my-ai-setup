#!/usr/bin/env bash
# PreToolUse hook: enforce path-based write restrictions for Write/Edit tools
#
# Input: stdin JSON {"tool_name": "Write|Edit", "tool_input": {"file_path": "..."}}
# Output:
#   - Deny: JSON with permissionDecision: "deny"
#   - Allow with warning: JSON with permissionDecision: "allow" and reason
#   - Silent allow: exit 0 with no output

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Defensive fallback: escape_json exists in common.sh but may be removed/modified
# Keep this for robustness - fails open if neither works (fail-open design)
# Note: json.dumps always wraps strings in quotes, so sed pattern is safe
if ! type escape_json &>/dev/null; then
  escape_json() { python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$1" | sed 's/^"//; s/"$//'; }
fi

# Default patterns (used when config file is missing or invalid)
DEFAULT_PROTECTED=(
  ".git/**"
  "node_modules/**"
  ".env*"
  "*.key"
  "*.pem"
  "package-lock.json"
  "yarn.lock"
)

DEFAULT_WARNED=(
  "src/**"
  "plugins/**/agents/*.md"
  "plugins/**/commands/*.md"
  "plugins/**/skills/**"
  ".claude-plugin/**"
)

DEFAULT_SAFE=(
  "docs/**"
  "agent_sandbox/**"
  "tests/**"
  "*.md"
)

# Global arrays populated by load_policies
PROTECTED_PATTERNS=()
WARNED_PATTERNS=()
SAFE_PATTERNS=()

# Check if path matches a glob pattern
# Usage: matches_pattern "path" "pattern"
# Returns 0 if matches, 1 otherwise
matches_pattern() {
  local path="$1" pattern="$2"

  # Step 1: Replace ** with placeholder before escaping
  # This prevents the * in (.*) from being converted later
  local regex="$pattern"
  regex="${regex//\*\*/__DOUBLESTAR__}"

  # Step 2: Escape regex special characters commonly found in paths
  regex="${regex//./\\.}"        # . -> \. (literal dot)
  regex="${regex//+/\\+}"        # + -> \+
  regex="${regex//\?/[^/]}"      # ? -> match single non-slash char

  # Step 3: Handle * (single star matches any chars except slash)
  regex="${regex//\*/[^/]*}"

  # Step 4: Replace placeholder with actual regex for **
  # ** matches zero or more of anything (including /)
  regex="${regex//__DOUBLESTAR__/.*}"

  # Step 5: Anchor the pattern and match
  [[ "$path" =~ ^${regex}$ ]]
}

# Normalize path to project-relative form
# Usage: normalize_path "/absolute/path" or normalize_path "relative/path"
# Returns: project-relative path or "OUTSIDE_PROJECT" for invalid paths
normalize_path() {
  local path="$1"

  # Handle relative paths that escape project (e.g., ../other/file)
  if [[ "$path" == ../* ]]; then
    echo "OUTSIDE_PROJECT"
    return
  fi

  # Handle absolute paths
  if [[ "$path" == /* ]]; then
    # Defensive check for empty PWD
    if [[ -z "${PWD:-}" ]]; then
      echo "OUTSIDE_PROJECT"
      return
    fi
    # Check if path is within project root
    if [[ "$path" == "$PWD/"* ]]; then
      # Strip project root prefix
      path="${path#$PWD/}"
    elif [[ "$path" == "$PWD" ]]; then
      # Path is exactly project root
      path=""
    else
      # Path is outside project
      echo "OUTSIDE_PROJECT"
      return
    fi
  fi

  # Remove ./ prefix
  path="${path#./}"

  # Remove trailing slash (directories passed as src/ -> src)
  path="${path%/}"

  echo "$path"
}

# Load policies from config file or use defaults
# Populates: PROTECTED_PATTERNS, WARNED_PATTERNS, SAFE_PATTERNS
load_policies() {
  local config_file="${SCRIPT_DIR}/config/write-policies.json"

  if [[ -f "$config_file" ]]; then
    # Use python3 to parse JSON once and output all arrays with markers
    local parsed_output
    parsed_output=$(python3 -c "
import json
import sys
try:
    with open('$config_file') as f:
        data = json.load(f)
    print('__PROTECTED__')
    for p in data.get('protected', []): print(p)
    print('__WARNED__')
    for p in data.get('warned', []): print(p)
    print('__SAFE__')
    for p in data.get('safe', []): print(p)
except Exception as e:
    print('__ERROR__', file=sys.stderr)
    print(f'write-control.sh: config parse error: {e}', file=sys.stderr)
")

    # Parse the combined output into separate arrays
    local current_section="" protected="" warned="" safe=""
    while IFS= read -r line; do
      case "$line" in
        __PROTECTED__) current_section="protected" ;;
        __WARNED__) current_section="warned" ;;
        __SAFE__) current_section="safe" ;;
        *)
          case "$current_section" in
            protected) protected+="$line"$'\n' ;;
            warned) warned+="$line"$'\n' ;;
            safe) safe+="$line"$'\n' ;;
          esac
          ;;
      esac
    done <<< "$parsed_output"

    # Remove trailing newlines
    protected="${protected%$'\n'}"
    warned="${warned%$'\n'}"
    safe="${safe%$'\n'}"

    # Convert to arrays (empty output = use defaults)
    # Use read loop for bash 3.x compatibility (macOS default)
    if [[ -n "$protected" ]]; then
      PROTECTED_PATTERNS=()
      while IFS= read -r line; do
        PROTECTED_PATTERNS+=("$line")
      done <<< "$protected"
    else
      PROTECTED_PATTERNS=("${DEFAULT_PROTECTED[@]}")
    fi

    if [[ -n "$warned" ]]; then
      WARNED_PATTERNS=()
      while IFS= read -r line; do
        WARNED_PATTERNS+=("$line")
      done <<< "$warned"
    else
      WARNED_PATTERNS=("${DEFAULT_WARNED[@]}")
    fi

    if [[ -n "$safe" ]]; then
      SAFE_PATTERNS=()
      while IFS= read -r line; do
        SAFE_PATTERNS+=("$line")
      done <<< "$safe"
    else
      SAFE_PATTERNS=("${DEFAULT_SAFE[@]}")
    fi
  else
    # Config missing: use defaults
    PROTECTED_PATTERNS=("${DEFAULT_PROTECTED[@]}")
    WARNED_PATTERNS=("${DEFAULT_WARNED[@]}")
    SAFE_PATTERNS=("${DEFAULT_SAFE[@]}")
  fi
}

# Check if path matches any protected pattern
# Returns 0 if protected, 1 otherwise
check_protected() {
  local path="$1"
  for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if matches_pattern "$path" "$pattern"; then
      return 0
    fi
  done
  return 1
}

# Check if path matches any warned pattern
# Returns 0 if warned, 1 otherwise
check_warned() {
  local path="$1"
  for pattern in "${WARNED_PATTERNS[@]}"; do
    if matches_pattern "$path" "$pattern"; then
      return 0
    fi
  done
  return 1
}

# Check if path matches any safe pattern
# Returns 0 if safe, 1 otherwise
check_safe() {
  local path="$1"
  for pattern in "${SAFE_PATTERNS[@]}"; do
    if matches_pattern "$path" "$pattern"; then
      return 0
    fi
  done
  return 1
}

# Output deny JSON response
# Usage: emit_deny "path" "reason"
emit_deny() {
  local path="$1" reason="$2"
  local escaped_path escaped_reason
  escaped_path=$(escape_json "$path")
  escaped_reason=$(escape_json "$reason")
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Protected path: ${escaped_path} - ${escaped_reason}"
  }
}
EOF
}

# Output allow with warning JSON response
# Usage: emit_allow_warning "path" "reason"
emit_allow_warning() {
  local path="$1" reason="$2"
  local escaped_path escaped_reason
  escaped_path=$(escape_json "$path")
  escaped_reason=$(escape_json "$reason")
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Production path: ${escaped_path} - ${escaped_reason}"
  }
}
EOF
}

# Read tool input from stdin with timeout protection
# Returns: file_path value or empty string on error
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

  # Extract file_path from JSON input
  # Input format: {"tool_name": "Write|Edit", "tool_input": {"file_path": "..."}}
  echo "$input" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null
}

# Main function
main() {
  local ORIGINAL_PATH
  ORIGINAL_PATH=$(read_tool_input)

  if [[ -z "$ORIGINAL_PATH" ]]; then
    exit 0  # No path, allow silently
  fi

  local FILE_PATH
  FILE_PATH=$(normalize_path "$ORIGINAL_PATH")

  # Block paths outside project
  if [[ "$FILE_PATH" == "OUTSIDE_PROJECT" ]]; then
    emit_deny "$ORIGINAL_PATH" "Path outside project boundary"
    exit 0
  fi

  load_policies

  if check_protected "$FILE_PATH"; then
    emit_deny "$FILE_PATH" "cannot be modified via Write/Edit tool"
    exit 0
  fi

  if check_warned "$FILE_PATH"; then
    emit_allow_warning "$FILE_PATH" "ensure this is intentional implementation"
    exit 0
  fi

  # Safe or unmatched: silent allow
  exit 0
}

# Support --source-only for testing (allows sourcing functions without running main)
if [[ "${1:-}" != "--source-only" ]]; then
  main
fi
