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
    if ! python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
        log_error "$file: Invalid JSON syntax"
        return 1
    fi

    # Check required fields
    local content=$(cat "$file")

    if ! echo "$content" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'name' in d" 2>/dev/null; then
        log_error "$file: Missing 'name' field"
        return 1
    fi

    if ! echo "$content" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'version' in d" 2>/dev/null; then
        log_error "$file: Missing 'version' field"
        return 1
    fi

    if ! echo "$content" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'description' in d" 2>/dev/null; then
        log_error "$file: Missing 'description' field"
        return 1
    fi

    return 0
}

# Validate marketplace.json
validate_marketplace_json() {
    local file=$1

    # Check JSON syntax
    if ! python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
        log_error "$file: Invalid JSON syntax"
        return 1
    fi

    # Check required fields
    local content=$(cat "$file")

    if ! echo "$content" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'name' in d" 2>/dev/null; then
        log_error "$file: Missing 'name' field"
        return 1
    fi

    if ! echo "$content" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'plugins' in d" 2>/dev/null; then
        log_error "$file: Missing 'plugins' array"
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
done < <(find . -type f -name "SKILL.md" -path "./skills/*" 2>/dev/null)
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
done < <(find . -type f -name "*.md" -path "./agents/*" 2>/dev/null)
if [ $agent_count -eq 0 ]; then
    log_info "No agents found"
fi
echo ""

# Validate commands (commands/*.md - check for description field in frontmatter)
echo "Validating Commands..."
cmd_count=0
while IFS= read -r cmd_file; do
    [ -z "$cmd_file" ] && continue
    log_info "Checking $cmd_file"
    # Commands require description in frontmatter
    local_content=$(cat "$cmd_file")
    if ! echo "$local_content" | head -1 | grep -q "^---$"; then
        log_error "$cmd_file: Missing opening frontmatter marker (---)"
    elif ! echo "$local_content" | sed -n '/^---$/,/^---$/p' | grep -q "^description:"; then
        log_error "$cmd_file: Missing 'description' field in frontmatter"
    else
        log_success "Frontmatter valid"
    fi
    ((cmd_count++)) || true
done < <(find . -type f -name "*.md" -path "./commands/*" 2>/dev/null)
if [ $cmd_count -eq 0 ]; then
    log_info "No commands found"
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