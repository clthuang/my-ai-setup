#!/usr/bin/env bash
# Content regression tests for the prompt-intelligence-system feature
# Run: bash plugins/iflow-dev/hooks/tests/test-promptimize-content.sh
#
# These tests verify critical content in the promptimize skill, scoring rubric,
# prompt guidelines, and related commands. They prevent accidental deletion of
# key sections, structural elements, and behavioral contracts during edits.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
HOOKS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${HOOKS_DIR}" && while [[ ! -d .git ]] && [[ $PWD != / ]]; do cd ..; done && pwd)"

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

# --- Paths ---
PLUGIN_DIR="${PROJECT_ROOT}/plugins/iflow-dev"
SKILL_DIR="${PLUGIN_DIR}/skills/promptimize"
SKILL_FILE="${SKILL_DIR}/SKILL.md"
RUBRIC_FILE="${SKILL_DIR}/references/scoring-rubric.md"
GUIDELINES_FILE="${SKILL_DIR}/references/prompt-guidelines.md"
PROMPTIMIZE_CMD="${PLUGIN_DIR}/commands/promptimize.md"
REFRESH_CMD="${PLUGIN_DIR}/commands/refresh-prompt-guidelines.md"


# ============================================================
# Dimension 1: BDD Scenarios (spec-driven content assertions)
# ============================================================

# --- scoring-rubric.md ---

# derived_from: spec:AC-rubric-dimensions (scoring rubric documents exactly 9 dimensions)
test_rubric_has_exactly_9_dimensions() {
    log_test "scoring-rubric.md documents exactly 9 scoring dimensions"

    # Given the scoring rubric file exists
    if [[ ! -f "$RUBRIC_FILE" ]]; then
        log_fail "File not found: $RUBRIC_FILE"
        return
    fi
    # When we count rows in the Behavioral Anchors table (which have descriptive text, NOT "Evaluated"/"Auto-pass")
    local dim_count
    dim_count=$(sed -n '/^## Behavioral Anchors/,/^## /p' "$RUBRIC_FILE" | grep -cE '^\| (Structure|Token|Description|Persuasion|Technique|Prohibition|Example|Progressive|Context)')
    # Then there are exactly 9 dimensions
    if [[ "$dim_count" -eq 9 ]]; then
        log_pass
    else
        log_fail "Expected 9 dimensions, found $dim_count"
    fi
}

# derived_from: spec:AC-rubric-scoring (each dimension has pass/partial/fail anchors)
test_rubric_has_pass_partial_fail_columns() {
    log_test "scoring-rubric.md has Pass/Partial/Fail columns in behavioral anchors"

    # Given the rubric file
    if [[ ! -f "$RUBRIC_FILE" ]]; then
        log_fail "File not found: $RUBRIC_FILE"
        return
    fi
    # When we check the table header
    local header
    header=$(grep -E '^\| Dimension' "$RUBRIC_FILE" | head -1)
    # Then it contains Pass (3), Partial (2), and Fail (1) headers
    if [[ "$header" == *"Pass (3)"* ]] && [[ "$header" == *"Partial (2)"* ]] && [[ "$header" == *"Fail (1)"* ]]; then
        log_pass
    else
        log_fail "Missing Pass/Partial/Fail columns in header: $header"
    fi
}

# derived_from: spec:AC-rubric-applicability (Component Type Applicability table present)
test_rubric_has_component_type_applicability_table() {
    log_test "scoring-rubric.md has Component Type Applicability table"

    # Given the rubric file
    if [[ ! -f "$RUBRIC_FILE" ]]; then
        log_fail "File not found: $RUBRIC_FILE"
        return
    fi
    # When we search for the section heading
    # Then it exists
    if grep -q '## Component Type Applicability' "$RUBRIC_FILE"; then
        log_pass
    else
        log_fail "Missing '## Component Type Applicability' section"
    fi
}

# derived_from: spec:AC-rubric-autopass (auto-pass entries exist for correct component types)
test_rubric_has_auto_pass_entries() {
    log_test "scoring-rubric.md has Auto-pass entries in applicability table"

    # Given the rubric file
    if [[ ! -f "$RUBRIC_FILE" ]]; then
        log_fail "File not found: $RUBRIC_FILE"
        return
    fi
    # When we count Auto-pass occurrences in the table
    local ap_count
    ap_count=$(grep -c 'Auto-pass' "$RUBRIC_FILE")
    # Then there are at least 1 (the spec specifies several: Persuasion/Command, etc.)
    if [[ "$ap_count" -ge 1 ]]; then
        log_pass
    else
        log_fail "Expected at least 1 Auto-pass entry, found $ap_count"
    fi
}

# derived_from: spec:AC-rubric-applicability-columns (table has Skill, Agent, Command columns)
test_rubric_applicability_has_three_component_columns() {
    log_test "scoring-rubric.md applicability table has Skill/Agent/Command columns"

    if [[ ! -f "$RUBRIC_FILE" ]]; then
        log_fail "File not found: $RUBRIC_FILE"
        return
    fi
    local header
    header=$(grep -E '^\| Dimension.*Skill' "$RUBRIC_FILE" | head -1)
    if [[ "$header" == *"Skill"* ]] && [[ "$header" == *"Agent"* ]] && [[ "$header" == *"Command"* ]]; then
        log_pass
    else
        log_fail "Missing Skill/Agent/Command columns: $header"
    fi
}

# --- prompt-guidelines.md ---

# derived_from: spec:AC-guidelines-date (has "Last Updated" date field)
test_guidelines_has_last_updated_date() {
    log_test "prompt-guidelines.md has 'Last Updated' date heading"

    if [[ ! -f "$GUIDELINES_FILE" ]]; then
        log_fail "File not found: $GUIDELINES_FILE"
        return
    fi
    # When we search for the date heading pattern
    if grep -qE '^## Last Updated: [0-9]{4}-[0-9]{2}-[0-9]{2}' "$GUIDELINES_FILE"; then
        log_pass
    else
        log_fail "Missing '## Last Updated: YYYY-MM-DD' heading"
    fi
}

# derived_from: spec:AC-guidelines-count (at least 15 guidelines with citations)
test_guidelines_has_at_least_15_guidelines() {
    log_test "prompt-guidelines.md has at least 15 guidelines with citations"

    if [[ ! -f "$GUIDELINES_FILE" ]]; then
        log_fail "File not found: $GUIDELINES_FILE"
        return
    fi
    # When we count lines that look like guidelines (numbered items or bold-prefixed bullets with citations)
    local count
    count=$(grep -cE '(\*\*.*\*\*.*\[|^[0-9]+\. \*\*.*\[)' "$GUIDELINES_FILE")
    # Then there are at least 15
    if [[ "$count" -ge 15 ]]; then
        log_pass
    else
        log_fail "Expected >= 15 guidelines with citations, found $count"
    fi
}

# derived_from: spec:AC-guidelines-sections (has all 6 required sections)
test_guidelines_has_core_principles_section() {
    log_test "prompt-guidelines.md has 'Core Principles' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Core Principles' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Core Principles section"; fi
}

test_guidelines_has_plugin_specific_patterns_section() {
    log_test "prompt-guidelines.md has 'Plugin-Specific Patterns' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Plugin-Specific Patterns' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Plugin-Specific Patterns section"; fi
}

test_guidelines_has_persuasion_techniques_section() {
    log_test "prompt-guidelines.md has 'Persuasion Techniques' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Persuasion Techniques' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Persuasion Techniques section"; fi
}

test_guidelines_has_techniques_by_evidence_tier_section() {
    log_test "prompt-guidelines.md has 'Techniques by Evidence Tier' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Techniques by Evidence Tier' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Techniques by Evidence Tier section"; fi
}

test_guidelines_has_anti_patterns_section() {
    log_test "prompt-guidelines.md has 'Anti-Patterns' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Anti-Patterns' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Anti-Patterns section"; fi
}

test_guidelines_has_update_log_section() {
    log_test "prompt-guidelines.md has 'Update Log' section"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '## Update Log' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing Update Log section"; fi
}

# --- SKILL.md content ---

# derived_from: spec:AC-skill-change-format (documents CHANGE/END CHANGE comment format)
test_skill_documents_change_end_change_format() {
    log_test "SKILL.md documents CHANGE/END CHANGE comment format"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    # When we search for both markers
    if grep -q 'CHANGE:' "$SKILL_FILE" && grep -q 'END CHANGE' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing CHANGE/END CHANGE documentation"
    fi
}

# derived_from: spec:AC-skill-approval (references AskUserQuestion with Accept all/Accept some/Reject)
test_skill_has_accept_all_option() {
    log_test "SKILL.md references 'Accept all' approval option"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'Accept all' "$SKILL_FILE"; then log_pass; else log_fail "Missing 'Accept all' option"; fi
}

test_skill_has_accept_some_option() {
    log_test "SKILL.md references 'Accept some' approval option"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'Accept some' "$SKILL_FILE"; then log_pass; else log_fail "Missing 'Accept some' option"; fi
}

test_skill_has_reject_option() {
    log_test "SKILL.md references 'Reject' approval option"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'Reject' "$SKILL_FILE"; then log_pass; else log_fail "Missing 'Reject' option"; fi
}

# derived_from: spec:AC-skill-components (handles 3 component types)
test_skill_handles_skill_type() {
    log_test "SKILL.md documents skill component type detection"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'SKILL.md' "$SKILL_FILE" && grep -q 'skill' "$SKILL_FILE"; then log_pass; else log_fail "Missing skill type documentation"; fi
}

test_skill_handles_agent_type() {
    log_test "SKILL.md documents agent component type detection"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'agents/' "$SKILL_FILE"; then log_pass; else log_fail "Missing agent type documentation"; fi
}

test_skill_handles_command_type() {
    log_test "SKILL.md documents command component type detection"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'commands/' "$SKILL_FILE"; then log_pass; else log_fail "Missing command type documentation"; fi
}

# derived_from: spec:AC-skill-invalid-path (documents invalid path error with valid patterns)
test_skill_documents_invalid_path_error() {
    log_test "SKILL.md documents invalid path error with expected patterns"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'skills/\*/SKILL.md' "$SKILL_FILE" || grep -q 'skills/<name>/SKILL.md' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing invalid path error message with valid pattern examples"
    fi
}

# derived_from: spec:AC-skill-staleness (documents staleness warning with 30-day threshold)
test_skill_documents_staleness_warning() {
    log_test "SKILL.md documents staleness warning with 30-day threshold"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '30' "$SKILL_FILE" && grep -qi 'stale\|staleness' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing staleness warning with 30-day threshold"
    fi
}

# derived_from: spec:AC-skill-yolo (YOLO mode override section present)
test_skill_has_yolo_mode_overrides() {
    log_test "SKILL.md has YOLO Mode Overrides section"
    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'YOLO' "$SKILL_FILE"; then log_pass; else log_fail "Missing YOLO Mode Overrides section"; fi
}

# --- promptimize.md command ---

# derived_from: spec:AC-cmd-delegates (delegates to skill via Skill() call)
test_promptimize_cmd_delegates_to_skill() {
    log_test "promptimize.md delegates to skill via Skill() call"
    if [[ ! -f "$PROMPTIMIZE_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -q 'Skill(' "$PROMPTIMIZE_CMD" && grep -q 'promptimize' "$PROMPTIMIZE_CMD"; then
        log_pass
    else
        log_fail "Missing Skill() delegation to promptimize"
    fi
}

# derived_from: spec:AC-cmd-interactive (asks for component type when no args)
test_promptimize_cmd_asks_component_type() {
    log_test "promptimize.md asks for component type when no arguments"
    if [[ ! -f "$PROMPTIMIZE_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -q 'AskUserQuestion' "$PROMPTIMIZE_CMD" && grep -q 'component' "$PROMPTIMIZE_CMD"; then
        log_pass
    else
        log_fail "Missing AskUserQuestion for component type selection"
    fi
}

# --- refresh-prompt-guidelines.md command ---

# derived_from: spec:AC-refresh-websearch-fallback (documents WebSearch unavailable fallback)
test_refresh_cmd_documents_websearch_fallback() {
    log_test "refresh-prompt-guidelines.md documents WebSearch unavailable fallback"
    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'WebSearch.*unavailable\|unavailable.*WebSearch\|WebSearch is unavailable' "$REFRESH_CMD"; then
        log_pass
    else
        log_fail "Missing WebSearch unavailable fallback documentation"
    fi
}

# derived_from: spec:AC-refresh-dedup (documents deduplication against existing)
test_refresh_cmd_documents_deduplication() {
    log_test "refresh-prompt-guidelines.md documents deduplication/diff against existing"
    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'overlap\|deduplic\|diff.*existing\|compare.*existing\|merge' "$REFRESH_CMD"; then
        log_pass
    else
        log_fail "Missing deduplication documentation"
    fi
}

# derived_from: spec:AC-refresh-changelog (documents changelog update)
test_refresh_cmd_documents_changelog_update() {
    log_test "refresh-prompt-guidelines.md documents changelog/Update Log append"
    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'Update Log\|changelog\|Changelog' "$REFRESH_CMD"; then
        log_pass
    else
        log_fail "Missing changelog/Update Log documentation"
    fi
}

# derived_from: spec:AC-refresh-preserve-sections (all 6 section names listed in preservation step)
test_refresh_cmd_lists_all_6_sections() {
    log_test "refresh-prompt-guidelines.md lists all 6 section names for preservation"
    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    local missing=0
    for section in "Core Principles" "Plugin-Specific Patterns" "Persuasion Techniques" "Techniques by Evidence Tier" "Anti-Patterns" "Update Log"; do
        if ! grep -q "$section" "$REFRESH_CMD"; then
            ((missing++)) || true
        fi
    done
    if [[ "$missing" -eq 0 ]]; then
        log_pass
    else
        log_fail "Missing $missing of 6 expected section names"
    fi
}


# ============================================================
# Dimension 2: Boundary Values
# ============================================================

# derived_from: dimension:boundary (SKILL.md under 500 line budget per CLAUDE.md)
test_skill_under_500_lines() {
    log_test "SKILL.md is under 500 lines (token budget constraint)"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    local lines
    lines=$(wc -l < "$SKILL_FILE" | tr -d ' ')
    if [[ "$lines" -le 500 ]]; then
        log_pass
    else
        log_fail "SKILL.md has $lines lines (max 500)"
    fi
}

# derived_from: dimension:boundary (scoring formula: 9*3=27 max, all pass=100)
test_scoring_formula_max_denominator_is_27() {
    log_test "scoring-rubric.md implies denominator of 27 (9 dims * max 3)"

    if [[ ! -f "$RUBRIC_FILE" ]]; then log_fail "File not found"; return; fi
    # Verify exactly 9 dimension rows in behavioral anchors table (section-scoped)
    local dim_count
    dim_count=$(sed -n '/^## Behavioral Anchors/,/^## /p' "$RUBRIC_FILE" | grep -cE '^\| (Structure|Token|Description|Persuasion|Technique|Prohibition|Example|Progressive|Context)')
    # And verify Pass score is 3
    if [[ "$dim_count" -eq 9 ]] && grep -q 'Pass (3)' "$RUBRIC_FILE"; then
        log_pass
    else
        log_fail "Expected 9 dimensions with Pass(3), found $dim_count dimensions"
    fi
}

# derived_from: dimension:boundary (SKILL.md references /27 or x 100 in scoring formula)
test_skill_documents_scoring_formula() {
    log_test "SKILL.md documents scoring formula with /27 denominator"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    # Check that the formula mentions 27 as denominator
    if grep -q '27' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "SKILL.md missing reference to 27 in scoring formula"
    fi
}


# ============================================================
# Dimension 3: Adversarial / Negative Testing
# ============================================================

# derived_from: dimension:adversarial-zero (guidelines Update Log has at least 1 entry)
test_guidelines_update_log_not_empty() {
    log_test "prompt-guidelines.md Update Log has at least 1 entry row"

    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    # After the "## Update Log" heading, count table rows (exclude header and separator)
    local log_rows
    log_rows=$(sed -n '/^## Update Log/,$ p' "$GUIDELINES_FILE" | grep -cE '^\| [0-9]{4}-' || true)
    if [[ "$log_rows" -ge 1 ]]; then
        log_pass
    else
        log_fail "Update Log has $log_rows date rows (expected >= 1)"
    fi
}

# derived_from: dimension:adversarial-data-integrity (rubric behavioral anchors has no empty cells)
test_rubric_no_empty_table_cells() {
    log_test "scoring-rubric.md behavioral anchors table has no empty cells"

    if [[ ! -f "$RUBRIC_FILE" ]]; then log_fail "File not found"; return; fi
    # Check for adjacent pipes with only whitespace between them (empty cell)
    local empty_cells
    empty_cells=$(grep -E '^\|' "$RUBRIC_FILE" | grep -cE '\|\s*\|' || true)
    # Subtract separator rows (|---|---|) which are expected
    local sep_rows
    sep_rows=$(grep -cE '^\|[-| ]+\|$' "$RUBRIC_FILE" || true)
    local actual_empty=$(( empty_cells - sep_rows ))
    if [[ "$actual_empty" -le 0 ]]; then
        log_pass
    else
        log_fail "Found $actual_empty empty table cell(s) in behavioral anchors"
    fi
}

# derived_from: dimension:adversarial-CRUD (SKILL.md has error handling for missing reference files)
test_skill_has_reference_file_error_handling() {
    log_test "SKILL.md documents error handling for missing reference files"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'not found\|error.*reference\|required reference' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing error handling for missing reference files"
    fi
}


# ============================================================
# Dimension 4: Error Propagation & Failure Modes
# ============================================================

# derived_from: design:error-contract (SKILL.md documents STOP on invalid path)
test_skill_stops_on_invalid_path() {
    log_test "SKILL.md documents STOP on invalid component path"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'STOP' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing STOP directive for invalid path"
    fi
}

# derived_from: design:error-contract (refresh command documents STOP on file not found)
test_refresh_cmd_stops_on_missing_file() {
    log_test "refresh-prompt-guidelines.md documents STOP on file not found"

    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -q 'STOP' "$REFRESH_CMD"; then
        log_pass
    else
        log_fail "Missing STOP directive for file not found"
    fi
}

# derived_from: design:error-contract (SKILL.md malformed marker fallback documented)
test_skill_has_malformed_marker_fallback() {
    log_test "SKILL.md documents malformed marker fallback for Accept-some"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'malformed.*marker\|marker.*fallback\|Selective acceptance unavailable' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing malformed marker fallback documentation"
    fi
}

# derived_from: design:error-contract (promptimize.md command handles empty file discovery)
test_promptimize_cmd_handles_empty_results() {
    log_test "promptimize.md documents handling when no files found"

    if [[ ! -f "$PROMPTIMIZE_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'no.*found\|No.*files found\|STOP' "$PROMPTIMIZE_CMD"; then
        log_pass
    else
        log_fail "Missing empty results handling"
    fi
}

# derived_from: design:error-contract (refresh command documents unparseable agent output)
test_refresh_cmd_handles_unparseable_output() {
    log_test "refresh-prompt-guidelines.md documents unparseable agent output fallback"

    if [[ ! -f "$REFRESH_CMD" ]]; then log_fail "File not found"; return; fi
    if grep -qi 'unparseable\|parse.*fail\|cannot be parsed' "$REFRESH_CMD"; then
        log_pass
    else
        log_fail "Missing unparseable output fallback documentation"
    fi
}


# ============================================================
# Dimension 5: Mutation Mindset (behavioral pinning)
# ============================================================

# derived_from: dimension:mutation-line-deletion (9 specific dimension NAMES present in SKILL.md)
test_skill_lists_all_9_dimension_names() {
    log_test "SKILL.md lists all 9 evaluation dimension names"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    local missing=0
    for dim in "Structure compliance" "Token economy" "Description quality" "Persuasion strength" "Technique currency" "Prohibition clarity" "Example quality" "Progressive disclosure" "Context engineering"; do
        if ! grep -q "$dim" "$SKILL_FILE"; then
            ((missing++)) || true
        fi
    done
    if [[ "$missing" -eq 0 ]]; then
        log_pass
    else
        log_fail "Missing $missing of 9 dimension names in SKILL.md"
    fi
}

# derived_from: dimension:mutation-return-value (SKILL.md report template includes key output fields)
test_skill_report_template_has_required_fields() {
    log_test "SKILL.md report template includes overall score and component type"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'Overall score' "$SKILL_FILE" && grep -q 'Component type' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Report template missing 'Overall score' or 'Component type' fields"
    fi
}

# derived_from: dimension:mutation-logic-inversion (SKILL.md distinguishes pass from partial/fail in issue table)
test_skill_severity_mapping_documented() {
    log_test "SKILL.md documents severity mapping (fail=blocker, partial=warning)"

    if [[ ! -f "$SKILL_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q 'blocker' "$SKILL_FILE" && grep -q 'warning' "$SKILL_FILE"; then
        log_pass
    else
        log_fail "Missing severity mapping documentation"
    fi
}

# derived_from: dimension:mutation-line-deletion (guidelines sections subsection structure intact)
test_guidelines_has_skills_subsection() {
    log_test "prompt-guidelines.md Plugin-Specific Patterns has Skills subsection"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '### Skills' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing ### Skills subsection"; fi
}

test_guidelines_has_agents_subsection() {
    log_test "prompt-guidelines.md Plugin-Specific Patterns has Agents subsection"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '### Agents' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing ### Agents subsection"; fi
}

test_guidelines_has_commands_subsection() {
    log_test "prompt-guidelines.md Plugin-Specific Patterns has Commands subsection"
    if [[ ! -f "$GUIDELINES_FILE" ]]; then log_fail "File not found"; return; fi
    if grep -q '### Commands' "$GUIDELINES_FILE"; then log_pass; else log_fail "Missing ### Commands subsection"; fi
}


# ============================================================
# Integration: validate.sh passes for all new files
# ============================================================

# derived_from: spec:AC-validate (all new files pass structural validation with 0 errors)
test_validate_sh_passes() {
    log_test "validate.sh passes with 0 errors (integration)"

    cd "$PROJECT_ROOT"
    local output exit_code=0
    output=$(bash ./validate.sh 2>&1) || exit_code=$?
    if [[ "$exit_code" -eq 0 ]]; then
        log_pass
    else
        log_fail "validate.sh exited with code $exit_code"
    fi
    cd "$SCRIPT_DIR"
}


# ============================================================
# Run all tests
# ============================================================
main() {
    echo "=========================================="
    echo "Promptimize Content Regression Tests"
    echo "=========================================="
    echo ""

    echo "--- Dimension 1: BDD Scenarios ---"
    echo ""

    # scoring-rubric.md
    test_rubric_has_exactly_9_dimensions
    test_rubric_has_pass_partial_fail_columns
    test_rubric_has_component_type_applicability_table
    test_rubric_has_auto_pass_entries
    test_rubric_applicability_has_three_component_columns

    # prompt-guidelines.md
    test_guidelines_has_last_updated_date
    test_guidelines_has_at_least_15_guidelines
    test_guidelines_has_core_principles_section
    test_guidelines_has_plugin_specific_patterns_section
    test_guidelines_has_persuasion_techniques_section
    test_guidelines_has_techniques_by_evidence_tier_section
    test_guidelines_has_anti_patterns_section
    test_guidelines_has_update_log_section

    # SKILL.md
    test_skill_documents_change_end_change_format
    test_skill_has_accept_all_option
    test_skill_has_accept_some_option
    test_skill_has_reject_option
    test_skill_handles_skill_type
    test_skill_handles_agent_type
    test_skill_handles_command_type
    test_skill_documents_invalid_path_error
    test_skill_documents_staleness_warning
    test_skill_has_yolo_mode_overrides

    # promptimize.md command
    test_promptimize_cmd_delegates_to_skill
    test_promptimize_cmd_asks_component_type

    # refresh-prompt-guidelines.md command
    test_refresh_cmd_documents_websearch_fallback
    test_refresh_cmd_documents_deduplication
    test_refresh_cmd_documents_changelog_update
    test_refresh_cmd_lists_all_6_sections

    echo ""
    echo "--- Dimension 2: Boundary Values ---"
    echo ""

    test_skill_under_500_lines
    test_scoring_formula_max_denominator_is_27
    test_skill_documents_scoring_formula

    echo ""
    echo "--- Dimension 3: Adversarial / Negative ---"
    echo ""

    test_guidelines_update_log_not_empty
    test_rubric_no_empty_table_cells
    test_skill_has_reference_file_error_handling

    echo ""
    echo "--- Dimension 4: Error Propagation ---"
    echo ""

    test_skill_stops_on_invalid_path
    test_refresh_cmd_stops_on_missing_file
    test_skill_has_malformed_marker_fallback
    test_promptimize_cmd_handles_empty_results
    test_refresh_cmd_handles_unparseable_output

    echo ""
    echo "--- Dimension 5: Mutation Mindset ---"
    echo ""

    test_skill_lists_all_9_dimension_names
    test_skill_report_template_has_required_fields
    test_skill_severity_mapping_documented
    test_guidelines_has_skills_subsection
    test_guidelines_has_agents_subsection
    test_guidelines_has_commands_subsection

    echo ""
    echo "--- Integration ---"
    echo ""

    test_validate_sh_passes

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

main
