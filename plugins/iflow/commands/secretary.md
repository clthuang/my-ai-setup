---
description: Intelligent task routing - discover agents and delegate work
argument-hint: [help|mode [manual|aware|yolo]|orchestrate <desc>|<request>]
---

# /iflow:secretary Command

Route requests to the most appropriate specialist agent.

## Subcommand Routing

Parse the first word of the argument:
- `help` → Help subcommand
- `mode` → Mode subcommand
- `orchestrate` or `continue` → Orchestrate subcommand
- anything else → Request handler (dispatches to iflow:secretary agent)
- no argument → Brief usage

## Subcommand: help

If argument is `help`:

Display usage instructions:

```
Secretary Agent - Intelligent Task Routing

Usage:
  /iflow:secretary help              Show this help
  /iflow:secretary mode              Show current activation mode
  /iflow:secretary mode <mode>       Set activation mode (manual|aware|yolo)
  /iflow:secretary orchestrate <desc> Run full workflow autonomously (YOLO only)
  /iflow:secretary <request>         Route request to best agent

Modes:
  manual   - Only activates via explicit /secretary command (default)
  aware    - Injects routing hints at session start
  yolo     - Fully autonomous: runs entire workflow without pausing

Orchestration (YOLO mode only):
  /iflow:secretary orchestrate build a login system
  /iflow:secretary continue          Resume from last completed phase

Examples:
  /iflow:secretary review auth for security issues
  /iflow:secretary help me improve test coverage
  /iflow:secretary find and fix performance problems

The secretary will:
1. Discover available agents across all plugins
2. Interpret your request (ask clarifying questions if needed)
3. Validate routing via independent reviewer
4. Match to the best specialist agent with mode recommendation
5. Confirm with you before delegating
6. Execute the delegation and report results
```

## Subcommand: mode

If argument is `mode` (no value):

1. Read config from `.claude/iflow.local.md`
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

1. Check if `.claude/iflow.local.md` exists
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
   - Report "Config created at .claude/iflow.local.md with mode: {value}"

If argument is `mode <invalid>`:

Report error:
```
Invalid mode: {invalid}

Valid modes are:
  manual - Only activates via explicit /secretary command
  aware  - Injects routing hints at session start
  yolo   - Fully autonomous: runs entire workflow without pausing
```

## Subcommand: orchestrate

If argument starts with `orchestrate` or `continue`:

### Prerequisites

1. Read `.claude/iflow.local.md`
2. Extract `activation_mode`
3. If mode is NOT `yolo`:
   ```
   Orchestration requires YOLO mode.

   Current mode: {mode}
   Set YOLO mode first: /iflow:secretary mode yolo
   ```
   Stop here.

### Detect Workflow State

1. Glob `docs/features/*/.meta.json`
2. Read each file, look for `"status": "active"`
3. If active feature found:
   - Extract `lastCompletedPhase` from .meta.json
   - Report: "Active feature: {id}-{slug}, last phase: {lastCompletedPhase}"
4. If no active feature AND description provided after "orchestrate":
   - This is a new feature request, start from brainstorm
5. If no active feature AND no description (bare `orchestrate` or `continue`):
   ```
   No active feature found and no description provided.

   Usage:
     /iflow:secretary orchestrate <description>  Start new feature
     /iflow:secretary continue                   Resume active feature
   ```
   Stop here.

### Determine Next Command

| lastCompletedPhase | Next Command |
|---|---|
| (no active feature) | iflow:brainstorm |
| null (feature exists, no phases) | iflow:specify |
| brainstorm | iflow:specify |
| specify | iflow:design |
| design | iflow:create-plan |
| create-plan | iflow:create-tasks |
| create-tasks | iflow:implement |
| implement | iflow:finish |
| finish | Already complete — report "Feature already completed." and stop |

### Execute in Main Session

Invoke the next command via Skill (NOT Task) so it runs in the main session and the user sees all output:

```
Skill({
  skill: "iflow:{next-command}",
  args: "[YOLO_MODE] {description or feature context}"
})
```

The existing command chaining and YOLO overrides handle everything from here. Each phase:
- Auto-selects at AskUserQuestion prompts (YOLO overrides in workflow-transitions)
- Runs full executor-reviewer cycles (all reviewer agents still execute)
- Auto-invokes the next command at completion

### Hard Stops

The chain breaks and reports to user when:
- **Circuit breaker**: 5 review iterations without approval in implementation
- **Git merge conflict**: Cannot auto-resolve in /finish
- **Hard prerequisite failure**: Missing spec.md or plan.md
- **Pre-merge validation failure**: 3 fix attempts exhausted

These are handled by the individual commands. The orchestrator does NOT need to catch them — the Skill invocation naturally surfaces them.

## Subcommand: <request>

If argument is anything other than `help`, `mode`, `orchestrate`, or `continue`:

> **CRITICAL — ROUTING CONSTRAINT**
>
> You are a **dispatcher**, not an executor. Your ONLY job is to send this request to the `iflow:secretary` agent via the Task tool.
>
> **FORBIDDEN** before dispatching:
> - Using Read, Glob, Grep to explore the codebase
> - Using Edit, Write, Bash to make changes
> - Answering the user's request directly
> - Summarizing what you "would" do
> - Asking the user clarifying questions about their request
>
> The secretary **agent** handles discovery, interpretation, and delegation — not you.

**Steps:**

1. **Read config** — Read `.claude/iflow.local.md`. Extract `activation_mode`. If `yolo`, set YOLO prefix.
2. **Dispatch** — Immediately call Task:
   ```
   Task({
     subagent_type: "iflow:secretary",
     description: "Route user request to appropriate agent",
     prompt: yolo
       ? "[YOLO_MODE] User request: {full argument string}"
       : "User request: {full argument string}"
   })
   ```
3. **Present results** — If the agent returned `workflow_signal: orchestrate`, redirect to the orchestrate subcommand logic above. Otherwise, present the agent's results directly.

## No Arguments

If no argument provided:

Display brief usage:
```
Usage: /iflow:secretary [help|mode|orchestrate|<request>]

Quick examples:
  /iflow:secretary help
  /iflow:secretary review auth module
  /iflow:secretary mode yolo
  /iflow:secretary orchestrate build a login system

Run /iflow:secretary help for full documentation.
```
