#!/usr/bin/env bash
# Release script for iflow plugin
# Copies iflow-dev to iflow, calculates version, and creates tagged release

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() { echo -e "${RED}Error: $1${NC}" >&2; exit 1; }
success() { echo -e "${GREEN}$1${NC}"; }
warn() { echo -e "${YELLOW}$1${NC}"; }

# File paths
PLUGIN_DEV_JSON="plugins/iflow-dev/.claude-plugin/plugin.json"
PLUGIN_PROD_JSON="plugins/iflow/.claude-plugin/plugin.json"
MARKETPLACE_JSON=".claude-plugin/marketplace.json"

#############################################
# Precondition checks
#############################################

check_preconditions() {
    # Must be on develop branch
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "develop" ]]; then
        error "Must be on 'develop' branch. Currently on '$current_branch'."
    fi

    # Working tree must be clean
    if ! git diff --quiet || ! git diff --cached --quiet; then
        error "Working tree has uncommitted changes. Commit or stash them first."
    fi

    # Must have upstream
    if ! git remote get-url origin &>/dev/null; then
        error "No 'origin' remote configured."
    fi

    # Both plugin directories must exist
    if [[ ! -d "plugins/iflow-dev" ]]; then
        error "plugins/iflow-dev directory not found."
    fi
    if [[ ! -d "plugins/iflow" ]]; then
        error "plugins/iflow directory not found."
    fi

    success "Preconditions passed"
}

#############################################
# Plugin reference validation
#############################################

validate_dev_references() {
    # iflow-dev should ONLY have iflow-dev: references, not /iflow:
    # This catches cases where someone accidentally used the wrong prefix
    if grep -r "/iflow:" plugins/iflow-dev --include="*.md" >/dev/null 2>&1; then
        error "Found /iflow: references in iflow-dev. Use /iflow-dev: instead."
        echo "Run: grep -rn '/iflow:' plugins/iflow-dev --include='*.md'"
        exit 1
    fi
    success "All references use correct iflow-dev: prefix"
}

#############################################
# Version calculation from code change percentage
#############################################

get_last_tag() {
    git tag --sort=-v:refname | head -1
}

calculate_bump_type() {
    local last_tag=$1

    # Get lines changed since last tag (additions + deletions)
    local lines_changed diff_output
    if [[ -z "$last_tag" ]]; then
        # Compare against empty tree for initial release
        diff_output=$(git diff --stat --stat-count=999999 4b825dc642cb6eb9a060e54bf8d69288fbee4904 HEAD 2>/dev/null | tail -1)
    else
        diff_output=$(git diff --stat --stat-count=999999 "${last_tag}..HEAD" 2>/dev/null | tail -1)
    fi

    # Extract insertions and deletions, sum them
    local insertions deletions
    insertions=$(echo "$diff_output" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo 0)
    deletions=$(echo "$diff_output" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo 0)
    lines_changed=$((${insertions:-0} + ${deletions:-0}))

    # Handle no changes
    if [[ -z "$lines_changed" ]] || [[ "$lines_changed" -eq 0 ]]; then
        echo ""
        return
    fi

    # Get total lines in codebase (tracked files only)
    local total_lines
    total_lines=$(git ls-files | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')

    # Calculate percentage
    local percentage
    percentage=$(echo "scale=2; $lines_changed * 100 / $total_lines" | bc)

    # Export for display in main()
    export CHANGE_STATS="$lines_changed lines changed / $total_lines total = ${percentage}%"

    # Determine bump type based on thresholds:
    # >10% = major, 3-10% = minor, ≤3% = patch
    if (( $(echo "$percentage > 10" | bc -l) )); then
        echo "major"
    elif (( $(echo "$percentage > 3" | bc -l) )); then
        echo "minor"
    else
        echo "patch"
    fi
}

get_dev_version() {
    if [[ -f "$PLUGIN_DEV_JSON" ]]; then
        grep -o '"version": *"[^"]*"' "$PLUGIN_DEV_JSON" | sed 's/"version": *"\([^"]*\)"/\1/' | sed 's/-dev$//'
    else
        echo "1.0.0"
    fi
}

bump_version() {
    local current=$1
    local bump_type=$2

    IFS='.' read -r major minor patch <<< "$current"

    case "$bump_type" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "${major}.$((minor + 1)).0"
            ;;
        patch)
            echo "${major}.${minor}.$((patch + 1))"
            ;;
        *)
            error "Invalid bump type: $bump_type"
            ;;
    esac
}

#############################################
# File updates
#############################################

copy_dev_to_prod() {
    success "Copying iflow-dev to iflow..."
    cp -r plugins/iflow-dev/* plugins/iflow/

    # Convert plugin references from iflow-dev to iflow
    # This handles both command refs (/iflow-dev:verify → /iflow:verify)
    # and subagent refs (iflow-dev:prd-reviewer → iflow:prd-reviewer)
    find plugins/iflow -name "*.md" -exec sed -i '' 's|iflow-dev:|iflow:|g' {} \;

    success "Copied and converted plugin references"
}

update_plugin_files() {
    local new_version=$1
    local next_dev_version=$2

    # Update iflow (production) plugin.json
    # Change name from iflow-dev to iflow, set release version
    sed -i '' 's/"name": *"iflow-dev"/"name": "iflow"/' "$PLUGIN_PROD_JSON"
    sed -i '' "s/\"version\": *\"[^\"]*\"/\"version\": \"$new_version\"/" "$PLUGIN_PROD_JSON"
    success "Updated $PLUGIN_PROD_JSON: name=iflow, version=$new_version"

    # Update iflow-dev plugin.json with next dev version
    sed -i '' "s/\"version\": *\"[^\"]*\"/\"version\": \"${next_dev_version}-dev\"/" "$PLUGIN_DEV_JSON"
    success "Updated $PLUGIN_DEV_JSON: version=${next_dev_version}-dev"
}

update_marketplace() {
    local new_version=$1
    local next_dev_version=$2

    # Update iflow version in marketplace
    # Use python for reliable JSON manipulation
    python3 -c "
import json

with open('$MARKETPLACE_JSON', 'r') as f:
    data = json.load(f)

for plugin in data['plugins']:
    if plugin['name'] == 'iflow':
        plugin['version'] = '$new_version'
    elif plugin['name'] == 'iflow-dev':
        plugin['version'] = '${next_dev_version}-dev'

with open('$MARKETPLACE_JSON', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
    success "Updated $MARKETPLACE_JSON: iflow=$new_version, iflow-dev=${next_dev_version}-dev"
}

#############################################
# Git operations
#############################################

commit_and_release() {
    local new_version=$1
    local tag="v$new_version"

    # Stage changes with IFLOW_RELEASE=1 to bypass hook
    export IFLOW_RELEASE=1
    git add plugins/ .claude-plugin/
    git commit -m "chore(release): v$new_version"
    success "Committed release changes"

    # Push develop
    git push origin develop
    success "Pushed develop"

    # Merge to main
    git checkout main
    git pull origin main
    git merge develop --no-ff -m "Merge release v$new_version"
    success "Merged develop into main"

    # Create and push tag
    git tag "$tag"
    git push origin main
    git push origin "$tag"
    success "Created and pushed tag $tag"

    # Return to develop
    git checkout develop
    success "Returned to develop branch"
}

#############################################
# Main
#############################################

main() {
    echo "=== iflow Plugin Release Script (Two-Plugin Model) ==="
    echo ""

    # Check preconditions
    check_preconditions

    # Get last tag
    local last_tag
    last_tag=$(get_last_tag)
    if [[ -n "$last_tag" ]]; then
        echo "Last tag: $last_tag"
    else
        echo "No previous tags found"
    fi

    # Calculate bump type
    local bump_type
    bump_type=$(calculate_bump_type "$last_tag")
    if [[ -z "$bump_type" ]]; then
        error "No code changes found since last tag."
    fi
    echo "Code changes: $CHANGE_STATS"
    echo "Bump type: $bump_type (≤3% → patch, 3-10% → minor, >10% → major)"

    # Get current dev version (strip -dev suffix) and calculate new version
    local dev_version new_version next_dev_version
    dev_version=$(get_dev_version)
    new_version="$dev_version"  # The dev version IS the target release version
    next_dev_version=$(bump_version "$new_version" "minor")

    echo "Release version: $new_version"
    echo "Next dev version: ${next_dev_version}-dev"
    echo ""

    # Confirm
    read -p "Proceed with release? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warn "Release cancelled"
        exit 0
    fi

    # Validate plugin references before copying
    validate_dev_references

    # Copy dev to prod
    copy_dev_to_prod

    # Update plugin files
    update_plugin_files "$new_version" "$next_dev_version"

    # Update marketplace
    update_marketplace "$new_version" "$next_dev_version"

    # Commit and release
    commit_and_release "$new_version"

    echo ""
    success "=== Released v$new_version ==="
    echo "iflow plugin is now at v$new_version"
    echo "iflow-dev plugin is now at v${next_dev_version}-dev"
}

main "$@"
