# Baseline Promptimize Scores

> **Note:** T01 and T11 require `claude -p` (headless) or interactive promptimize, which cannot
> run inside a nested Claude Code session. Scores below are to be populated in a fresh CC session.
> Run `bash plugins/iflow/scripts/batch-promptimize.sh` from project root (outside CC session).

## Pre-Refactor Baseline (to be collected)

| File | Score | Status |
|------|-------|--------|
| plugins/iflow/agents/design-reviewer.md | — | Pending (requires fresh session) |
| plugins/iflow/commands/secretary.md | — | Pending (requires fresh session) |
| plugins/iflow/skills/brainstorming/SKILL.md | — | Pending (requires fresh session) |
| plugins/iflow/commands/review-ds-code.md | — | Pending (requires fresh session) |
| plugins/iflow/commands/review-ds-analysis.md | — | Pending (requires fresh session) |

## Instructions for Manual Collection

```bash
# From a fresh terminal (not inside a CC session):
bash plugins/iflow/scripts/batch-promptimize.sh 2>&1 | grep -E "PASS|FAIL|ERROR"
```

Or run /iflow:promptimize on each file interactively in a new CC session.
