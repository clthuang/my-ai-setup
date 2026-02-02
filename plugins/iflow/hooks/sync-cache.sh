#!/usr/bin/env bash
# SessionStart hook: sync plugin source files to cache directory
# Ensures Claude Code always uses the latest plugin code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# Find the source project root
SOURCE_ROOT="$(detect_project_root)"
SOURCE_PLUGIN="${SOURCE_ROOT}/plugins/iflow"

# Detect installed plugin path dynamically from installed_plugins.json
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
CACHE_PLUGIN=""
if [[ -f "$INSTALLED_PLUGINS" ]]; then
    # Extract installPath for iflow-dev@my-local-plugins
    CACHE_PLUGIN=$(grep -o '"installPath": *"[^"]*iflow-dev[^"]*"' "$INSTALLED_PLUGINS" | head -1 | sed 's/"installPath": *"\([^"]*\)"/\1/')
fi

# Fallback to dev path if not installed
if [[ -z "$CACHE_PLUGIN" ]]; then
    CACHE_PLUGIN="$HOME/.claude/plugins/cache/my-local-plugins/iflow-dev/0.0.0-dev"
fi

# Only sync if source exists and this is the my-ai-setup project
if [[ -d "${SOURCE_PLUGIN}" && -f "${SOURCE_PLUGIN}/.claude-plugin/plugin.json" ]]; then
    rsync -a --delete "${SOURCE_PLUGIN}/" "${CACHE_PLUGIN}/"
fi

# Also sync marketplace.json to marketplace cache
SOURCE_MARKETPLACE="${SOURCE_ROOT}/.claude-plugin/marketplace.json"
CACHE_MARKETPLACE="$HOME/.claude/plugins/marketplaces/my-local-plugins/.claude-plugin/marketplace.json"

if [[ -f "$SOURCE_MARKETPLACE" && -d "$(dirname "$CACHE_MARKETPLACE")" ]]; then
    cp "$SOURCE_MARKETPLACE" "$CACHE_MARKETPLACE"
fi

# Output required JSON
echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
exit 0
