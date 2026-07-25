-- cutover-prepass.sql — backlog #085 cleaning pre-pass for the v1→v2 cutover.
-- Run against the database the rebuild tool will read (rehearse on a COPY first;
-- see docs/dev_guides/cutover-runbook.md). One transaction; every mutated row is
-- copied into cutover_prepass_record before it is touched (delete-with-record).
--
-- Targets (from the tool's own pre-import vocab diff):
--   (a) phase='create-tasks' rows (retired 7-phase-era name) → remapped to
--       'create-plan', the phase it was merged into. Append-only event history
--       tolerates the resulting coexistence with native create-plan rows.
--   (b) one-character phase rows on event_type='skipped' (#086 char-explosion,
--       writer guard-fixed at 132; these are the historical residue) → deleted.
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS cutover_prepass_record (
  action      TEXT NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  id INTEGER, type_id TEXT, project_id TEXT, phase TEXT, event_type TEXT,
  timestamp TEXT, iterations INTEGER, reviewer_notes TEXT,
  backward_reason TEXT, backward_target TEXT, source TEXT, created_at TEXT
);

INSERT INTO cutover_prepass_record
  (action,id,type_id,project_id,phase,event_type,timestamp,iterations,
   reviewer_notes,backward_reason,backward_target,source,created_at)
SELECT 'remap-create-tasks',id,type_id,project_id,phase,event_type,timestamp,
       iterations,reviewer_notes,backward_reason,backward_target,source,created_at
FROM phase_events WHERE phase='create-tasks';

UPDATE phase_events SET phase='create-plan' WHERE phase='create-tasks';

INSERT INTO cutover_prepass_record
  (action,id,type_id,project_id,phase,event_type,timestamp,iterations,
   reviewer_notes,backward_reason,backward_target,source,created_at)
SELECT 'delete-char-row',id,type_id,project_id,phase,event_type,timestamp,
       iterations,reviewer_notes,backward_reason,backward_target,source,created_at
FROM phase_events WHERE length(phase)=1 AND event_type='skipped';

DELETE FROM phase_events WHERE length(phase)=1 AND event_type='skipped';

COMMIT;

-- Verification (all three must hold before running the rebuild tool):
--   1. residual dirty rows = 0:
--        SELECT COUNT(*) FROM phase_events
--        WHERE phase='create-tasks' OR (length(phase)=1 AND event_type='skipped');
--   2. record counts match the vocab diff's inventory:
--        SELECT action, COUNT(*) FROM cutover_prepass_record GROUP BY action;
--   3. no other out-of-vocab phase values remain — the rebuild tool's own
--      pre-import vocab diff re-checks this fail-closed on its next run.
