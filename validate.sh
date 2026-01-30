#!/bin/bash
# Validation script for agent-teams repository
# Validates skills, agents, plugins, and commands

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}ERROR: $1${NC}"
    ((ERRORS++)) || true
}

log_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
    ((WARNINGS++)) || true
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_info() {
    echo -e "  $1"
}

# Validate YAML frontmatter
validate_frontmatter() {
    local file=$1
    local content=$(cat "$file")

    # Check for frontmatter markers
    if ! echo "$content" | head -1 | grep -q "^---$"; then
        log_error "$file: Missing opening frontmatter marker (---)"
        return 1
    fi

    # Extract frontmatter
    local frontmatter=$(echo "$content" | sed -n '/^---$/,/^---$/p' | sed '1d;$d')

    # Check for name field
    if ! echo "$frontmatter" | grep -q "^name:"; then
        log_error "$file: Missing 'name' field in frontmatter"
        return 1
    fi

    # Check for description field
    if ! echo "$frontmatter" | grep -q "^description:"; then
        log_error "$file: Missing 'description' field in frontmatter"
        return 1
    fi

    # Validate name format (lowercase, hyphens only)
    local name=$(echo "$frontmatter" | grep "^name:" | sed 's/^name:[[:space:]]*//')
    if ! echo "$name" | grep -qE "^[a-z][a-z0-9-]*$"; then
        log_error "$file: Name '$name' must be lowercase with hyphens only"
        return 1
    fi

    return 0
}

# Validate skill description quality
validate_description() {
    local file=$1
    local content=$(cat "$file")
    local frontmatter=$(echo "$content" | sed -n '/^---$/,/^---$/p' | sed '1d;$d')
    local description=$(echo "$frontmatter" | grep "^description:" | sed 's/^description:[[:space:]]*//')

    # Check minimum length
    if [ ${#description} -lt 50 ]; then
        log_warning "$file: Description is short (<50 chars). Consider adding more detail."
    fi

    # Check for "Use when" pattern
    if ! echo "$description" | grep -qi "use when\|use for\|triggered when"; then
        log_warning "$file: Description should include when to use it (e.g., 'Use when...')"
    fi

    # Check for first-person language
    if echo "$description" | grep -qiE "^(I |You can|This lets you)"; then
        log_warning "$file: Description should be third-person (e.g., 'Creates...' not 'You can create...')"
    fi
}

# Validate SKILL.md line count
validate_skill_size() {
    local file=$1
    local lines=$(wc -l < "$file")

    if [ "$lines" -gt 500 ]; then
        log_warning "$file: SKILL.md has $lines lines (recommended <500). Consider using reference files."
    fi
}

# Validate plugin.json
validate_plugin_json() {
    local file=$1

    # Check JSON syntax
    if ! jq empty "$file" 2>/dev/null; then
        log_error "$file: Invalid JSON syntax"
        return 1
    fi

    # Check required fields (only 'name' is required per official docs)
    if ! jq -e '.name' "$file" > /dev/null 2>&1; then
        log_error "$file: Missing required 'name' field"
        return 1
    fi

    # Validate name format (kebab-case)
    local name=$(jq -r '.name' "$file")
    if ! echo "$name" | grep -qE "^[a-z][a-z0-9-]*$"; then
        log_error "$file: Name '$name' must be kebab-case (lowercase with hyphens)"
        return 1
    fi

    return 0
}

# Validate marketplace.json
validate_marketplace_json() {
    local file=$1

    # Check JSON syntax
    if ! jq empty "$file" 2>/dev/null; then
        log_error "$file: Invalid JSON syntax"
        return 1
    fi

    # Check required fields
    if ! jq -e '.name' "$file" > /dev/null 2>&1; then
        log_error "$file: Missing 'name' field"
        return 1
    fi

    if ! jq -e '.plugins' "$file" > /dev/null 2>&1; then
        log_error "$file: Missing 'plugins' array"
        return 1
    fi

    # Validate plugins is an array
    if ! jq -e '.plugins | type == "array"' "$file" > /dev/null 2>&1; then
        log_error "$file: 'plugins' must be an array"
        return 1
    fi

    return 0
}

# Main validation
echo "=========================================="
echo "Agent Teams Repository Validation"
echo "=========================================="
echo ""

# Validate skills (supports nested directories: skills/*/SKILL.md and skills/*/*/SKILL.md)
echo "Validating Skills..."
skill_count=0
while IFS= read -r skill_file; do
    [ -z "$skill_file" ] && continue
    log_info "Checking $skill_file"
    validate_frontmatter "$skill_file" && log_success "Frontmatter valid"
    validate_description "$skill_file"
    validate_skill_size "$skill_file"
    ((skill_count++)) || true
done < <(find . -type f -name "SKILL.md" \( -path "./skills/*" -o -path "./plugins/*/skills/*" \) 2>/dev/null)
if [ $skill_count -eq 0 ]; then
    log_info "No skills found"
fi
echo ""

# Validate agents (agents/*/*.md - each agent in its own subdirectory)
echo "Validating Agents..."
agent_count=0
while IFS= read -r agent_file; do
    [ -z "$agent_file" ] && continue
    log_info "Checking $agent_file"
    validate_frontmatter "$agent_file" && log_success "Frontmatter valid"
    validate_description "$agent_file"
    ((agent_count++)) || true
done < <(find . -type f -name "*.md" \( -path "./agents/*" -o -path "./plugins/*/agents/*" \) 2>/dev/null)
if [ $agent_count -eq 0 ]; then
    log_info "No agents found"
fi
echo ""

# Validate commands (commands/*.md - all frontmatter fields are optional per official docs)
echo "Validating Commands..."
cmd_count=0
while IFS= read -r cmd_file; do
    [ -z "$cmd_file" ] && continue
    log_info "Checking $cmd_file"
    local_content=$(cat "$cmd_file")

    # Check if frontmatter exists (optional but validate if present)
    if echo "$local_content" | head -1 | grep -q "^---$"; then
        cmd_frontmatter=$(echo "$local_content" | sed -n '/^---$/,/^---$/p' | sed '1d;$d')

        # Validate model field if present (must be sonnet, opus, or haiku)
        if echo "$cmd_frontmatter" | grep -q "^model:"; then
            cmd_model=$(echo "$cmd_frontmatter" | grep "^model:" | sed 's/^model:[[:space:]]*//')
            if ! echo "sonnet opus haiku" | grep -qw "$cmd_model"; then
                log_error "$cmd_file: Invalid model '$cmd_model' (must be sonnet, opus, or haiku)"
            fi
        fi

        log_success "Frontmatter valid"
    else
        log_success "No frontmatter (valid - all fields optional)"
    fi
    ((cmd_count++)) || true
done < <(find . -type f -name "*.md" \( -path "./commands/*" -o -path "./plugins/*/commands/*" \) 2>/dev/null)
if [ $cmd_count -eq 0 ]; then
    log_info "No commands found"
fi
echo ""

# Validate hooks
echo "Validating Hooks..."
hooks_found=0
for hooks_dir in hooks plugins/*/hooks; do
    [ -d "$hooks_dir" ] || continue

    if [ -f "$hooks_dir/hooks.json" ]; then
        hooks_found=1
        log_info "Checking $hooks_dir/hooks.json"
        if jq empty "$hooks_dir/hooks.json" 2>/dev/null; then
            log_success "hooks.json valid JSON"
        else
            log_error "$hooks_dir/hooks.json: Invalid JSON syntax"
        fi

        # Check shell scripts are executable
        for hook_script in "$hooks_dir"/*.sh; do
            if [ -f "$hook_script" ]; then
                log_info "Checking $hook_script"
                if [ -x "$hook_script" ]; then
                    log_success "$hook_script is executable"
                else
                    log_error "$hook_script is not executable (run: chmod +x $hook_script)"
                fi
            fi
        done

        # Run hook integration tests if available
        if [ -f "$hooks_dir/tests/test-hooks.sh" ]; then
            log_info "Running hook integration tests..."
            if [ -x "$hooks_dir/tests/test-hooks.sh" ]; then
                if "$hooks_dir/tests/test-hooks.sh" > /tmp/hook-tests-output.txt 2>&1; then
                    log_success "Hook integration tests passed"
                else
                    log_error "Hook integration tests failed"
                    cat /tmp/hook-tests-output.txt
                fi
            else
                log_error "$hooks_dir/tests/test-hooks.sh is not executable"
            fi
        fi
    fi
done
if [ $hooks_found -eq 0 ]; then
    log_info "No hooks/hooks.json found"
fi
echo ""

# Validate feature metadata
echo "Validating Feature Metadata..."
feature_count=0
while IFS= read -r meta_file; do
    [ -z "$meta_file" ] && continue
    log_info "Checking $meta_file"

    # Validate .meta.json structure and fields
    validation_output=$(python3 -c "
import json
import sys

required = ['id', 'mode', 'status', 'created', 'branch']
deprecated = ['worktree', 'currentPhase', 'phases']

try:
    with open('$meta_file') as f:
        meta = json.load(f)
except json.JSONDecodeError as e:
    print(f'ERROR: Invalid JSON: {e}')
    sys.exit(1)

errors = []
warnings = []

# Check required fields (slug or name accepted)
for field in required:
    if field not in meta:
        errors.append(f'Missing required field: {field}')

# Check slug/name (prefer slug, accept name for backwards compatibility)
if 'slug' not in meta:
    if 'name' in meta:
        warnings.append(\"Field 'name' should be renamed to 'slug'\")
    else:
        errors.append('Missing required field: slug (or name)')

# Check deprecated fields
for field in deprecated:
    if field in meta:
        warnings.append(f\"Deprecated field '{field}' should be removed\")

# Status consistency checks
status = meta.get('status')
completed = meta.get('completed')

if status == 'active' and completed is not None:
    errors.append(\"Status is 'active' but 'completed' is set\")

if status in ['completed', 'abandoned'] and completed is None:
    errors.append(f\"Status is '{status}' but 'completed' is not set\")

for e in errors:
    print(f'ERROR: {e}')
for w in warnings:
    print(f'WARNING: {w}')

sys.exit(1 if errors else 0)
" 2>&1)

    python_exit=$?
    if [ $python_exit -eq 0 ]; then
        if [ -n "$validation_output" ]; then
            # Has warnings but no errors - use here-string to avoid subshell
            while IFS= read -r line; do
                [[ "$line" == WARNING:* ]] && log_warning "${line#WARNING: }"
            done <<< "$validation_output"
            log_success ".meta.json valid (with warnings)"
        else
            log_success ".meta.json valid"
        fi
    else
        # Use here-string to avoid subshell variable scope issue
        while IFS= read -r line; do
            [[ "$line" == ERROR:* ]] && log_error "$meta_file: ${line#ERROR: }"
            [[ "$line" == WARNING:* ]] && log_warning "${line#WARNING: }"
        done <<< "$validation_output"
    fi
    ((feature_count++)) || true
done < <(find docs/features -name ".meta.json" -type f 2>/dev/null)
if [ $feature_count -eq 0 ]; then
    log_info "No feature metadata found"
fi
echo ""

# Validate plugin.json files
echo "Validating Plugin Manifests..."
for plugin_json in $(find . -path "*/.claude-plugin/plugin.json" -type f 2>/dev/null); do
    log_info "Checking $plugin_json"
    validate_plugin_json "$plugin_json" && log_success "plugin.json valid"
done
echo ""

# Validate marketplace.json
echo "Validating Marketplace..."
for marketplace_json in $(find . -path "*/.claude-plugin/marketplace.json" -type f 2>/dev/null); do
    log_info "Checking $marketplace_json"
    validate_marketplace_json "$marketplace_json" && log_success "marketplace.json valid"
done
echo ""

# Summary
echo "=========================================="
echo "Validation Complete"
echo "=========================================="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Validation failed with $ERRORS error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}Validation passed${NC}"
    exit 0
fi