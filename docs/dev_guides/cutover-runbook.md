# v1→v2 Cutover Runbook (backlog #085)

The cutover is **manual and deliberate** — it is never run by an agent session, because
the operator must first stop every writer *including their own session's MCP servers*.
Rehearsed green end-to-end on a live-DB copy 2026-07-25 (this document's commands are the
rehearsal's commands; results at the bottom).

Tool: `plugins/pd/hooks/lib/entity_registry/rebuild_tool.py` (feature 132). Defaults
target the LIVE paths — every rehearsal invocation must override `--db`,
`--staging-path`, `--report-dir`.

## 0. Rehearse on a copy (repeat any time; zero live risk)

```bash
SCRATCH=$(mktemp -d)
sqlite3 "file:$HOME/.claude/pd/entities/entities.db?mode=ro" ".backup '$SCRATCH/copy.db'"

# raw copy must ABORT on the pre-import vocab diff (fail-closed proof):
PYTHONPATH=plugins/pd/hooks/lib plugins/pd/.venv/bin/python -m entity_registry.rebuild_tool \
  --db "$SCRATCH/copy.db" --staging-path "$SCRATCH/s1.db" --report-dir "$SCRATCH"

sqlite3 "$SCRATCH/copy.db" < scripts/dev/cutover-prepass.sql
sqlite3 "$SCRATCH/copy.db" "SELECT COUNT(*) FROM phase_events WHERE phase='create-tasks' OR (length(phase)=1 AND event_type='skipped');"   # expect 0
sqlite3 "$SCRATCH/copy.db" "SELECT action, COUNT(*) FROM cutover_prepass_record GROUP BY action;"                                          # expect 54 remap / 73 delete (as of 2026-07-25)

# cleaned copy must COMPLETE; run twice — checksums must be identical (deterministic replay):
PYTHONPATH=plugins/pd/hooks/lib plugins/pd/.venv/bin/python -m entity_registry.rebuild_tool \
  --db "$SCRATCH/copy.db" --staging-path "$SCRATCH/s2.db" --report-dir "$SCRATCH"
```

Green bar: report shows per-kind×workspace `new == old` (552 total at rehearsal), the
tolerated anomaly classes only (`empty_id_normalized`, `orphan_phase_event`,
`orphan_workflow_phase`), and a checksum stable across runs.

## 1. Stop ALL writers (the step the tool cannot enforce)

1. Close every Claude Code session using this machine's pd plugin — including the one
   you might be reading this in. Run the cutover from a plain terminal.
2. Kill stale MCP/agent processes and verify nothing holds the DB:
   ```bash
   lsof +D ~/.claude/pd | grep -E 'entities\.db' || echo "no holders"
   ps -axww | grep -E 'entity_server|workflow_state_server' | grep -v grep
   ```
   Both must come back empty. Lane A (2026-07-16) observed 4+ live MCP PIDs with the WAL
   actively growing — the swap's checkpoint+rename must not race writers.

## 2. Backup, clean, verify

```bash
cp ~/.claude/pd/entities/entities.db ~/.claude/pd/entities/entities.db.pre-cutover-$(date +%Y%m%d)
sqlite3 ~/.claude/pd/entities/entities.db < scripts/dev/cutover-prepass.sql
# then the two verification queries from step 0 (expect 0 residual; 54/73 records)
```

## 3. Dry backfill against live (no swap), review the report

```bash
PYTHONPATH=plugins/pd/hooks/lib plugins/pd/.venv/bin/python -m entity_registry.rebuild_tool
# defaults: --db live, report to ~/.claude/pd/migrations/
```
Review: parity totals equal; anomaly lists small and explained (rehearsal baseline:
2 empty-id, 13 orphan phase_events, 3 orphan workflow_phases). Delete the staging file
the dry run leaves beside the live DB before step 4 (the tool refuses to overwrite it).

## 4. The swap

```bash
PYTHONPATH=plugins/pd/hooks/lib plugins/pd/.venv/bin/python -m entity_registry.rebuild_tool \
  --swap --summary-path docs/features/132-backfill-rebuild-tool/rebuild-report-summary.md
```
Effects: old file archived read-only at `~/.claude/pd/entities/entities.db.v1-readonly`;
staging promoted in its place; dated marker written to
`~/.claude/pd/migrations/v2-cutover.json`.

## 5. Post-cutover window

- Start a fresh session; MCP servers reconnect against the v2 file.
- `/pd:doctor` — the `check_v2_cutover_window` marker check goes live (fresh/expired
  states); watch it through the escape-hatch window (133 retro, Act 5).
- Commit the regenerated `rebuild-report-summary.md` (see its placeholder header).
- Backlog follow-through now unblocked: #060 (backlog writes → migrate manual register
  into the DB), #081/#082/#084 v1-retirement decisions.

**Rollback:** stop writers again, remove the promoted file, restore
`entities.db.v1-readonly` (rename back, `chmod +w`), delete the marker, restart sessions.

## Review items noted at rehearsal (not blockers)

- `workspaces` cardinality 2,185 (Jul 16) → 2,329 (Jul 25) for 7 logical workspaces —
  ~16 rows/day still minted by an m11-era mapping writer; investigate the writer before
  v1 retirement.
- Orphan phase_events drifted 11 → 13 over the same window (2 new orphans; tolerated
  class, but the writer is live).

## Rehearsal record — 2026-07-25

Raw copy aborted exactly on the documented inventory (`create-tasks` + 23 corruption
chars). After `cutover-prepass.sql`: 0 residual dirty rows; records 54 remap + 73 delete
= the 127-row inventory. Two clean runs: parity 552→552 exact per kind×workspace;
checksums byte-identical (`sha256:ab442648d7b5…`); uuid_remap_count 552 both runs.
