# Specification: Phase Context Accumulation

**Origin:** Backlog #00044 — backward transitions (rework) have zero context about prior phase decisions, causing blind rework and unnecessary re-iterations.

## Problem Statement
When backward travel occurs (reviewer sends `backward_to`), the re-entered phase has no knowledge of what prior phases decided, produced, or were told by reviewers. `backward_context` exists but is cleared after phase completion — a second backward hop loses all prior context. `phase_timing` tracks iterations and reviewer notes but not decisions or artifacts. The result: reviewers re-raise resolved issues, drafters contradict prior conclusions, and iteration counts inflate.

## Success Criteria
- [ ] `complete_phase` MCP accepts a `phase_summary` parameter and stores it in entity metadata under `phase_summaries` (append-list)
- [ ] Summary schema: `{phase, timestamp, outcome, artifacts_produced, key_decisions, reviewer_feedback_summary, rework_trigger}`
- [ ] `_project_meta_json` projects `phase_summaries` to `.meta.json`
- [ ] On backward transition, `validateAndSetup` Step 1b injects prior phase summaries as merged `## Phase Context` block
- [ ] Reviewer dispatch prompts in 4 phase command files include the same block on backward transitions
- [ ] Multiple rework cycles through the same phase accumulate entries (append, not overwrite)
- [ ] Features without summaries experience zero behavior change

## Write Ownership
- `commitAndComplete` in workflow-transitions SKILL.md is the **summary author** — the LLM executing it constructs the summary dict from its Step 3 Phase Summary output, THEN passes it to `complete_phase` MCP as a separate call after the initial completion call. Data flow: Step 2 (complete_phase without summary) → Step 3 (generate Phase Summary text) → Step 3b (NEW: construct summary dict from Step 3 output, call `update_entity` with phase_summary appended to metadata). This avoids reordering existing steps.
- `_process_complete_phase` at workflow_state_server.py:661 continues to handle completion. A new helper `_append_phase_summary` handles summary storage via `update_entity`.
- `validateAndSetup` Step 1b is the **reader/injector** — reads `.meta.json`, formats summaries into prompt context

## API Changes

### Summary storage — via update_entity after completion
No change to `complete_phase` MCP signature. Instead, `commitAndComplete` Step 3b calls `update_entity` to append the summary to `phase_summaries` in entity metadata after the phase completion call succeeds. This keeps the existing `complete_phase` contract unchanged.

```python
# commitAndComplete Step 3b (new):
# After Step 3 Phase Summary output, construct dict and append:
update_entity(
    type_id=feature_type_id,
    metadata={"phase_summaries": existing_summaries + [new_summary]}
)
```

### Entity metadata — new key
```python
# METADATA_SCHEMAS['feature'] addition (metadata.py:31-45):
"phase_summaries": list  # append-list of summary entries

# Each entry:
{
    "phase": "specify",
    "timestamp": "2026-04-02T08:00:00Z",  // ISO 8601 with UTC, matching _iso_now()
    "outcome": "Specification complete (3 iterations).",
    "artifacts_produced": ["spec.md"],
    "key_decisions": "Free-text paragraph of key choices made.",
    "reviewer_feedback_summary": "Brief summary of reviewer feedback.",
    "rework_trigger": null  # or "design reviewer flagged AC-3 gap"
}
```

### .meta.json — new field
```json
{
  "phase_summaries": [
    {"phase": "specify", "timestamp": "...", "outcome": "...", ...},
    {"phase": "design", "timestamp": "...", "outcome": "...", ...}
  ]
}
```
Projected by `_project_meta_json` (workflow_state_server.py:295-385) alongside existing `phases`, `backward_context`.

## Scope

### In Scope
- Add `phase_summary` parameter to `complete_phase` MCP tool
- Store summaries in entity metadata as append-list under `phase_summaries` key
- Project `phase_summaries` to `.meta.json` via `_project_meta_json`
- Add `phase_summaries: list` to `METADATA_SCHEMAS['feature']` in metadata.py
- Update `validateAndSetup` Step 1b to inject summaries on backward transitions
- Update `commitAndComplete` to construct and pass summary dict
- Update 4 phase command files (specify.md, design.md, create-plan.md, implement.md) to include phase summaries in reviewer dispatch prompts on backward transitions. Brainstorm command excluded — brainstorm has no reviewer dispatch prompts.
- Cap summaries at 2000 chars per entry; trim injection to last 2 per phase

### Out of Scope
- Structured DB tables for phase summaries (backlog #00051)
- Cross-feature context sharing
- Summary quality scoring or validation
- Forward-transition injection (summaries only injected on backward travel)

## Acceptance Criteria

### AC-1: complete_phase accepts and stores phase_summary
- Given `complete_phase` is called with `phase_summary='{"phase":"specify","timestamp":"...","outcome":"...",...}'`
- When the call succeeds
- Then entity metadata `phase_summaries` list contains the new entry appended
- And prior entries are preserved (not overwritten)

### AC-2: phase_summary parameter is optional
- Given `complete_phase` is called without `phase_summary` (or with null)
- When the call succeeds
- Then `phase_summaries` is unchanged (no empty entry appended)

### AC-3: _project_meta_json projects phase_summaries
- Given entity metadata contains `phase_summaries` with 2 entries
- When `_project_meta_json` generates .meta.json
- Then .meta.json contains `"phase_summaries": [{...}, {...}]`

### AC-4: validateAndSetup injects on backward transition
- Given .meta.json contains `phase_summaries` with entries for specify and design
- When `validateAndSetup("specify")` detects backward travel (the target phase is already completed, i.e., `phase_timing[target_phase]` has a `completed` timestamp in .meta.json)
- Then a `## Phase Context` markdown block is prepended to the phase prompt, containing:
  - Backward context (existing `backward_context` field, if present) labeled "Reviewer Referral"
  - Phase summaries (last 2 per phase) labeled "Prior Phase Summaries"
- Note: injection triggers on ANY re-entry into a completed phase, regardless of whether `backward_context` exists. This covers both reviewer-initiated rework and user-initiated re-runs.

### AC-5: validateAndSetup does NOT inject on forward transition
- Given .meta.json contains `phase_summaries`
- When `validateAndSetup("design")` processes a normal forward transition (specify completed, now entering design for the first time — no `completed` timestamp for design in phase_timing)
- Then no `## Phase Context` block is prepended

### AC-6: Reviewer prompts include phase context on backward transition
- Given backward travel to specify phase
- When spec-reviewer is dispatched
- Then the dispatch prompt includes `## Phase Context` section with prior summaries
- And this section appears after `## Relevant Engineering Memory` and before the review instructions

### AC-7: commitAndComplete constructs summary
- Given a phase completes with 3 iterations and reviewer notes
- When `commitAndComplete` executes
- Then it constructs a JSON summary dict with all 7 schema fields populated from its Step 3 output
- And passes it to `complete_phase` MCP as `phase_summary` parameter

### AC-8: Summary entries cap at 2000 chars
- Given `commitAndComplete` produces a summary exceeding 2000 chars when serialized
- When the summary is stored
- Then `reviewer_feedback_summary` is truncated first (to min 100 chars), then `key_decisions`, appending "..." to indicate truncation
- And the total serialized JSON entry is <=2000 chars

### AC-9: Injection trims to last 2 per phase
- Given `phase_summaries` contains 4 entries for specify (4 rework cycles)
- When injection formats the `## Phase Context` block
- Then only the 2 most recent specify entries are included (by list position — append order, not timestamp)
- And all 4 entries remain in metadata (storage is not trimmed)

### AC-12: Malformed summary handled gracefully
- Given `commitAndComplete` constructs a summary that is not valid JSON or fails to serialize
- When the `update_entity` call attempts to store it
- Then the phase completion is not affected (summary storage is best-effort)
- And a warning is logged: "Phase summary storage failed: {error}"

### AC-10: Zero behavior change without summaries
- Given a feature with no `phase_summaries` in metadata (pre-existing or new)
- When `validateAndSetup` runs (forward or backward)
- Then no `## Phase Context` block is generated
- And no errors or warnings are produced

### AC-11: METADATA_SCHEMAS updated
- Given `validate_metadata` is called on a feature entity with `phase_summaries: [...]`
- When validation runs
- Then no schema-mismatch warnings are produced for the `phase_summaries` key

## Feasibility Assessment

### Assessment
**Overall:** Confirmed
**Reasoning:** All integration points exist and are well-isolated. `_process_complete_phase` already writes structured data to metadata — adding a new field is mechanical. `_project_meta_json` already projects `backward_context` — projecting `phase_summaries` is identical pattern. `validateAndSetup` Step 1b already reads `.meta.json` and injects backward_context — adding phase_summaries to the same injection block is additive. `commitAndComplete` already produces Phase Summary text output — converting to structured dict is field mapping.

**Key Assumptions:**
- `_process_complete_phase` can accept a new parameter without breaking existing callers — Status: Verified (MCP parameters are optional with defaults)
- `commitAndComplete` has access to all summary fields at completion time — Status: Verified (SKILL.md:246-273 shows it has phase name, iterations, artifact list, reviewer notes)
- `.meta.json` projection handles arbitrary metadata keys — Status: Verified (`_project_meta_json` reads metadata dict and projects specific keys)

## Dependencies
- `workflow_state_server.py` — `_process_complete_phase` (storage), `_project_meta_json` (projection)
- `workflow-transitions/SKILL.md` — `commitAndComplete` (generation), `validateAndSetup` Step 1b (injection)
- `metadata.py` — `METADATA_SCHEMAS` (schema registration)
- 4 phase command files — `specify.md`, `design.md`, `create-plan.md`, `implement.md` (reviewer prompt injection)
