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

1. **If `review_result.approved == true`** -> proceed to Step 5.

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

## Step 5: Name-to-ID-Slug Mapping

1. Scan `docs/features/` for all `{NNN}-*` directories. Extract numeric prefixes, find the highest `NNN`. If none exist, start at 0.
2. Flatten all features across all modules from `decomposition` into a single ordered list (preserve module order, then feature order within module).
3. Assign sequential IDs starting from `NNN + 1`.
4. Derive slug from each feature name:
   - Lowercase the name
   - Replace spaces and special characters with hyphens
   - Collapse consecutive hyphens
   - Truncate to 30 characters
   - Trim trailing hyphens
5. Build mapping table: `{ "Human Readable Name" -> "{id}-{slug}" }` for all features.
6. Remap every `depends_on` entry in `decomposition` from human-readable names to their `{id}-{slug}` equivalents using the mapping table.
7. Remap `suggested_milestones[].features` entries the same way.

Store the updated decomposition as `mapped_decomposition` and the mapping table as `name_to_id_slug`.

## Step 6: Cycle Detection

Reason through the dependency graph to detect cycles. Do NOT write executable code -- perform this as LLM analysis:

1. Build an adjacency list from `depends_on` arrays in `mapped_decomposition`. Each feature's `{id}-{slug}` maps to the list of `{id}-{slug}` values it depends on.
2. Track three states per node: **unvisited**, **in-progress**, **visited**.
3. For each unvisited node, walk depth-first through its dependencies:
   - Mark current node **in-progress**.
   - Recurse into each dependency.
   - If a dependency is **in-progress**, a cycle exists -- trace the path back to identify the full cycle.
   - After all dependencies are processed, mark node **visited**.
4. If cycle found:
   - Format: `"Circular dependency detected: {id-slug-A} -> {id-slug-B} -> ... -> {id-slug-A}"`
   - Set `cycle_detected = true` and store the cycle description in `cycle_error`.
   - This blocks approval at the user gate (Step 8). Do not proceed to Step 7.
5. If no cycle: set `cycle_detected = false`, proceed to Step 7.

## Step 7: Topological Sort

Generate execution order via `tsort`:

1. Build tsort input lines from `mapped_decomposition`:
   - For each feature with dependencies: for each dep, emit `echo "{dep} {feature}"` (dependency before dependent).
   - For isolated features (empty `depends_on`): emit `echo "{feature} {feature}"` (self-edge ensures node appears in output).
2. Pipe all lines into `tsort`:
   ```
   printf "%s\n" {all lines} | tsort
   ```
3. Parse `tsort` output: each line is a feature `{id}-{slug}` in valid execution order.
4. Store result as `execution_order` array.
5. **Fallback:** If `command -v tsort` fails (tsort not available):
   - Perform LLM-based topological sort: "Order these features so that every feature appears after all its dependencies. Process nodes with zero in-degree first, remove their edges, repeat."
   - Store result as `execution_order`.

## Step 8: User Approval Gate

Initialize `refinement_count = 0`.

1. Build question text:
   - Base: `"Decomposition complete: {n} features across {m} modules. Approve?"`
   - If `cycle_detected == true`: prepend `"Warning: Circular dependency detected: {cycle_error}. Resolve by refining or cancel.\n\n"` to question text.
   - If `refinement_count >= 3`: replace question text with `"Final decision -- select one: {n} features across {m} modules."` (suppresses built-in Other option).

2. Present approval gate:
   ```
   AskUserQuestion:
     questions: [{
       "question": "{question_text}",
       "header": "Approval",
       "options": [
         {"label": "Approve", "description": "Create features and roadmap"},
         {"label": "Cancel", "description": "Save PRD without project features"}
       ],
       "multiSelect": false
     }]
   ```

3. Handle response:
   - **"Approve"** -> proceed to Step 9.
   - **"Cancel"** -> output `"Decomposition cancelled. PRD saved at {project_dir}/prd.md."` -> STOP.
   - **"Other" (free-text)** -> capture as `refinement_feedback`. Increment `refinement_count`. If `refinement_count > 3`: ignore, re-present with Approve/Cancel only. Otherwise: re-run full decomposer+reviewer cycle (Step 1) with previous `decomposition` + `refinement_feedback` appended to prompt, then return to Step 8.

## Step 9: Create Feature Directories

For each feature in `execution_order`:

1. Look up feature data from `mapped_decomposition` (name, description, module, depends_on, complexity).
2. Derive `{id}` and `{slug}` from the `{id}-{slug}` string.
3. Create directory `docs/features/{id}-{slug}/`.
4. Write `docs/features/{id}-{slug}/.meta.json`:
   ```json
   {
     "id": "{id}",
     "slug": "{slug}",
     "status": "planned",
     "created": "{ISO timestamp}",
     "mode": null,
     "branch": null,
     "project_id": "{project P-ID from project_dir basename}",
     "module": "{module name}",
     "depends_on_features": ["{dep-id}-{dep-slug}", ...],
     "lastCompletedPhase": null,
     "phases": {}
   }
   ```
   Note: `mode` and `branch` are null for planned features -- set during planned-to-active transition.

## Step 10: Generate roadmap.md

Write `{project_dir}/roadmap.md` with this structure:

- H1: `Roadmap: {Project Name}`
- Comment: `<!-- Arrow: prerequisite (A before B) -->`
- H2: `Dependency Graph` -- mermaid `graph TD` block with edges:
  ```
  F{id1}[{id1}-{slug1}] --> F{id2}[{id2}-{slug2}]
  ```
- H2: `Execution Order` -- numbered list:
  ```
  1. **{id}-{slug}** -- {description} (depends on: {deps or "none"})
  ```
- H2: `Milestones` -- for each milestone, H3 `M{n}: {name}` with bullet list of `{id}-{slug}` features.
- H2: `Cross-Cutting Concerns` -- bullet list from `cross_cutting` array.

Sources:
- `execution_order` array from Step 7 for ordering.
- `suggested_milestones` from decomposition (feature refs already remapped to ID-slugs in Step 5).
- `cross_cutting` array directly from decomposition.
- Mermaid edges: for each feature with dependencies, emit `F{dep-id}[{dep-id}-{dep-slug}] --> F{feature-id}[{feature-id}-{feature-slug}]`.

## Step 11: Update Project .meta.json

Read `{project_dir}/.meta.json` and update two fields:

1. Set `"features"` to array of `"{id}-{slug}"` strings in execution order.
2. Set `"milestones"` to array from `suggested_milestones` with feature refs as ID-slugs:
   ```json
   [{"name": "...", "features": ["{id}-{slug}", ...], "rationale": "..."}]
   ```

Write the updated JSON back to `{project_dir}/.meta.json`.

## Error Handling

| Error | Action |
|-------|--------|
| Feature directory creation fails mid-way | Keep created dirs, update project `.meta.json` with created features only |
| `roadmap.md` write fails | Warn user, continue with project `.meta.json` update |
| Project `.meta.json` update fails | Error, stop -- manual recovery needed |

## Output

After Step 11 completes, display:

```
Project decomposition complete.
  Features: {n} created ({comma-separated list of id-slug})
  Roadmap: {project_dir}/roadmap.md
  Next: Use /show-status to see project features, or /specify --feature={first-feature} to start
```
