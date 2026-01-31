#!/usr/bin/env bash
# Release script for iflow plugin
# Calculates version from conventional commits and creates tagged release

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
PLUGIN_JSON="plugins/iflow/.claude-plugin/plugin.json"
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

    success "Preconditions passed"
}

#############################################
# Version calculation from conventional commits
#############################################

get_last_tag() {
    git describe --tags --abbrev=0 2>/dev/null || echo ""
}

calculate_bump_type() {
    local last_tag=$1
    local commits

    if [[ -z "$last_tag" ]]; then
        # No previous tag, look at all commits
        commits=$(git log --pretty=format:"%s%n%b" 2>/dev/null)
    else
        # Commits since last tag
        commits=$(git log "${last_tag}..HEAD" --pretty=format:"%s%n%b" 2>/dev/null)
    fi

    if [[ -z "$commits" ]]; then
        echo ""
        return
    fi

    # Check for BREAKING CHANGE (major bump)
    if echo "$commits" | grep -qE "^BREAKING CHANGE:|!:"; then
        echo "major"
        return
    fi

    # Check for feat: (minor bump)
    if echo "$commits" | grep -qE "^feat(\(.+\))?:"; then
        echo "minor"
        return
    fi

    # Check for fix: (patch bump)
    if echo "$commits" | grep -qE "^fix(\(.+\))?:"; then
        echo "patch"
        return
    fi

    # No conventional commits found
    echo ""
}

get_current_version() {
    if [[ -f "$PLUGIN_JSON" ]]; then
        grep -o '"version": *"[^"]*"' "$PLUGIN_JSON" | sed 's/"version": *"\([^"]*\)"/\1/'
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

update_version_in_files() {
    local new_version=$1

    # Update plugin.json
    if [[ -f "$PLUGIN_JSON" ]]; then
        sed -i '' "s/\"version\": *\"[^\"]*\"/\"version\": \"$new_version\"/" "$PLUGIN_JSON"
        success "Updated $PLUGIN_JSON to v$new_version"
    else
        error "Plugin JSON not found: $PLUGIN_JSON"
    fi

    # Update marketplace.json version
    if [[ -f "$MARKETPLACE_JSON" ]]; then
        sed -i '' "s/\"version\": *\"[^\"]*\"/\"version\": \"$new_version\"/" "$MARKETPLACE_JSON"
        success "Updated $MARKETPLACE_JSON to v$new_version"
    else
        error "Marketplace JSON not found: $MARKETPLACE_JSON"
    fi
}

# Convert marketplace.json to public format (for main branch)
convert_to_public_marketplace() {
    if [[ -f "$MARKETPLACE_JSON" ]]; then
        # Change plugin name from iflow-dev to iflow
        sed -i '' 's/"name": *"iflow-dev"/"name": "iflow"/' "$MARKETPLACE_JSON"
        # Change marketplace name to public
        sed -i '' 's/"name": *"my-local-plugins"/"name": "iflow-plugins"/' "$MARKETPLACE_JSON"
        # Update description
        sed -i '' 's/"description": *"Personal local plugins marketplace (development)"/"description": "iflow plugin marketplace"/' "$MARKETPLACE_JSON"
        success "Converted marketplace.json to public format"
    fi
}

# Convert marketplace.json back to dev format (for develop branch)
convert_to_dev_marketplace() {
    if [[ -f "$MARKETPLACE_JSON" ]]; then
        # Change plugin name from iflow to iflow-dev
        sed -i '' 's/"name": *"iflow"/"name": "iflow-dev"/' "$MARKETPLACE_JSON"
        # Change marketplace name to local
        sed -i '' 's/"name": *"iflow-plugins"/"name": "my-local-plugins"/' "$MARKETPLACE_JSON"
        # Update description
        sed -i '' 's/"description": *"iflow plugin marketplace"/"description": "Personal local plugins marketplace (development)"/' "$MARKETPLACE_JSON"
        # Reset version to dev
        sed -i '' 's/"version": *"[^"]*"/"version": "0.0.0-dev"/' "$MARKETPLACE_JSON"
        success "Restored marketplace.json to dev format"
    fi
}

#############################################
# Git operations
#############################################

commit_and_release() {
    local new_version=$1
    local tag="v$new_version"

    # Convert to public format for release
    convert_to_public_marketplace

    # Commit version changes (with public marketplace format)
    git add "$PLUGIN_JSON" "$MARKETPLACE_JSON"
    git commit -m "chore(release): v$new_version"
    success "Committed version bump"

    # Push develop (with public format temporarily)
    git push origin develop
    success "Pushed develop"

    # Merge to main
    git checkout main
    git pull origin main
    git merge develop --no-edit
    success "Merged develop into main"

    # Create and push tag
    git tag "$tag"
    git push origin main
    git push origin "$tag"
    success "Created and pushed tag $tag"

    # Return to develop and restore dev format
    git checkout develop
    convert_to_dev_marketplace
    git add "$MARKETPLACE_JSON"
    git commit -m "chore: restore dev marketplace format"
    git push origin develop
    success "Restored dev format on develop branch"
}

#############################################
# Main
#############################################

main() {
    echo "=== iflow Plugin Release Script ==="
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
        error "No releasable commits found. Use feat:, fix:, or BREAKING CHANGE: prefixes."
    fi
    echo "Bump type: $bump_type"

    # Calculate new version
    local current_version new_version
    current_version=$(get_current_version)
    new_version=$(bump_version "$current_version" "$bump_type")
    echo "Version: $current_version → $new_version"
    echo ""

    # Confirm
    read -p "Proceed with release? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warn "Release cancelled"
        exit 0
    fi

    # Update files
    update_version_in_files "$new_version"

    # Commit and release
    commit_and_release "$new_version"

    echo ""
    success "=== Released v$new_version ==="
}

main "$@"
