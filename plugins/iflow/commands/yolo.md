---
description: Toggle YOLO autonomous mode on or off
argument-hint: "[on|off]"
---

<yolo-command>

You are the YOLO mode toggle. Parse the argument and manage YOLO state.

## Input

Argument: `$ARGUMENTS`

## Config File

Path: `{project_root}/.claude/iflow-dev.local.md`

If the file doesn't exist, create it with this exact content:
```
---
yolo_mode: false
yolo_max_stop_blocks: 50
---
```

## State File

Path: `{project_root}/.claude/.yolo-hook-state`

## Logic

### If argument is "on":

1. Read `{project_root}/.claude/iflow-dev.local.md`. Create from template if missing.
2. Set `yolo_mode: true` in the YAML frontmatter (use Edit tool).
3. Reset the state file by writing this exact content to `{project_root}/.claude/.yolo-hook-state`:
```
stop_count=0
last_phase=null
```
4. Output:
```
YOLO mode enabled. Hooks will enforce autonomous execution.
Reviews must genuinely pass before phase transitions.
Use /iflow:yolo off or press Escape to return to interactive mode.
```

### If argument is "off":

1. Read `{project_root}/.claude/iflow-dev.local.md`. Create from template if missing.
2. Set `yolo_mode: false` in the YAML frontmatter (use Edit tool).
3. Output:
```
YOLO mode disabled. Returning to interactive mode.
AskUserQuestions will be shown. Session can stop between phases.
```

### If no argument (status check):

1. Read `yolo_mode` from `{project_root}/.claude/iflow-dev.local.md` (default: false).
2. Read `stop_count` from `{project_root}/.claude/.yolo-hook-state` (default: 0).
3. Read `yolo_max_stop_blocks` from config (default: 50).
4. Find active feature: scan `docs/features/*/.meta.json` for `status: "active"`.
5. Output:
```
YOLO mode: {on/off}
Active feature: {id}-{slug} (last completed: {phase}) | none
Stop blocks used: {count}/{max}
```

## Important

- Use the Edit tool to modify YAML frontmatter (never bash/sed for config).
- The state file uses simple key=value format -- Write tool is fine for resets.
- Changes take effect immediately -- both hooks read config fresh on every invocation.

</yolo-command>
