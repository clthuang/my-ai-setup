#!/usr/bin/env bash
# Release script for iflow plugin
# Copies iflow-dev to iflow, calculates version, and creates tagged release

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# CI mode - skip interactive confirmation
CI_MODE=false
if [[ "${1:-}" == "--ci" ]] || [[ "${CI:-}" == "true" ]]; then
    CI_MODE=true
fi

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
# CHANGELOG validation
#############################################

check_changelog() {
    if [[ ! -f "CHANGELOG.md" ]]; then
        warn "CHANGELOG.md not found, skipping validation"
        return
    fi

    # Check if there's content under [Unreleased]
    local unreleased_content
    unreleased_content=$(sed -n '/^## \[Unreleased\]/,/^## \[/{/^## \[/d;/^$/d;p;}' CHANGELOG.md)

    if [[ -z "$unreleased_content" ]]; then
        if [[ "$CI_MODE" == "true" ]]; then
            error "CHANGELOG.md has no entries under [Unreleased]. Add changelog entries before releasing."
        else
            warn "CHANGELOG.md has no entries under [Unreleased]."
            read -p "Continue without changelog entries? (y/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                warn "Release cancelled — add CHANGELOG entries and retry."
                exit 0
            fi
        fi
    else
        success "CHANGELOG has unreleased entries"
    fi
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

    # Determine bump type based on thresholds:
    # >10% = major, 3-10% = minor, ≤3% = patch
    local bump_type
    if (( $(echo "$percentage > 10" | bc -l) )); then
        bump_type="major"
    elif (( $(echo "$percentage > 3" | bc -l) )); then
        bump_type="minor"
    else
        bump_type="patch"
    fi

    # Output bump type and stats (newline-separated for parsing)
    echo "$bump_type"
    echo "$lines_changed lines changed / $total_lines total = ${percentage}%"
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
    success "Syncing iflow-dev to iflow (with deletions)..."
    rsync -av --delete --exclude='.claude-plugin/plugin.json' --exclude='.venv' plugins/iflow-dev/ plugins/iflow/

    # Blanket convert iflow-dev → iflow in all markdown files
    # Handles all separators: colon (iflow-dev:cmd), dot (iflow-dev.local.md),
    # slash (plugins/iflow-dev/skills/...), and any future patterns
    find plugins/iflow -name "*.md" -exec sed -i '' 's/iflow-dev/iflow/g' {} \;

    # Blanket convert in shell scripts, excluding cross-plugin scripts
    # that legitimately reference both iflow and iflow-dev directories
    find plugins/iflow -name "*.sh" \
        ! -name "pre-commit-guard.sh" \
        ! -name "sync-cache.sh" \
        -exec sed -i '' 's/iflow-dev/iflow/g' {} \;

    # Blanket convert in Python files
    find plugins/iflow -name "*.py" \
        -exec sed -i '' 's/iflow-dev/iflow/g' {} \;

    # Verification gate: fail release if unconverted references leak through
    local remaining
    remaining=$(grep -rn "iflow-dev" plugins/iflow/ --include="*.md" --include="*.sh" --include="*.py" \
        | grep -v "pre-commit-guard.sh" \
        | grep -v "sync-cache.sh" || true)
    if [[ -n "$remaining" ]]; then
        error "Unconverted iflow-dev references found in released plugin:"
        echo "$remaining"
        exit 1
    fi

    success "Copied and converted plugin references"
}

update_plugin_files() {
    local new_version=$1
    local next_dev_version=$2

    # Copy dev plugin.json as base (so mcpServers and any new fields propagate),
    # then sed name and version to production values.
    cp "$PLUGIN_DEV_JSON" "$PLUGIN_PROD_JSON"
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
# CHANGELOG promotion
#############################################

promote_changelog() {
    local new_version=$1
    local today
    today=$(date +%Y-%m-%d)

    if [[ ! -f "CHANGELOG.md" ]]; then
        warn "CHANGELOG.md not found, skipping promotion"
        return
    fi

    # Check if there's content under [Unreleased] (non-empty lines before next ## header)
    local unreleased_content
    unreleased_content=$(sed -n '/^## \[Unreleased\]/,/^## \[/{/^## \[/d;/^$/d;p;}' CHANGELOG.md)

    if [[ -z "$unreleased_content" ]]; then
        warn "No unreleased CHANGELOG entries to promote"
        return
    fi

    # Insert versioned header after [Unreleased] line
    sed -i '' "s/^## \[Unreleased\]$/## [Unreleased]\n\n## [$new_version] - $today/" CHANGELOG.md
    success "Promoted CHANGELOG [Unreleased] entries to [$new_version] - $today"
}

#############################################
# Git operations
#############################################

commit_and_release() {
    local new_version=$1
    local tag="v$new_version"

    # Stage changes with IFLOW_RELEASE=1 to bypass hook
    export IFLOW_RELEASE=1
    git add plugins/ .claude-plugin/ CHANGELOG.md
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

    # Validate CHANGELOG has unreleased entries
    check_changelog

    # Get last tag
    local last_tag
    last_tag=$(get_last_tag)
    if [[ -n "$last_tag" ]]; then
        echo "Last tag: $last_tag"
    else
        echo "No previous tags found"
    fi

    # Calculate bump type and change stats
    local bump_output bump_type change_stats
    bump_output=$(calculate_bump_type "$last_tag")
    if [[ -z "$bump_output" ]]; then
        error "No code changes found since last tag."
    fi
    bump_type=$(echo "$bump_output" | head -1)
    change_stats=$(echo "$bump_output" | tail -1)
    echo "Code changes: $change_stats"
    echo "Bump type: $bump_type (≤3% → patch, 3-10% → minor, >10% → major)"

    # Calculate new version by bumping from last tag
    local last_version new_version next_dev_version
    last_version="${last_tag#v}"  # v1.6.0 → 1.6.0
    new_version=$(bump_version "$last_version" "$bump_type")
    next_dev_version="$new_version"

    echo "Release version: $new_version"
    echo "Next dev version: ${next_dev_version}-dev"
    echo ""

    # Confirm
    if [[ "$CI_MODE" == "true" ]]; then
        success "CI mode: auto-confirming release"
    else
        read -p "Proceed with release? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "Release cancelled"
            exit 0
        fi
    fi

    # Validate plugin references before copying
    validate_dev_references

    # Copy dev to prod
    copy_dev_to_prod

    # Update plugin files
    update_plugin_files "$new_version" "$next_dev_version"

    # Update marketplace
    update_marketplace "$new_version" "$next_dev_version"

    # Promote CHANGELOG [Unreleased] to versioned entry
    promote_changelog "$new_version"

    # Commit and release
    commit_and_release "$new_version"

    echo ""
    success "=== Released v$new_version ==="
    echo "iflow plugin is now at v$new_version"
    echo "iflow-dev plugin is now at v${next_dev_version}-dev"
}

main "$@"
