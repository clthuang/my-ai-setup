#!/bin/bash
# Bootstrap and run the MCP memory server.
# Resolution order: existing venv → system python3 → auto-bootstrap venv.
#
# Called by Claude Code via plugin.json mcpServers — do NOT write to stdout
# (would corrupt MCP stdio protocol). All diagnostics go to stderr.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PLUGIN_DIR/.venv"
SERVER_SCRIPT="$SCRIPT_DIR/memory_server.py"

export PYTHONPATH="$PLUGIN_DIR/hooks/lib${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONUNBUFFERED=1

# Fast path: existing venv
if [[ -x "$VENV_DIR/bin/python" ]]; then
    exec "$VENV_DIR/bin/python" "$SERVER_SCRIPT"
fi

# System python3 with required deps
if python3 -c "import mcp.server.fastmcp; import numpy; import dotenv" 2>/dev/null; then
    exec python3 "$SERVER_SCRIPT"
fi

# Bootstrap: create venv and install core deps (one-time)
echo "memory-server: bootstrapping venv at $VENV_DIR..." >&2
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install -q "mcp>=1.0,<2" "numpy>=1.24,<3" "python-dotenv>=1.0,<2" >&2
exec "$VENV_DIR/bin/python" "$SERVER_SCRIPT"
