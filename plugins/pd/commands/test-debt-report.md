---
description: Aggregate deferred test debt across features and the backlog
---

# /pd:test-debt-report

Read-only aggregator. Prints one markdown table of deferred test debt, sorted by open count. No writes, no commit.

**Steps:**
1. Resolve the script: glob `~/.claude/plugins/cache/*/pd*/*/scripts/test_debt_report.py`, else `plugins/pd/scripts/test_debt_report.py` (Fallback — dev workspace).
2. Run `python3 ${script_path} --features-dir {pd_artifacts_root}/features --backlog-path {pd_artifacts_root}/backlog.md`. Its sources are historical per-feature `.qa-gate.json` MED/LOW findings (the rebuilt flow no longer mints these; new debt arrives as backlog rows) plus active testability-tagged backlog rows.
3. Print the script's stdout unchanged; surface stderr on non-zero exit.

**See also:** `/pd:cleanup-backlog` archives closed backlog sections.
