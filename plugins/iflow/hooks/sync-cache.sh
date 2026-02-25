#!/usr/bin/env bash
# SessionStart hook: sync plugin source files to cache directory
# Ensures Claude Code always uses the latest plugin code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
install_err_trap

# Find the source project root
SOURCE_ROOT="$(detect_project_root)"
SOURCE_PLUGIN_DEV="${SOURCE_ROOT}/plugins/iflow-dev"
SOURCE_PLUGIN_PROD="${SOURCE_ROOT}/plugins/iflow"

# Detect installed plugin paths dynamically from installed_plugins.json
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
CACHE_PLUGIN_DEV=""
CACHE_PLUGIN_PROD=""

if [[ -f "$INSTALLED_PLUGINS" ]]; then
    # Extract installPath for iflow-dev@my-local-plugins
    CACHE_PLUGIN_DEV=$(grep -o '"installPath": *"[^"]*iflow-dev[^"]*"' "$INSTALLED_PLUGINS" 2>/dev/null | head -1 | sed 's/"installPath": *"\([^"]*\)"/\1/' || true)
    # Extract installPath for iflow@my-local-plugins (may not be installed)
    CACHE_PLUGIN_PROD=$(grep -o '"installPath": *"[^"]*my-local-plugins/iflow/[^"]*"' "$INSTALLED_PLUGINS" 2>/dev/null | head -1 | sed 's/"installPath": *"\([^"]*\)"/\1/' || true)
fi

# Exit gracefully if iflow-dev not found in installed_plugins.json
if [[ -z "$CACHE_PLUGIN_DEV" ]]; then
    echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
    exit 0
fi

# Sync iflow-dev (primary development plugin)
if [[ -d "${SOURCE_PLUGIN_DEV}" && -f "${SOURCE_PLUGIN_DEV}/.claude-plugin/plugin.json" ]]; then
    rsync -a --delete "${SOURCE_PLUGIN_DEV}/" "${CACHE_PLUGIN_DEV}/" 2>/dev/null || true
fi

# Sync iflow (production plugin) if installed in cache
if [[ -n "$CACHE_PLUGIN_PROD" && -d "$CACHE_PLUGIN_PROD" ]]; then
    if [[ -d "${SOURCE_PLUGIN_PROD}" && -f "${SOURCE_PLUGIN_PROD}/.claude-plugin/plugin.json" ]]; then
        rsync -a --delete "${SOURCE_PLUGIN_PROD}/" "${CACHE_PLUGIN_PROD}/" 2>/dev/null || true
    fi
fi

# Also sync marketplace.json to marketplace cache
SOURCE_MARKETPLACE="${SOURCE_ROOT}/.claude-plugin/marketplace.json"
CACHE_MARKETPLACE="$HOME/.claude/plugins/marketplaces/my-local-plugins/.claude-plugin/marketplace.json"

if [[ -f "$SOURCE_MARKETPLACE" && -d "$(dirname "$CACHE_MARKETPLACE")" ]]; then
    cp "$SOURCE_MARKETPLACE" "$CACHE_MARKETPLACE" 2>/dev/null || true
fi

# Output required JSON
echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
exit 0
