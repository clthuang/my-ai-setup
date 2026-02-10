---
name: decomposing
description: Orchestrates project decomposition -- decomposer + reviewer cycle, dependency graph, user approval, feature creation. Use when creating a project from a PRD or when the create-project command invokes decomposition.
---

# Project Decomposition

Decomposes a project PRD into modules and features through an AI decomposer/reviewer cycle.

## Prerequisites

Expects inputs:
- `project_dir` (string): path to `docs/projects/{id}-{slug}/`
- `prd_content` (string): full PRD markdown text
- `expected_lifetime` (string): e.g. "3-months", "6-months", "1-year", "2-years"

## Step 1: Invoke Decomposer Agent

Dispatch decomposition via Task tool:

```
Tool: Task
subagent_type: iflow-dev:project-decomposer
prompt: |
  Decompose this PRD into modules and features.

  ## PRD
  {prd_content}

  ## Constraints
  - Expected lifetime: {expected_lifetime}
  - Each feature must be a vertical slice (end-to-end value)
  - 100% coverage: every PRD requirement maps to at least one feature
  - Minimize cross-feature dependencies
  - Module boundaries should align with functional domains
  - Complexity should match expected lifetime ({shorter -> simpler})

  ## Output Format
  Return JSON:
  {
    "modules": [{"name": "...", "description": "...", "features": [{"name": "...", "description": "...", "depends_on": [], "complexity": "Low|Medium|High"}]}],
    "cross_cutting": ["..."],
    "suggested_milestones": [{"name": "...", "features": ["..."], "rationale": "..."}]
  }
```

Store the raw response as `decomposer_output`.

## Step 2: Parse JSON Response

1. Attempt `JSON.parse(decomposer_output)`.
2. If valid JSON -> store as `decomposition` and proceed to Step 3.
3. If invalid JSON -> retry **once**:
   - Re-invoke Step 1 with appended message: `"\n\nYour previous response was not valid JSON. The parse error was: {error}. Return ONLY the JSON object, no prose."`
   - Parse again. If valid -> proceed to Step 3.
4. If still invalid -> present to user:
   ```
   AskUserQuestion:
     questions: [{
       "question": "Decomposer returned invalid JSON after retry. How to proceed?",
       "header": "Parse Error",
       "options": [
         {"label": "View raw output", "description": "Display the raw decomposer response for manual inspection"},
         {"label": "Retry from scratch", "description": "Re-run decomposition with a fresh prompt"},
         {"label": "Cancel", "description": "Abort decomposition"}
       ],
       "multiSelect": false
     }]
   ```
   - "View raw output" -> display raw text, then ask user to provide corrected JSON or instructions
   - "Retry from scratch" -> go to Step 1
   - "Cancel" -> abort, return to caller

## Step 3: Invoke Reviewer Agent

Set `iteration = 1`. Dispatch review via Task tool:

```
Tool: Task
subagent_type: iflow-dev:project-decomposition-reviewer
prompt: |
  Review this decomposition for quality.

  ## Original PRD
  {prd_content}

  ## Decomposition
  {decomposition_json}

  ## Project Context
  Expected lifetime: {expected_lifetime}

  ## Evaluation Criteria
  1. Organisational cohesion
  2. Engineering best practices (no circular deps, no god-modules)
  3. Goal alignment (serves PRD, no premature generalisation)
  4. Lifetime-appropriate complexity
  5. 100% coverage

  ## Iteration
  This is iteration {iteration} of 3.

  Return JSON:
  {"approved": bool, "issues": [{"criterion": "...", "description": "...", "severity": "blocker|warning"}], "criteria_evaluated": ["..."]}
```

Parse reviewer response as JSON. If non-JSON, treat as `approved: false` with a single blocker: "Reviewer returned invalid response".

## Step 4: Review-Fix Cycle

Max 3 iterations. After Step 3 returns `review_result`:

1. **If `review_result.approved == true`** -> proceed to Step 5 (defined in later task).

2. **If `review_result.approved == false` AND `iteration < 3`:**
   - Increment `iteration`.
   - Re-invoke decomposer (Step 1 pattern) with revision prompt:
     ```
     Tool: Task
     subagent_type: iflow-dev:project-decomposer
     prompt: |
       Revise this decomposition to address reviewer issues.

       ## PRD
       {prd_content}

       ## Previous Decomposition (to revise)
       {decomposition_json}

       ## Reviewer Issues
       {review_result.issues formatted as list}

       ## Constraints
       - Expected lifetime: {expected_lifetime}
       - Address all blocker issues
       - Preserve structure that was not flagged
       - Return the complete revised JSON (same schema)
     ```
   - Parse response (apply Step 2 logic).
   - Store as new `decomposition`.
   - Re-invoke reviewer (Step 3) with new decomposition and incremented iteration.

3. **If `review_result.approved == false` AND `iteration == 3`:**
   - Log remaining issues as warnings.
   - Proceed to Step 5 with current decomposition. Note: "Decomposition approved with unresolved warnings after 3 iterations."

<!-- Steps 5-11 added by tasks 3.2 and 3.3 -->
