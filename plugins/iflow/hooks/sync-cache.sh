#!/usr/bin/env bash
# SessionStart hook: sync plugin source files to cache directory
# Ensures Claude Code always uses the latest plugin code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# Find the source project root
SOURCE_ROOT="$(detect_project_root)"
SOURCE_PLUGIN="${SOURCE_ROOT}/plugins/iflow"
# Plugin name is iflow-dev on develop branch (local development)
CACHE_PLUGIN="$HOME/.claude/plugins/cache/my-local-plugins/iflow-dev/0.0.0-dev"

# Only sync if source exists and this is the my-ai-setup project
if [[ -d "${SOURCE_PLUGIN}" && -f "${SOURCE_PLUGIN}/.claude-plugin/plugin.json" ]]; then
    rsync -a --delete "${SOURCE_PLUGIN}/" "${CACHE_PLUGIN}/"
fi

# Output required JSON
echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
exit 0
