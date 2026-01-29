#!/usr/bin/env bash
# Hook integration tests
# Run: ./hooks/tests/test-hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
HOOKS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${HOOKS_DIR}/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

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

# Test 1: common.sh library exists and is sourceable
test_common_library_exists() {
    log_test "common.sh library exists and is sourceable"

    if [[ -f "${HOOKS_DIR}/lib/common.sh" ]]; then
        if source "${HOOKS_DIR}/lib/common.sh" 2>/dev/null; then
            log_pass
        else
            log_fail "Cannot source common.sh"
        fi
    else
        log_fail "lib/common.sh not found"
    fi
}

# Test 2: detect_project_root finds correct directory from project root
test_detect_project_root() {
    log_test "detect_project_root finds project from project root"

    source "${HOOKS_DIR}/lib/common.sh"

    cd "${PROJECT_ROOT}"
    local detected
    detected=$(detect_project_root)

    if [[ "$detected" == "$PROJECT_ROOT" ]]; then
        log_pass
    else
        log_fail "Expected $PROJECT_ROOT, got $detected"
    fi
}

# Test 3: detect_project_root works from subdirectory
test_detect_project_root_subdirectory() {
    log_test "detect_project_root works from hooks subdirectory"

    source "${HOOKS_DIR}/lib/common.sh"

    cd "${HOOKS_DIR}"
    local detected
    detected=$(detect_project_root)

    if [[ "$detected" == "$PROJECT_ROOT" ]]; then
        log_pass
    else
        log_fail "Expected $PROJECT_ROOT, got $detected"
    fi

    cd "${PROJECT_ROOT}"
}

# Test 4: detect_project_root works from deeply nested directory
test_detect_project_root_nested() {
    log_test "detect_project_root works from deeply nested directory"

    source "${HOOKS_DIR}/lib/common.sh"

    cd "${PROJECT_ROOT}/docs/features"
    local detected
    detected=$(detect_project_root)

    if [[ "$detected" == "$PROJECT_ROOT" ]]; then
        log_pass
    else
        log_fail "Expected $PROJECT_ROOT, got $detected"
    fi

    cd "${PROJECT_ROOT}"
}

# Test 5: escape_json handles special characters
test_escape_json() {
    log_test "escape_json handles special characters"

    source "${HOOKS_DIR}/lib/common.sh"

    local input=$'Line1\nLine2\tTab"Quote\\Backslash'
    local escaped
    escaped=$(escape_json "$input")

    # Check newline, tab, quote, backslash were escaped
    if [[ "$escaped" == *'\n'* ]] && [[ "$escaped" == *'\t'* ]] && [[ "$escaped" == *'\"'* ]] && [[ "$escaped" == *'\\'* ]]; then
        log_pass
    else
        log_fail "Escaping not working correctly: $escaped"
    fi
}

# Test 6: session-start.sh produces valid JSON
test_session_start_json() {
    log_test "session-start.sh produces valid JSON"

    cd "${PROJECT_ROOT}"
    local output
    output=$("${HOOKS_DIR}/session-start.sh" 2>/dev/null)

    if echo "$output" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
        log_pass
    else
        log_fail "Invalid JSON output"
    fi
}

# Test 7: session-start.sh works from subdirectory
test_session_start_from_subdirectory() {
    log_test "session-start.sh works from subdirectory"

    cd "${PROJECT_ROOT}/docs"
    local output
    output=$("${HOOKS_DIR}/session-start.sh" 2>/dev/null)

    if echo "$output" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
        log_pass
    else
        log_fail "Invalid JSON output from subdirectory"
    fi

    cd "${PROJECT_ROOT}"
}

# Test 8: pre-commit-guard.sh allows non-commit commands
test_pre_commit_guard_allows_non_commit() {
    log_test "pre-commit-guard.sh allows non-commit commands"

    cd "${PROJECT_ROOT}"
    local output
    output=$(echo '{"tool_name": "Bash", "tool_input": {"command": "git status"}}' | "${HOOKS_DIR}/pre-commit-guard.sh" 2>/dev/null)

    if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('hookSpecificOutput', {}).get('permissionDecision') == 'allow'" 2>/dev/null; then
        log_pass
    else
        log_fail "Should allow git status"
    fi
}

# Test 9: pre-commit-guard.sh allows non-git commands
test_pre_commit_guard_allows_non_git() {
    log_test "pre-commit-guard.sh allows non-git commands"

    cd "${PROJECT_ROOT}"
    local output
    output=$(echo '{"tool_name": "Bash", "tool_input": {"command": "ls -la"}}' | "${HOOKS_DIR}/pre-commit-guard.sh" 2>/dev/null)

    if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('hookSpecificOutput', {}).get('permissionDecision') == 'allow'" 2>/dev/null; then
        log_pass
    else
        log_fail "Should allow ls command"
    fi
}

# Test 10: pre-commit-guard.sh blocks commits on main branch
test_pre_commit_guard_blocks_main() {
    log_test "pre-commit-guard.sh blocks commits on main branch"

    cd "${PROJECT_ROOT}"

    # Only test if actually on main
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

    if [[ "$branch" == "main" ]] || [[ "$branch" == "master" ]]; then
        local output exit_code
        output=$(echo '{"tool_name": "Bash", "tool_input": {"command": "git commit -m test"}}' | "${HOOKS_DIR}/pre-commit-guard.sh" 2>/dev/null) || exit_code=$?

        if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'" 2>/dev/null; then
            log_pass
        else
            log_fail "Should block commits on main"
        fi
    else
        log_skip "Not on main branch (on $branch)"
    fi
}

# Test 11: pre-commit-guard.sh works from subdirectory
test_pre_commit_guard_from_subdirectory() {
    log_test "pre-commit-guard.sh works from subdirectory"

    cd "${PROJECT_ROOT}/docs"
    local output
    output=$(echo '{"tool_name": "Bash", "tool_input": {"command": "git status"}}' | "${HOOKS_DIR}/pre-commit-guard.sh" 2>/dev/null)

    if echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('hookSpecificOutput', {}).get('permissionDecision') == 'allow'" 2>/dev/null; then
        log_pass
    else
        log_fail "Hook should work from subdirectory"
    fi

    cd "${PROJECT_ROOT}"
}

# Run all tests
main() {
    echo "=========================================="
    echo "Hook Integration Tests"
    echo "=========================================="
    echo ""

    test_common_library_exists
    test_detect_project_root
    test_detect_project_root_subdirectory
    test_detect_project_root_nested
    test_escape_json
    test_session_start_json
    test_session_start_from_subdirectory
    test_pre_commit_guard_allows_non_commit
    test_pre_commit_guard_allows_non_git
    test_pre_commit_guard_blocks_main
    test_pre_commit_guard_from_subdirectory

    echo ""
    echo "=========================================="
    echo "Results: ${TESTS_PASSED}/${TESTS_RUN} passed"
    if [[ $TESTS_SKIPPED -gt 0 ]]; then
        echo "Skipped: ${TESTS_SKIPPED}"
    fi
    echo "=========================================="

    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main
