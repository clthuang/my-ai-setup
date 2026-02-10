# Specification: Project-Level Workflow Foundation

## Problem Statement

The iflow-dev plugin has no mechanism to decompose a large product vision into multiple coordinated features, forcing solo developers to manually break down projects outside the workflow and losing the methodical rigor that makes the existing feature pipeline valuable.

## Success Criteria

- [ ] Brainstorm Stage 7 presents "Promote to Project" option when PRD matches 3+ of 6 defined scale signals
- [ ] Brainstorm Stage 7 does NOT show project option when PRD matches fewer than 3 signals
- [ ] `/create-project` command creates `docs/projects/{id}-{slug}/` with valid `.meta.json` and `prd.md`
- [ ] Decomposition subagent produces structured JSON matching the defined output schema
- [ ] Decomposition reviewer evaluates and challenges decomposition quality before user sees it
- [ ] `roadmap.md` contains a mermaid dependency graph and topologically-sorted execution order
- [ ] Decomposed features are created in `docs/features/` with `status: planned`, `project_id`, `module`, and `depends_on_features` fields
- [ ] Phase commands (specify, design, create-plan, create-tasks, implement) inject project PRD and roadmap as context when feature has `project_id`
- [ ] Phase commands inject completed dependency features' `spec.md` and `design.md` as context
- [ ] Features without `project_id` behave identically to current workflow (no regressions)
- [ ] `validate.sh` passes with 0 errors, 0 warnings (including planned features with nullable `branch` and `mode`)
- [ ] New `project-decomposer` agent passes validate.sh frontmatter checks
- [ ] New `project-decomposition-reviewer` agent passes validate.sh frontmatter checks
- [ ] Decomposition review-fix cycle blocks user approval gate until reviewer approves or max iterations reached
- [ ] New `decomposing` skill is under 500 lines and 5,000 tokens
- [ ] New `.meta.json` fields (`project_id`, `module`, `depends_on_features`, `planned` status) are recognized by all consuming components (6 direct + 5 phase commands via workflow-transitions)

## Scope

### In Scope (Phase 1 Foundation MVP)

1. **Scale detection in brainstorm Stage 7** (FR-1)
   - 6 closed signals analyzed by LLM against PRD content:
     1. **Multiple entity types** — PRD describes 3+ distinct data entities with separate CRUD lifecycles
     2. **Multiple functional areas** — PRD requires 3+ distinct functional capabilities (e.g., auth, billing, reporting)
     3. **Multiple API surfaces** — PRD needs 2+ API types (REST, WebSocket, GraphQL) or 3+ distinct API endpoint groups
     4. **Cross-cutting concerns** — PRD mentions capabilities that span multiple functional areas (auth, logging, permissions)
     5. **Multiple UI sections** — PRD describes 3+ distinct user-facing views/pages/screens
     6. **External integrations** — PRD requires 2+ external service integrations
   - Detection threshold: 3+ signals = recommend project route
   - "Promote to Project" option added to Stage 7 AskUserQuestion when threshold met
   - Both project and feature options shown when triggered; only feature when not
   - LLM-based detection is inherently fuzzy; false positives handled by user choosing "Promote to Feature", false negatives by manual `/create-project`

2. **Project creation command and data model** (FR-2)
   - New `/create-project` command, invocable two ways:
     - Automatically from brainstorm Stage 7 when user selects "Promote to Project"
     - Standalone: `/create-project --prd={path}` (fallback for scale detection misses)
   - Creates `docs/projects/{id}-{slug}/` directory with `.meta.json` and `prd.md`
   - P-prefixed project IDs (P001, P002, etc.)
   - Project statuses: `active`, `completed`, `abandoned`
   - During project creation, user is asked for `expected_lifetime` via AskUserQuestion with options: "3-months", "6-months", "1-year", "2-years" (default: "1-year")
   - **Project `.meta.json` schema:**
     ```json
     {
       "id": "P001",
       "slug": "crypto-tracker",
       "status": "active",
       "expected_lifetime": "1-year",
       "created": "2026-02-10T11:40:52Z",
       "completed": null,
       "brainstorm_source": "docs/brainstorms/20260210-114052-crypto-tracker.prd.md",
       "milestones": [
         {
           "id": "M1",
           "name": "Foundation",
           "status": "active",
           "features": ["021-auth", "022-data-models"]
         }
       ],
       "features": ["021-auth", "022-data-models", "023-dashboard"],
       "lastCompletedMilestone": null
     }
     ```

3. **AI-driven project decomposition with skeptical review** (FR-3)
   - New `project-decomposer` agent (subagent) — generates decomposition
   - New `project-decomposition-reviewer` agent (subagent) — skeptical review of decomposition quality
   - Input: full PRD markdown text + `expected_lifetime` from project `.meta.json`
   - **Decomposition output schema:**
     ```json
     {
       "modules": [
         {
           "name": "Authentication",
           "description": "User auth and session management",
           "features": [
             {
               "name": "User registration and login",
               "description": "Email/password auth with JWT tokens",
               "depends_on": [],
               "complexity": "Medium"
             }
           ]
         }
       ],
       "cross_cutting": ["Error handling patterns", "API response format"],
       "suggested_milestones": [
         {
           "name": "Foundation",
           "features": ["User registration and login", "Core data models"],
           "rationale": "Required by all other features"
         }
       ]
     }
     ```
   - New `decomposing` skill orchestrating: decomposer call → reviewer review-fix cycle (max 3 iterations) → cycle detection → topological sort → milestone grouping → user approval gate (max 3 refinement iterations)
   - **Reviewer evaluation criteria** (checklist in reviewer agent prompt):
     1. Organisational cohesion — module boundaries align with functional domains
     2. Engineering best practices — dependencies flow one direction, no god-modules, no circular deps
     3. Goal alignment — decomposition serves PRD goals without premature generalisation
     4. Lifetime-appropriate complexity — complexity calibrated to `expected_lifetime`
     5. 100% coverage — every PRD requirement maps to at least one feature
   - Review-fix cycle: reviewer returns JSON with `approved`, `issues[]`, `criteria_evaluated[]`; decomposer revises on rejection; max 3 iterations
   - `roadmap.md` artifact with mermaid graph and execution order
   - User approval gate via AskUserQuestion after reviewer approves (max 3 user refinement iterations)
   - Milestone groupings based on dependency layers (features sharing same dependency depth grouped together); delegated to LLM decomposer via `suggested_milestones` output

4. **Feature-project linking and planned→active transition** (FR-4)
   - New optional `.meta.json` fields: `project_id`, `module`, `depends_on_features`
   - New feature status: `planned` (created by decomposition, not yet started)
   - **Feature creation from decomposition:** The `decomposing` skill creates feature directories directly, writing `.meta.json` with:
     ```json
     {
       "id": "022",
       "slug": "data-models",
       "mode": null,
       "status": "planned",
       "created": "2026-02-10T12:00:00Z",
       "branch": null,
       "project_id": "P001",
       "module": "Core",
       "depends_on_features": ["021-auth"],
       "lastCompletedPhase": null,
       "phases": {}
     }
     ```
   - `mode` and `branch` are `null` for planned features (set when transitioning to active)
   - `validate.sh` must be updated to allow `null` for `mode` and `branch` when `status` is `planned`
   - **Planned→active transition:** When user runs `/specify` (or any first phase command) on a planned feature:
     1. System detects `status: "planned"` and prompts via AskUserQuestion: "Start working on {id}-{slug}? This will set it to active and create a branch."
     2. User selects workflow mode (Standard/Full) via AskUserQuestion
     3. System updates `.meta.json`: `status` → `"active"`, `mode` → selected mode, `branch` → `"feature/{id}-{slug}"`
     4. System creates git branch
     5. Phase 1 enforces single-active-feature: if another active feature exists, show existing active-feature-exists warning via AskUserQuestion (same as current `create-feature` behavior)
   - `depends_on_features` is stored and used for roadmap generation and context injection but NOT enforced at runtime in Phase 1 (enforcement deferred to Phase 2)

5. **Project context injection** (FR-4b)
   - `workflow-transitions` `validateAndSetup` gains a new Step 5 (after marking phase started): "Inject project context"
   - When `project_id` is detected in feature `.meta.json`:
     1. Read project PRD: `docs/projects/{project_id}-{slug}/prd.md`
     2. Read roadmap: `docs/projects/{project_id}-{slug}/roadmap.md`
     3. For each feature in `depends_on_features` with `status: "completed"`: read its `spec.md` and `design.md`
     4. Prepend to phase input as:
        ```markdown
        ## Project Context
        ### Project PRD
        {content of prd.md}
        ### Roadmap
        {content of roadmap.md}
        ### Completed Dependency: {feature-id-slug}
        #### Spec
        {content of spec.md}
        #### Design
        {content of design.md}
        ```
   - If project directory or roadmap.md does not exist: warn "Project artifacts missing for {project_id}, proceeding without project context" and continue
   - All phase commands receive this context automatically via workflow-transitions
   - Standalone features (no `project_id`) skip Step 5 entirely — no behavior change

6. **Project lifetime philosophy** (FR-5)
   - Projects have an expected lifetime — systems are not built to last forever
   - Decomposition reviewer challenges over-engineering and premature generalisation
   - Focus on good scaffolding that makes rebuilding easy before entropy sets in
   - `expected_lifetime` field in project `.meta.json` is set during project creation (user selects via AskUserQuestion, default "1-year")
   - Decomposition reviewer uses lifetime expectation to calibrate complexity tolerance: shorter lifetime = simpler decomposition, less abstraction

7. **`.meta.json` field consistency across workflow** (FR-6)
   - New fields (`project_id`, `module`, `depends_on_features`) and new status value (`planned`) must be recognized by all consuming components:
     - `workflow-state` skill — schema documentation updated with new fields, new status value, and nullable `mode`/`branch` for planned features
     - `workflow-transitions` skill — `validateAndSetup` gains Step 5 for project context injection; recognizes `planned` status for transition to `active`
     - `create-feature` command — no changes needed (decomposing skill creates planned features directly; create-feature only handles user-initiated creation)
     - `show-status` command — displays `project_id` and `module` when present; shows `planned` features grouped under their project with basic grouping (not full dashboard — that's Phase 2)
     - `list-features` command — includes `planned` features; shows project affiliation
     - `session-start` hook — recognizes `planned` status (not surfaced as "active feature"); includes project name in context when active feature has `project_id`
     - `finish` command — no changes needed (only operates on `active` features)
     - Phase commands (specify, design, create-plan, create-tasks, implement) — receive project context via `workflow-transitions` Step 5; handle planned→active transition at first invocation
     - `validate.sh` — updated to allow `null` for `mode` and `branch` when `status` is `planned`
   - Standalone features (no `project_id`) behave identically to current workflow

### Out of Scope

- Concurrent feature support (multiple `status: active` simultaneously) — Phase 2
- Dependency enforcement at `/specify` (blocking warnings for unmet dependencies) — Phase 2
- Full project dashboard in `show-status` (milestone progress table, critical path, next actionable features) — Phase 2
- Project finish command — Phase 3
- `/show-roadmap`, feature re-sequencing, milestone management commands — Phase 3
- Project templates, cross-project dependencies, time-based milestones
- Automated merge conflict detection between concurrent features
- Shared project architecture document (context injection serves this purpose for MVP)

## Acceptance Criteria

### AC-1: Scale Detection
- Given a PRD describing 4+ entity types, 3+ functional areas, and cross-cutting auth concerns
- When brainstorm Stage 7 runs
- Then AskUserQuestion presents 4 options: "Promote to Project (recommended)", "Promote to Feature", "Refine Further", "Save and Exit"

### AC-2: Scale Detection — No False Positive
- Given a PRD describing a single utility function with 1 entity type and 1 functional area
- When brainstorm Stage 7 runs
- Then AskUserQuestion presents only: "Promote to Feature", "Refine Further", "Save and Exit" (no project option)

### AC-3: Project Creation
- Given the user selects "Promote to Project" in brainstorm Stage 7
- When project creation runs
- Then `docs/projects/P001-{slug}/.meta.json` exists with fields: id, slug, status="active", expected_lifetime, created, milestones=[], features=[], brainstorm_source
- And `docs/projects/P001-{slug}/prd.md` exists with the PRD content

### AC-4: Decomposition — Happy Path
- Given a project PRD with 4 distinct modules
- When the decomposition skill runs
- Then the `project-decomposer` subagent returns JSON with: `modules[]` (each with name, description, features[]), `cross_cutting[]`, `suggested_milestones[]`
- And each feature in the output has `name`, `description`, `depends_on[]`, and `complexity` fields
- And no circular dependencies exist in the depends_on graph

### AC-5: Decomposition — Cycle Detection
- Given the decomposition subagent returns features with circular dependencies (A depends on B, B depends on A)
- When cycle detection runs
- Then the system blocks approval and displays the cycle to the user
- And the user can refine (up to 3 iterations)

### AC-6: Roadmap Generation
- Given an approved decomposition with 4 modules and 10 features
- When roadmap generation runs
- Then `docs/projects/{id}-{slug}/roadmap.md` contains:
  - A mermaid dependency graph with all features as nodes and dependency edges
  - A topologically-sorted execution order (features with no dependencies first)
  - Milestone groupings based on dependency layers (as output by the decomposer's `suggested_milestones`)

### AC-7: Feature Creation from Decomposition
- Given an approved decomposition with 3 features
- When the decomposing skill creates feature directories
- Then 3 entries exist in `docs/features/` with `.meta.json` containing:
  - `status: "planned"`, `mode: null`, `branch: null`
  - `project_id: "P001"`
  - `module: "{module name}"`
  - `depends_on_features: ["{id-slug}", ...]` matching decomposition output
- And no active-feature-exists warning is triggered

### AC-8: Planned→Active Transition
- Given a feature with `status: "planned"` and `mode: null` and `branch: null`
- When user runs `/specify` on that feature
- Then system asks to confirm starting work and select workflow mode via AskUserQuestion
- And on confirmation: `status` becomes `"active"`, `mode` is set, `branch` is set, git branch is created
- And if another feature already has `status: "active"`: active-feature-exists warning is shown first

### AC-9: Project Context Injection — Phase Commands
- Given a feature with `project_id: "P001"` and `docs/projects/P001-{slug}/prd.md` exists
- When `/specify` runs on that feature
- Then the skill's input context includes a "## Project Context" section containing the project PRD title heading and roadmap content

### AC-10: Project Context Injection — Sibling Artifacts
- Given Feature B depends on Feature A (`depends_on_features: ["021-auth"]`)
- And Feature A has `status: "completed"` with `spec.md` and `design.md`
- When `/design` runs on Feature B
- Then the skill's input context includes a "### Completed Dependency: 021-auth" section with Feature A's spec and design content

### AC-11: No Regression — Standalone Features
- Given a feature without `project_id` field in `.meta.json`
- When any phase command runs (specify, design, create-plan, create-tasks, implement)
- Then the command behaves identically to current workflow (no project context injection, no feature picker, no changes)

### AC-12: Decomposition Approval Gate
- Given the decomposition subagent has returned results
- When the system presents the user approval gate
- Then AskUserQuestion shows: "Approve decomposition ({N} modules, {M} features)", "Refine (describe what to change)", "Cancel (save PRD without project creation)"
- And selecting "Refine" allows up to 3 refinement iterations before forcing a decision

### AC-13: Decomposition Review-Fix Cycle
- Given the `project-decomposer` agent has produced a decomposition
- When the `project-decomposition-reviewer` agent reviews it
- Then the reviewer is invoked with a prompt containing the 5 evaluation criteria (organisational cohesion, engineering best practices, goal alignment, lifetime-appropriate complexity, 100% coverage)
- And the reviewer returns JSON with `approved`, `issues[]`, and `criteria_evaluated[]` fields
- And if issues found: the decomposer revises and reviewer re-evaluates (up to 3 iterations)
- And if approved: decomposition proceeds to cycle detection and user approval gate
- And if max iterations reached without approval: concerns are noted and user sees them at the approval gate

### AC-14: Decomposition Reviewer — Over-Engineering Detection
- Given a project with `expected_lifetime: "6-months"` and a decomposition proposing 8 modules with shared abstraction layers
- When the `project-decomposition-reviewer` evaluates with the lifetime-appropriate complexity criterion
- Then the reviewer's `issues[]` includes at least one entry referencing over-engineering relative to the expected lifetime

### AC-15: `.meta.json` Field Consistency — Schema
- Given the new fields are defined (`project_id`, `module`, `depends_on_features`, status `planned`)
- When `workflow-state` skill documentation is read
- Then all new fields appear in the State Schema section with types and descriptions
- And `planned` appears in the Status Values table

### AC-16: `.meta.json` Field Consistency — Show Status
- Given 3 features with `project_id: "P001"` (1 planned, 1 active, 1 completed)
- When `/show-status` runs
- Then planned features appear grouped under their project (basic grouping, not full dashboard)
- And the active feature shows its project affiliation and module

### AC-17: `.meta.json` Field Consistency — Session Start
- Given the most recent active feature has `project_id: "P001"`
- When a new session starts
- Then the session context message includes the project name
- And given no active feature but 2 planned features exist for project P001
- Then the session context does NOT surface planned features as "active"

### AC-18: validate.sh — Planned Feature Compatibility
- Given a feature with `status: "planned"`, `mode: null`, `branch: null`
- When `validate.sh` runs
- Then no errors are reported for the null `mode` and `branch` fields

## Feasibility Assessment

### Assessment Approach
1. **First Principles** — Adding a directory, JSON metadata, and markdown artifacts is straightforward file I/O
2. **Codebase Evidence** — Existing patterns support every component
3. **External Evidence** — Topological sort is a well-known algorithm; LLM-based decomposition is standard practice

### Feasibility Scale
| Level | Meaning | Evidence Required |
|-------|---------|-------------------|
| Confirmed | Verified working approach | Code reference or documentation |
| Likely | No blockers, standard patterns | First principles reasoning |
| Uncertain | Assumptions need validation | List assumptions to verify |

### Assessment
**Overall:** Confirmed

**Reasoning:** Every component maps directly to existing patterns in the codebase:
- Scale detection: LLM analysis of PRD text — same approach as brainstorm Stage 4 reviewer analysis. Location: `plugins/iflow-dev/skills/brainstorming/SKILL.md:200-270`
- Project creation: Mirrors feature creation (directory + .meta.json + artifact). Location: `plugins/iflow-dev/commands/create-feature.md`
- Decomposition agent: Follows existing agent pattern (YAML frontmatter + system prompt + JSON output). Location: `plugins/iflow-dev/agents/prd-reviewer.md` (same input/output pattern)
- Decomposition reviewer: Same pattern as `spec-reviewer`, `design-reviewer`, `task-reviewer` — skeptical JSON-response agent with review-fix cycle. Location: `plugins/iflow-dev/agents/spec-reviewer.md`, `plugins/iflow-dev/agents/task-reviewer.md`
- Review-fix cycle: Established pattern in specify, design, create-plan, create-tasks phases — decomposer produces, reviewer challenges, loop until approved or max iterations. Location: `plugins/iflow-dev/commands/specify.md` (Stage 1 loop)
- Roadmap artifact: Markdown with mermaid — same as `tasks.md` dependency graph. Location: `plugins/iflow-dev/skills/breaking-down-tasks/SKILL.md:94-103`
- Feature .meta.json extensions: Schema is open-ended, additions are backward-compatible. Location: `docs/features/005-make-specs-executable/.meta.json` (7 fields) vs `docs/features/020-crypto-domain-skills/.meta.json` (full tracking)
- Context injection in workflow-transitions: Adding a conditional read step in `validateAndSetup`. Location: `plugins/iflow-dev/skills/workflow-transitions/SKILL.md:10-99`
- `planned` status: Adding a string value to an unvalidated field — no code changes needed beyond recognizing it. Location: `plugins/iflow-dev/skills/workflow-state/SKILL.md:183-270`
- Planned→active transition: Same pattern as `create-feature` (mode selection, branch creation, .meta.json update). Location: `plugins/iflow-dev/commands/create-feature.md`
- validate.sh update: Simple conditional to skip `mode`/`branch` checks for `planned` status. Location: `validate.sh:479-528`
- Field consistency: 6 direct consumers + 5 phase commands (via workflow-transitions) + finish (no changes) + validate.sh. Each needs a small conditional addition.

**Key Assumptions:**
- LLM can reliably detect scale signals in PRD text — Status: Likely (LLM already performs complex analysis in brainstorm stages 4-6)
- LLM can decompose a PRD into well-structured modules/features — Status: Likely (similar to task breakdown, which works well)
- LLM reviewer can evaluate decomposition quality against engineering principles — Status: Likely (same pattern as design-reviewer evaluating architecture quality)
- Topological sort can be implemented as LLM instructions (not programmatic code) — Status: Likely (the sort is on small graphs, 5-20 nodes; LLM can order them)
- `validate.sh` can be updated to handle nullable fields for planned features — Status: Confirmed (simple conditional in bash)

**Open Risks:** If LLM decomposition quality is poor, the review-fix cycle and user approval gate catch it (max 3 reviewer iterations + max 3 user refinements). Manual `/create-project` remains as fallback.

## Dependencies

- None (this is Phase 1 with no prerequisites)

## Open Questions

- None for Phase 1. Remaining PRD open questions are deferred to Phase 2+.
