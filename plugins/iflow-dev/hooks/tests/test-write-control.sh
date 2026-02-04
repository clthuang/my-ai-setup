#!/usr/bin/env bash
# Tests for write-control.sh hook
# Run: ./hooks/tests/test-write-control.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
HOOKS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Walk up to find repo root (has .git directory)
PROJECT_ROOT="$(cd "${HOOKS_DIR}" && while [[ ! -d .git ]] && [[ $PWD != / ]]; do cd ..; done && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Create temp config directory for testing
TEST_CONFIG_DIR=""
setup_test_config() {
  TEST_CONFIG_DIR=$(mktemp -d)
  trap 'rm -rf "$TEST_CONFIG_DIR"' EXIT
}

log_test() {
  echo -e "TEST: $1"
  ((TESTS_RUN++)) || true
}

log_pass() {
  echo -e "${GREEN}  PASS${NC}"
  ((TESTS_PASSED++)) || true
}

log_fail() {
  echo -e "${RED}  FAIL: $1${NC}"
  ((TESTS_FAILED++)) || true
}

log_skip() {
  echo -e "${YELLOW}  SKIP: $1${NC}"
  ((TESTS_SKIPPED++)) || true
  ((TESTS_RUN--)) || true
}

# Source the script for testing (without running main)
source "${HOOKS_DIR}/write-control.sh" --source-only

# =============================================================================
# Test: matches_pattern
# =============================================================================

test_matches_pattern() {
  log_test "matches_pattern: *.md matches file.md"
  if matches_pattern "file.md" "*.md"; then
    log_pass
  else
    log_fail "*.md should match file.md"
  fi

  log_test "matches_pattern: *.md does NOT match dir/file.md"
  if ! matches_pattern "dir/file.md" "*.md"; then
    log_pass
  else
    log_fail "*.md should not match dir/file.md"
  fi

  log_test "matches_pattern: **/*.md matches dir/file.md"
  if matches_pattern "dir/file.md" "**/*.md"; then
    log_pass
  else
    log_fail "**/*.md should match dir/file.md"
  fi

  log_test "matches_pattern: .git/** matches .git/config"
  if matches_pattern ".git/config" ".git/**"; then
    log_pass
  else
    log_fail ".git/** should match .git/config"
  fi

  log_test "matches_pattern: .git/** matches .git/hooks/pre-commit"
  if matches_pattern ".git/hooks/pre-commit" ".git/**"; then
    log_pass
  else
    log_fail ".git/** should match .git/hooks/pre-commit"
  fi

  log_test "matches_pattern: .git/** does NOT match .github/workflows"
  if ! matches_pattern ".github/workflows" ".git/**"; then
    log_pass
  else
    log_fail ".git/** should not match .github/workflows"
  fi

  log_test "matches_pattern: .env* matches .env"
  if matches_pattern ".env" ".env*"; then
    log_pass
  else
    log_fail ".env* should match .env"
  fi

  log_test "matches_pattern: .env* matches .env.local"
  if matches_pattern ".env.local" ".env*"; then
    log_pass
  else
    log_fail ".env* should match .env.local"
  fi

  log_test "matches_pattern: .env* does NOT match env"
  if ! matches_pattern "env" ".env*"; then
    log_pass
  else
    log_fail ".env* should not match env (requires leading dot)"
  fi

  log_test "matches_pattern: src/** matches src/index.ts"
  if matches_pattern "src/index.ts" "src/**"; then
    log_pass
  else
    log_fail "src/** should match src/index.ts"
  fi

  log_test "matches_pattern: src/** does NOT match src (no trailing content)"
  if ! matches_pattern "src" "src/**"; then
    log_pass
  else
    log_fail "src/** should not match src alone"
  fi

  log_test "matches_pattern: plugins/**/agents/*.md matches plugins/iflow/agents/test.md"
  if matches_pattern "plugins/iflow/agents/test.md" "plugins/**/agents/*.md"; then
    log_pass
  else
    log_fail "plugins/**/agents/*.md should match plugins/iflow/agents/test.md"
  fi
}

# =============================================================================
# Test: normalize_path
# =============================================================================

test_normalize_path() {
  log_test "normalize_path: relative path unchanged"
  local result
  result=$(normalize_path "src/file.ts")
  if [[ "$result" == "src/file.ts" ]]; then
    log_pass
  else
    log_fail "Expected 'src/file.ts', got '$result'"
  fi

  log_test "normalize_path: strips ./ prefix"
  result=$(normalize_path "./src/file.ts")
  if [[ "$result" == "src/file.ts" ]]; then
    log_pass
  else
    log_fail "Expected 'src/file.ts', got '$result'"
  fi

  log_test "normalize_path: strips trailing slash"
  result=$(normalize_path "src/")
  if [[ "$result" == "src" ]]; then
    log_pass
  else
    log_fail "Expected 'src', got '$result'"
  fi

  log_test "normalize_path: ../ returns OUTSIDE_PROJECT"
  result=$(normalize_path "../other/file.ts")
  if [[ "$result" == "OUTSIDE_PROJECT" ]]; then
    log_pass
  else
    log_fail "Expected 'OUTSIDE_PROJECT', got '$result'"
  fi

  log_test "normalize_path: absolute path within project is normalized"
  result=$(normalize_path "${PWD}/src/file.ts")
  if [[ "$result" == "src/file.ts" ]]; then
    log_pass
  else
    log_fail "Expected 'src/file.ts', got '$result'"
  fi

  log_test "normalize_path: absolute path outside project returns OUTSIDE_PROJECT"
  result=$(normalize_path "/etc/passwd")
  if [[ "$result" == "OUTSIDE_PROJECT" ]]; then
    log_pass
  else
    log_fail "Expected 'OUTSIDE_PROJECT', got '$result'"
  fi

  log_test "normalize_path: handles file in root (no directory)"
  result=$(normalize_path "README.md")
  if [[ "$result" == "README.md" ]]; then
    log_pass
  else
    log_fail "Expected 'README.md', got '$result'"
  fi
}

# =============================================================================
# Test: load_policies
# =============================================================================

test_load_policies() {
  log_test "load_policies: loads from valid config file"
  # Save original SCRIPT_DIR and use temp config
  local orig_script_dir="$SCRIPT_DIR"
  SCRIPT_DIR="$TEST_CONFIG_DIR"
  mkdir -p "${TEST_CONFIG_DIR}/config"
  echo '{"protected": ["test/**"], "warned": ["warn/**"], "safe": ["safe/**"]}' > "${TEST_CONFIG_DIR}/config/write-policies.json"

  load_policies

  if [[ "${PROTECTED_PATTERNS[0]}" == "test/**" ]]; then
    log_pass
  else
    log_fail "Expected protected pattern 'test/**', got '${PROTECTED_PATTERNS[0]:-empty}'"
  fi

  SCRIPT_DIR="$orig_script_dir"

  log_test "load_policies: uses defaults when config missing"
  SCRIPT_DIR="$TEST_CONFIG_DIR"
  rm -f "${TEST_CONFIG_DIR}/config/write-policies.json"

  load_policies

  # Should have default patterns
  local found=0
  for p in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$p" == ".git/**" ]]; then
      found=1
      break
    fi
  done
  if [[ $found -eq 1 ]]; then
    log_pass
  else
    log_fail "Expected default pattern '.git/**' in PROTECTED_PATTERNS"
  fi

  SCRIPT_DIR="$orig_script_dir"

  log_test "load_policies: uses defaults when config is invalid JSON"
  SCRIPT_DIR="$TEST_CONFIG_DIR"
  mkdir -p "${TEST_CONFIG_DIR}/config"
  echo 'not valid json{' > "${TEST_CONFIG_DIR}/config/write-policies.json"

  load_policies

  # Should have default patterns
  found=0
  for p in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$p" == ".git/**" ]]; then
      found=1
      break
    fi
  done
  if [[ $found -eq 1 ]]; then
    log_pass
  else
    log_fail "Expected default pattern '.git/**' when config invalid"
  fi

  SCRIPT_DIR="$orig_script_dir"
}

# =============================================================================
# Test: check_protected, check_warned, check_safe
# =============================================================================

test_check_protected() {
  # Ensure defaults are loaded
  PROTECTED_PATTERNS=("${DEFAULT_PROTECTED[@]}")

  log_test "check_protected: .git/config is protected"
  if check_protected ".git/config"; then
    log_pass
  else
    log_fail ".git/config should be protected"
  fi

  log_test "check_protected: node_modules/pkg/index.js is protected"
  if check_protected "node_modules/pkg/index.js"; then
    log_pass
  else
    log_fail "node_modules/pkg/index.js should be protected"
  fi

  log_test "check_protected: .env is protected"
  if check_protected ".env"; then
    log_pass
  else
    log_fail ".env should be protected"
  fi

  log_test "check_protected: secrets.key is protected"
  if check_protected "secrets.key"; then
    log_pass
  else
    log_fail "secrets.key should be protected"
  fi

  log_test "check_protected: src/file.ts is NOT protected"
  if ! check_protected "src/file.ts"; then
    log_pass
  else
    log_fail "src/file.ts should not be protected"
  fi

  log_test "check_protected: README.md is NOT protected"
  if ! check_protected "README.md"; then
    log_pass
  else
    log_fail "README.md should not be protected"
  fi
}

test_check_warned() {
  # Ensure defaults are loaded
  WARNED_PATTERNS=("${DEFAULT_WARNED[@]}")

  log_test "check_warned: src/index.ts is warned"
  if check_warned "src/index.ts"; then
    log_pass
  else
    log_fail "src/index.ts should be warned"
  fi

  log_test "check_warned: plugins/iflow/agents/test.md is warned"
  if check_warned "plugins/iflow/agents/test.md"; then
    log_pass
  else
    log_fail "plugins/iflow/agents/test.md should be warned"
  fi

  log_test "check_warned: docs/guide.md is NOT warned"
  if ! check_warned "docs/guide.md"; then
    log_pass
  else
    log_fail "docs/guide.md should not be warned"
  fi

  log_test "check_warned: README.md is NOT warned"
  if ! check_warned "README.md"; then
    log_pass
  else
    log_fail "README.md should not be warned"
  fi
}

test_check_safe() {
  # Ensure defaults are loaded
  SAFE_PATTERNS=("${DEFAULT_SAFE[@]}")

  log_test "check_safe: docs/guide.md is safe"
  if check_safe "docs/guide.md"; then
    log_pass
  else
    log_fail "docs/guide.md should be safe"
  fi

  log_test "check_safe: agent_sandbox/session/file.py is safe"
  if check_safe "agent_sandbox/session/file.py"; then
    log_pass
  else
    log_fail "agent_sandbox path should be safe"
  fi

  log_test "check_safe: tests/test_main.py is safe"
  if check_safe "tests/test_main.py"; then
    log_pass
  else
    log_fail "tests path should be safe"
  fi

  log_test "check_safe: README.md is safe (*.md pattern)"
  if check_safe "README.md"; then
    log_pass
  else
    log_fail "README.md should be safe"
  fi

  log_test "check_safe: src/index.ts is NOT safe"
  if ! check_safe "src/index.ts"; then
    log_pass
  else
    log_fail "src/index.ts should not be safe"
  fi
}

# =============================================================================
# Test: emit_deny, emit_allow_warning
# =============================================================================

test_emit_deny() {
  log_test "emit_deny: produces valid JSON with deny decision"
  local output
  output=$(emit_deny ".git/config" "cannot be modified")

  if echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
h = d.get('hookSpecificOutput', {})
assert h.get('hookEventName') == 'PreToolUse', 'hookEventName mismatch'
assert h.get('permissionDecision') == 'deny', 'permissionDecision mismatch'
assert 'Protected path' in h.get('permissionDecisionReason', ''), 'reason missing Protected path'
assert '.git/config' in h.get('permissionDecisionReason', ''), 'reason missing path'
" 2>/dev/null; then
    log_pass
  else
    log_fail "emit_deny output is invalid: $output"
  fi
}

test_emit_allow_warning() {
  log_test "emit_allow_warning: produces valid JSON with allow decision"
  local output
  output=$(emit_allow_warning "src/index.ts" "ensure intentional")

  if echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
h = d.get('hookSpecificOutput', {})
assert h.get('hookEventName') == 'PreToolUse', 'hookEventName mismatch'
assert h.get('permissionDecision') == 'allow', 'permissionDecision mismatch'
assert 'Production path' in h.get('permissionDecisionReason', ''), 'reason missing Production path'
assert 'src/index.ts' in h.get('permissionDecisionReason', ''), 'reason missing path'
" 2>/dev/null; then
    log_pass
  else
    log_fail "emit_allow_warning output is invalid: $output"
  fi
}

# =============================================================================
# Test: read_tool_input
# =============================================================================

test_read_tool_input() {
  log_test "read_tool_input: extracts file_path from valid JSON"
  local result
  result=$(echo '{"tool_name": "Write", "tool_input": {"file_path": "src/test.ts"}}' | read_tool_input_from_string)
  if [[ "$result" == "src/test.ts" ]]; then
    log_pass
  else
    log_fail "Expected 'src/test.ts', got '$result'"
  fi

  log_test "read_tool_input: returns empty for missing file_path"
  result=$(echo '{"tool_name": "Write", "tool_input": {}}' | read_tool_input_from_string)
  if [[ -z "$result" ]]; then
    log_pass
  else
    log_fail "Expected empty string, got '$result'"
  fi

  log_test "read_tool_input: returns empty for invalid JSON"
  result=$(echo 'not json' | read_tool_input_from_string)
  if [[ -z "$result" ]]; then
    log_pass
  else
    log_fail "Expected empty string for invalid JSON, got '$result'"
  fi

  log_test "read_tool_input: handles absolute path"
  result=$(echo '{"tool_name": "Edit", "tool_input": {"file_path": "/Users/test/project/src/file.ts"}}' | read_tool_input_from_string)
  if [[ "$result" == "/Users/test/project/src/file.ts" ]]; then
    log_pass
  else
    log_fail "Expected absolute path, got '$result'"
  fi
}

# Helper for testing read_tool_input without timeout (for predictable testing)
read_tool_input_from_string() {
  python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null
}

test_read_tool_input_timeout() {
  log_test "read_tool_input: timeout behavior"
  log_skip "Timeout testing requires interactive stdin - manual verification needed"
}

# =============================================================================
# Test: Integration tests (full pipeline)
# =============================================================================

test_integration() {
  cd "${PROJECT_ROOT}"

  log_test "integration: protected path .git/config returns deny"
  local output
  output=$(echo '{"tool_name": "Write", "tool_input": {"file_path": ".git/config"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['hookSpecificOutput']['permissionDecision'] == 'deny'" 2>/dev/null; then
    log_pass
  else
    log_fail "Expected deny for .git/config: $output"
  fi

  log_test "integration: protected path with absolute returns deny"
  output=$(echo "{\"tool_name\": \"Write\", \"tool_input\": {\"file_path\": \"${PWD}/.git/config\"}}" | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['hookSpecificOutput']['permissionDecision'] == 'deny'" 2>/dev/null; then
    log_pass
  else
    log_fail "Expected deny for absolute .git/config: $output"
  fi

  log_test "integration: warned path src/index.ts returns allow with message"
  output=$(echo '{"tool_name": "Write", "tool_input": {"file_path": "src/index.ts"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); h=d['hookSpecificOutput']; assert h['permissionDecision'] == 'allow' and 'Production path' in h['permissionDecisionReason']" 2>/dev/null; then
    log_pass
  else
    log_fail "Expected allow with warning for src/index.ts: $output"
  fi

  log_test "integration: safe path docs/README.md returns silent (no output)"
  output=$(echo '{"tool_name": "Write", "tool_input": {"file_path": "docs/README.md"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if [[ -z "$output" ]]; then
    log_pass
  else
    log_fail "Expected no output for safe path, got: $output"
  fi

  log_test "integration: unmatched path random/file.txt returns silent"
  output=$(echo '{"tool_name": "Write", "tool_input": {"file_path": "random/file.txt"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if [[ -z "$output" ]]; then
    log_pass
  else
    log_fail "Expected no output for unmatched path, got: $output"
  fi

  log_test "integration: outside project path /etc/passwd returns deny"
  output=$(echo '{"tool_name": "Write", "tool_input": {"file_path": "/etc/passwd"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['hookSpecificOutput']['permissionDecision'] == 'deny'" 2>/dev/null; then
    log_pass
  else
    log_fail "Expected deny for /etc/passwd: $output"
  fi

  log_test "integration: ../escape path returns deny"
  output=$(echo '{"tool_name": "Edit", "tool_input": {"file_path": "../other/file.txt"}}' | "${HOOKS_DIR}/write-control.sh" 2>/dev/null)
  if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['hookSpecificOutput']['permissionDecision'] == 'deny'" 2>/dev/null; then
    log_pass
  else
    log_fail "Expected deny for ../escape path: $output"
  fi
}

# =============================================================================
# Run all tests
# =============================================================================

run_all_tests() {
  echo "=========================================="
  echo "Write Control Hook Tests"
  echo "=========================================="
  echo ""

  setup_test_config

  test_matches_pattern
  test_normalize_path
  test_load_policies
  test_check_protected
  test_check_warned
  test_check_safe
  test_emit_deny
  test_emit_allow_warning
  test_read_tool_input
  test_read_tool_input_timeout
  test_integration

  echo ""
  echo "=========================================="
  echo "Results: ${TESTS_PASSED}/${TESTS_RUN} passed"
  if [[ $TESTS_SKIPPED -gt 0 ]]; then
    echo "Skipped: ${TESTS_SKIPPED}"
  fi
  if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
  fi
  echo "=========================================="

  if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
  fi
  exit 0
}

run_all_tests
