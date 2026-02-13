---
name: retrospecting
description: Runs data-driven AORTA retrospective using retro-facilitator agent with full intermediate context. Use when the user says 'run retro', 'capture learnings', 'reflect on feature', or 'update knowledge bank'.
---

# Retrospective

Data-driven AORTA retrospective using retro-facilitator agent.

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context

## Process

### Step 1: Assemble Context Bundle

Read and collect all intermediate data:

**a. Phase Metrics** — Read `.meta.json` and extract:
- Phase timings: all `phases.*.started` / `phases.*.completed` timestamps
- Iteration counts: `phases.*.iterations`
- Reviewer notes: `phases.*.reviewerNotes`
- Mode: Standard or Full

**b. Review History** — Read `.review-history.md`:
- If file exists: capture full content
- If file doesn't exist: note "No review history available"

**c. Implementation Log** — Read `implementation-log.md`:
- If file exists: capture full content
- If file doesn't exist: note "No implementation log available"

**d. Git Summary** — Run via Bash:
```bash
git log --oneline develop..HEAD | wc -l
```
```bash
git diff --stat develop..HEAD
```

**e. Artifact Stats** — Read and count lines for each artifact:
- `spec.md`, `design.md`, `plan.md`, `tasks.md`
- Note which artifacts exist vs missing

**f. AORTA Framework** — Read `references/aorta-framework.md` from this skill's directory.

### Step 2: Dispatch retro-facilitator

```
Task tool call:
  description: "Run AORTA retrospective"
  subagent_type: iflow-dev:retro-facilitator
  prompt: |
    Run AORTA retrospective for feature {id}-{slug}.

    ## Context Bundle

    ### Phase Metrics
    {assembled .meta.json extract — phase timings, iterations, reviewer notes, mode}

    ### Review History
    {.review-history.md content, or "No review history available"}

    ### Implementation Log
    {implementation-log.md content, or "No implementation log available"}

    ### Git Summary
    Commits: {commit count}
    Files changed:
    {git diff --stat output}

    ### Artifact Stats
    - spec.md: {line count or "missing"}
    - design.md: {line count or "missing"}
    - plan.md: {line count or "missing"}
    - tasks.md: {line count or "missing"}

    ### AORTA Framework
    {content of references/aorta-framework.md}

    Return structured JSON with observe, review, tune, act sections
    plus retro_md content.
```

**Fallback:** If retro-facilitator agent fails, fall back to investigation-agent:

```
Task tool call:
  description: "Gather feature learnings"
  subagent_type: iflow-dev:investigation-agent
  prompt: |
    Gather retrospective data for feature {id}-{slug}.

    Read:
    - Feature folder contents (docs/features/{id}-{slug}/)
    - Git log for this branch
    - .review-history.md if exists

    Identify:
    - What went well
    - What could improve
    - Patterns worth documenting
    - Anti-patterns to avoid

    Return structured findings as JSON:
    {
      "what_went_well": [...],
      "what_could_improve": [...],
      "patterns": [...],
      "anti_patterns": [...],
      "heuristics": []
    }
```

If using fallback, generate retro.md in the legacy format (What Went Well / What Could Improve / Learnings Captured).

### Step 3: Write retro.md

Write `docs/features/{id}-{slug}/retro.md` using the `retro_md` field from the retro-facilitator agent response.

The retro_md follows the AORTA format:

```markdown
# Retrospective: {Feature Name}

## AORTA Analysis

### Observe (Quantitative Metrics)
| Phase | Duration | Iterations | Notes |
|-------|----------|------------|-------|
| ... | ... | ... | ... |

{Quantitative summary}

### Review (Qualitative Observations)
1. **{Observation}** — {evidence}
2. ...

### Tune (Process Recommendations)
1. **{Recommendation}** (Confidence: {level})
   - Signal: {what was observed}
2. ...

### Act (Knowledge Bank Updates)
**Patterns added:**
- {pattern text} (from: {provenance})

**Anti-patterns added:**
- {anti-pattern text} (from: {provenance})

**Heuristics added:**
- {heuristic text} (from: {provenance})

## Raw Data
- Feature: {id}-{slug}
- Mode: {mode}
- Branch lifetime: {days or N/A}
- Total review iterations: {count}
```

### Step 4: Update Knowledge Bank

From the `act` section of the agent response, append entries to knowledge bank files:

1. For each pattern in `act.patterns`:
   - Append to `docs/knowledge-bank/patterns.md`
2. For each anti-pattern in `act.anti_patterns`:
   - Append to `docs/knowledge-bank/anti-patterns.md`
3. For each heuristic in `act.heuristics`:
   - Append to `docs/knowledge-bank/heuristics.md`

Each entry format:
```markdown
### {Type}: {Name}
{Text}
- Observed in: {provenance}      ← use "Source:" instead for heuristics.md
- Confidence: {confidence}
- Last observed: Feature #{NNN}
- Observation count: 1
```

If a knowledge-bank file doesn't exist, create it with a header:
```markdown
# {Patterns|Anti-Patterns|Heuristics}

Accumulated learnings from feature retrospectives.
```

### Step 4b: Validate Knowledge Bank (Pre-Existing Entries)

Performed by the orchestrating agent inline (not a sub-agent dispatch). Only validates `anti-patterns.md` and `heuristics.md` (not `patterns.md`).

**a. Read all entries** from `docs/knowledge-bank/anti-patterns.md` and `docs/knowledge-bank/heuristics.md` (~15 entries total).

**b. Identify pre-existing entries** — exclude entries just added in Step 4 by comparing entry names against the retro-facilitator's `act.anti_patterns` and `act.heuristics` output. Only pre-existing entries proceed to validation.

**c. Determine relevance** for each pre-existing entry:
- **RELEVANT** if the entry's domain (file patterns, coding practices, workflow steps) overlaps with this feature's git diff files, implementation-log decisions/deviations, or review-history issues (all already in context from Step 1)
- **NOT RELEVANT** if the entry's domain has no overlap — skip, no update needed

**d. Evaluate relevant entries** against this feature's experience:

| Verdict | Condition | Action |
|---------|-----------|--------|
| CONFIRMED | Feature experience aligns with entry's guidance | Update `Last observed: Feature #{id}`, increment `Observation count` |
| CONTRADICTED | Feature experience contradicts the entry | Append `- Challenged: Feature #{id} — {specific contradiction}` to the entry |

**e. Staleness check** (mechanical, not LLM-judgment):

1. For each pre-existing entry, extract the feature number NNN from `Last observed: Feature #{NNN}`
2. Glob `docs/features/` directories, extract numeric prefix (pattern: `/^(\d+)-/`), count directories with numeric ID > NNN
3. If count >= 10: flag entry as STALE
4. Surface all stale entries to user via AskUserQuestion:
   ```
   AskUserQuestion:
     questions: [{
       "question": "The following entries haven't been observed in 10+ features:\n{list with entry names and last-observed feature numbers}\n\nFor each entry, choose an action.",
       "header": "Stale Knowledge Bank Entries",
       "options": [
         {"label": "Keep", "description": "Remove stale marker, update Last observed to current feature"},
         {"label": "Update", "description": "Provide new text, modify in-place, reset Observation count to 1"},
         {"label": "Retire", "description": "Delete entry from file, note in retro.md"}
       ],
       "multiSelect": false
     }]
   ```
5. Apply user's choice per entry:
   - **Keep**: Remove stale marker, update `Last observed` to current feature, `Observation count` unchanged
   - **Update**: User provides new text, modify entry in-place, update `Last observed`, reset `Observation count` to 1
   - **Retire**: Delete entry from file, append to `retro.md`: `Retired: {entry name} — {user's reason}`

### Step 5: Commit

```bash
git add docs/features/{id}-{slug}/retro.md docs/knowledge-bank/
git commit -m "docs: AORTA retrospective for feature {id}-{slug}"
git push
```

## Graceful Degradation

| Condition | Behavior |
|-----------|----------|
| `.review-history.md` missing | Agent runs with metrics-only (Observe works, Review limited) |
| `.meta.json` has no phase data | Agent notes "insufficient data", produces minimal retro |
| retro-facilitator agent fails | Fall back to investigation-agent (Step 2 fallback) |
| No git data available | Omit git summary from context bundle |

## Output

```
Retrospective complete (AORTA framework).
Updated: {list of knowledge-bank files updated}
Saved to retro.md.
```

## Automatic Execution

This skill runs automatically during `/iflow-dev:finish`:
- No permission prompt required
- Findings drive knowledge bank updates
- User sees summary of learnings captured
