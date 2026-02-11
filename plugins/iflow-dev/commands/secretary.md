---
description: Intelligent task routing - discover agents and delegate work
argument-hint: [help|mode [manual|aware|yolo]|<request>]
---

# /iflow-dev:secretary Command

Route requests to the most appropriate specialist agent.

## Subcommand: help

If argument is `help`:

Display usage instructions:

```
Secretary Agent - Intelligent Task Routing

Usage:
  /iflow-dev:secretary help              Show this help
  /iflow-dev:secretary mode              Show current activation mode
  /iflow-dev:secretary mode <mode>       Set activation mode (manual|aware|yolo)
  /iflow-dev:secretary <request>         Route request to best agent

Modes:
  manual   - Only activates via explicit /secretary command (default)
  aware    - Injects routing hints at session start
  yolo     - Fully autonomous: runs entire workflow without pausing

Examples:
  /iflow-dev:secretary review auth for security issues
  /iflow-dev:secretary help me improve test coverage
  /iflow-dev:secretary find and fix performance problems

The secretary will:
1. Discover available agents across all plugins
2. Interpret your request (ask clarifying questions if needed)
3. Match to the best specialist agent
4. Confirm with you before delegating
5. Execute the delegation and report results
```

## Subcommand: mode

If argument is `mode` (no value):

1. Read config from `.claude/secretary.local.md`
2. If config not found: Report "Config not found. Using defaults (manual mode)."
3. If config found: Extract and display `activation_mode` value

Display format:
```
Current mode: {mode}

Available modes:
  manual - Only activates via explicit /secretary command
  aware  - Injects routing hints at session start
  yolo   - Fully autonomous: runs entire workflow without pausing
```

If argument is `mode <value>` where value is `manual`, `aware`, or `yolo`:

1. Check if `.claude/secretary.local.md` exists
2. If exists:
   - Use Edit tool to update `activation_mode` line
   - Report "Mode updated to {value}"
3. If not exists:
   - Create `.claude/` directory if needed (via Bash: mkdir -p)
   - Use Write tool to create config with specified mode:
     ```
     ---
     activation_mode: {value}
     ---
     ```
   - Report "Config created at .claude/secretary.local.md with mode: {value}"

If argument is `mode <invalid>`:

Report error:
```
Invalid mode: {invalid}

Valid modes are:
  manual - Only activates via explicit /secretary command
  aware  - Injects routing hints at session start
  yolo   - Fully autonomous: runs entire workflow without pausing
```

## Subcommand: <request>

If argument is anything other than `help` or `mode`:

This is a user request to route.

**Before dispatching**, read `.claude/secretary.local.md`. If `activation_mode: yolo`, prefix the Task prompt with `[YOLO_MODE]`:

```
# Read config
config = read(".claude/secretary.local.md")
yolo = config contains "activation_mode: yolo"

Task({
  subagent_type: "iflow-dev:secretary",
  description: "Route user request to appropriate agent",
  prompt: yolo
    ? "[YOLO_MODE] User request: {full argument string}"
    : "User request: {full argument string}"
})
```

The secretary agent will:
1. Discover available agents
2. Interpret the request (may ask clarifying questions)
3. Match to best agent and recommend
4. Get user confirmation
5. Delegate to selected agent
6. Report results

## No Arguments

If no argument provided:

Display brief usage:
```
Usage: /iflow-dev:secretary [help|mode|<request>]

Quick examples:
  /iflow-dev:secretary help
  /iflow-dev:secretary review auth module
  /iflow-dev:secretary mode aware

Run /iflow-dev:secretary help for full documentation.
```
