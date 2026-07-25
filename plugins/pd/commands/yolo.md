---
description: Turn YOLO autonomous mode on or off
argument-hint: "[on|off]"
---

# /pd:yolo

Flips the `[YOLO_MODE]` flag that `yolo-guard.sh` and `yolo-stop.sh` enforce. The behaviour it selects — auto-select recommended options, propagate the flag into every dispatch, and the safety hard-stops that override it in every mode — is the global YOLO rule in the workflow-transitions skill. Not restated here.

**Steps:**
1. `on` or `off` → set `yolo_mode` in `{project_root}/.claude/pd.local.md` with the Edit tool (never bash or sed). Create the file with `yolo_mode: false` if absent.
2. `on` also resets `{project_root}/.claude/.yolo-hook-state` to `stop_count=0`, `last_phase=null`, `yolo_paused=false`, `yolo_paused_at=0`.
3. No argument → report `yolo_mode`, `stop_count` against `yolo_max_stop_blocks`, and pause state, read from those two files.

**Constraints:** both files are read fresh on every hook invocation, so a toggle takes effect immediately; the `yolo_usage_*` keys keep their hook-side defaults unless the user sets them.
