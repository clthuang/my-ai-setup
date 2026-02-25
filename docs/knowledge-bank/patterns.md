# Patterns

Approaches that have worked well. Updated through retrospectives.

---

## Development Patterns

### Pattern: Context7 for Configuration Verification
Use Context7 to look up Claude Code documentation before guessing configuration syntax.
- Used in: Feature #002
- Benefit: Discovered correct hooks auto-discovery path (plugin root, not .claude-plugin/)
- Avoided: Wrong fix that would have required later correction

### Pattern: Follow Skill Completion Guidance
Read skill completion messages for the correct next step instead of guessing.
- Used in: Feature #002
- Benefit: Skills define the workflow; following them ensures consistency
- Example: designing skill says "Run /create-plan" not "/create-tasks"

### Pattern: Coverage Matrix for Multi-Component Work
When modifying multiple similar components, create a coverage matrix early.
- Used in: Feature #003
- Benefit: Caught missing brainstorm and verify commands during task verification
- Example: Matrix showing Command × (Validation, Reviewer Loop, State Update)
- Instead of: Discovering gaps during implementation

### Pattern: Hardened Persona for Review Agents
Define explicit "MUST NOT" constraints for reviewer agents to prevent scope creep.
- Used in: Feature #003
- Benefit: Clear boundaries prevent reviewers from suggesting new features
- Mantra: "Is this artifact clear and complete FOR WHAT IT CLAIMS TO DO?"
- Key constraints: No new features, no nice-to-haves, no questioning product decisions

### Pattern: Chain Validation Principle
Each workflow phase output should be self-sufficient for the next phase.
- Used in: Feature #003
- Benefit: Clear reviewer context - what to validate and why
- Question: "Can next phase complete its work using ONLY this artifact?"
- Enables: Expectations table defining what each phase needs from previous

### Pattern: PROJECT_ROOT vs PLUGIN_ROOT in Hooks
Use PROJECT_ROOT for dynamic project state, PLUGIN_ROOT for static plugin assets.
- Discovered in: Plugin cache staleness bug fix
- Benefit: Prevents reading stale cached data when plugin files are copied
- Implementation: Shared `detect_project_root()` function in `hooks/lib/common.sh`
- Key insight: Claude's PWD may be a subdirectory, so walk up to find `.git`
- See: [Hook Development Guide](../guides/hook-development.md)

### Pattern: Hook Schema Compliance
Hook JSON output must use correct field names for each hook type.
- Discovered in: Feature #005
- Problem: PreToolUse used `decision`/`additionalContext` but should use `permissionDecision`/`permissionDecisionReason`
- Key insight: Different hook types have different valid fields:
  - SessionStart: `hookSpecificOutput.additionalContext`
  - PreToolUse: `hookSpecificOutput.permissionDecision`, `permissionDecisionReason`
  - PostToolUse: `hookSpecificOutput.additionalContext`
- Validation: Use Context7 to look up Claude Code hook documentation for authoritative schema
- Solution: Tests should validate output structure matches expected schema per hook type

### Pattern: Retroactive Feature Creation as Recovery
When work is done outside the workflow, recover by creating feature artifacts after the fact.
- Used in: Feature #008
- Steps: Create folder + .meta.json, write brainstorm.md/spec.md, create branch, commit, run /iflow:finish
- Benefit: Preserves audit trail without discarding completed work
- Trade-off: Artifacts are reconstructed, not organic; less detailed than if created during work

### Pattern: Two-Plugin Coexistence
Maintain separate dev (iflow/) and production (iflow/) plugin directories.
- Used in: Feature #012
- Benefit: Clean releases via copy, no branch-based transformations
- Protection: Pre-commit hook blocks direct commits to production plugin

### Pattern: Environment Variable Bypass for Automation
Use env var (e.g., IFLOW_RELEASE=1) to bypass protective hooks during scripted operations.
- Used in: Feature #012
- Benefit: Hooks protect interactive use while allowing automation
- Key: Check early in hook, output allow with reason, exit cleanly

### Pattern: Parallel Subagent Delegation for Independent Research
Deploy multiple subagents in parallel when researching independent domains.
- Used in: Feature #013
- Benefit: Faster research, no dependencies between internet/codebase/skills searches
- Implementation: Multiple Task tool calls in single response for simultaneous invocation
- Key: Each agent has clear domain boundary and returns structured findings

### Pattern: Evidence-Backed Claims in Documentation
Require citations for technical claims in PRDs and design documents.
- Used in: Feature #013
- Benefit: Improves intellectual honesty, surfaces assumptions vs verified facts
- Format: `{claim} — Evidence: {source}` or `{claim} — Assumption: needs verification`
- Quality gate: Reviewer challenges uncited claims and false certainty

### Pattern: Trigger Phrase Descriptions for Skills and Agents
Use explicit trigger phrases in descriptions to enable intent matching.
- Source: [Anthropic plugin-dev](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/plugin-dev)
- Format: `This skill should be used when the user says 'X', 'Y', or 'Z'. [Capability description].`
- Benefit: AI can match user intent to components via quoted phrases
- Key: Use third-person language, not second-person; include 3-4 trigger phrases
- Applied: 2026-02-04 quality improvements

### Pattern: Semantic Color Coding for Agents
Assign colors to agents based on functional category for visual distinction.
- Used in: 2026-02-04 quality improvements
- Categories:
  - `cyan` = Research (exploration, investigation)
  - `green` = Implementation (writing code/docs)
  - `blue` = Planning/validation (chain, design, plan review)
  - `yellow` = Early-stage review (brainstorm, PRD)
  - `magenta` = Quality/compliance review (spec, security, final)
  - `red` = Simplification
- Benefit: Terminal output distinguishes agent types at a glance

### Pattern: Thin Orchestrator + Reference Files
Keep SKILL.md as a process orchestrator (<120 lines), push domain knowledge to `references/` directory.
- Used in: Feature #018
- Benefit: Extensible without touching core logic; new types/methods added to reference files only
- Structure: SKILL.md defines Input/Process/Output, references/ holds domain-specific content
- Example: structured-problem-solving SKILL.md (114 lines) + 4 reference files (~480 lines total)

### Pattern: Cross-Skill Read via Base Directory
Derive sibling skill path by replacing skill name in Base directory path for read-only access.
- Used in: Feature #018
- Mechanism: Replace `skills/{current-skill}` with `skills/{target-skill}` in Base directory
- Constraint: Read-only access to reference files only; never write to another skill's directory
- Fallback: Copy needed content to own `references/` directory if path resolution fails

### Pattern: Conditional PRD Sections
Use "only when condition is met" guards for optional sections in document templates.
- Used in: Feature #018
- Benefit: Backward compatibility — absence of condition means default behavior
- Example: Structured Analysis section only appears when Problem Type is not "none"
- Key: Missing field = default behavior, no version flags or migration scripts needed

### Pattern: Zero-Code-Change State Machine Solutions
Explore whether existing transition logic can handle new cases by setting the right initial state values.
- Used in: Feature #021
- Benefit: Avoided modifying core validateTransition logic for planned→active feature transitions
- Example: Setting `lastCompletedPhase = "brainstorm"` made /specify a normal forward transition (index 1 == 0 + 1)
- Key: Reuse existing invariants rather than adding conditional branches

### Pattern: Test Fixtures Must Match Tool Scan Paths
Place test fixtures where validation tools actually scan, not in temporary/sandbox locations.
- Used in: Feature #021
- Benefit: Plan reviewer caught that fixtures in agent_sandbox/ would be invisible to validate.sh scanning docs/features/
- Instead: Use docs/features/999-test-*/ for validate.sh fixtures, with explicit cleanup steps

### Pattern: Independent Iteration Budgets for Nested Cycles
When a workflow has nested iteration loops, make budgets independent.
- Used in: Feature #021
- Benefit: Reviewer-decomposer cycle (max 3) doesn't consume user refinement cycle (max 3) budget
- Key: Each cycle has its own counter and max, preventing one from starving the other

### Pattern: Heavy Upfront Review Investment
Heavy upfront review investment (15-30+ pre-implementation review iterations) correlates with clean implementation (0-1 actionable issues across all reviewers). Front-loading review effort shifts risk discovery to phases where changes are cheap (text edits) rather than expensive (code changes).
- Observed in: Feature #022, implementation phase
- Confidence: high
- Last observed: Feature #025
- Observation count: 2

### Pattern: Template Indentation Matching
When inserting blocks into existing prompt templates, read the target file first and match its specific indentation level (which may differ per file). Prevents downstream formatting issues.
- Observed in: Feature #022, Task 1.5
- Confidence: medium
- Last observed: Feature #022
- Observation count: 1

<!-- Example format:
### Pattern: Early Interface Definition
Define interfaces before implementation. Enables parallel work.
- Used in: Feature #42
- Benefit: Reduced integration issues by 50%
-->

### Pattern: Skeptic Design Reviewer Catches Feasibility Blockers Early
When the design reviewer operates in 'skeptic' mode and challenges unverified assumptions (CLI mechanisms, parser complexity, file format handling, runtime behavior gaps), it prevents costly rework in later phases. Architectural pivots and behavioral clarifications made during design are far cheaper than discovering these issues during implementation.
- Observed in: Feature #023, design phase
- Confidence: high
- Last observed: Feature #025
- Observation count: 2

### Pattern: Detailed Rebuttals With Line-Number Evidence Resolve False Positives
When the implementer provides exact line references, quotes from spec/design, and git-blame evidence for pre-existing code, false-positive review blockers are resolved without code churn. This preserves implementation quality while avoiding unnecessary changes.
- Observed in: Feature #023, implement phase
- Confidence: medium
- Last observed: Feature #023
- Observation count: 1

### Pattern: Documentation Gap Verification via Three-Point Anchor
When merging documentation improvements into CLAUDE.md, cross-examine candidate items against three anchor points: (1) constitution.md core principles, (2) system prompt enforced behaviors, (3) workflow phase safety mechanisms. Items present in all three are redundant; items in none are genuine gaps.
- Observed in: CLAUDE.md Working Standards addition — filtered 8 candidates to 5
- Confidence: high
- Last observed: 2026-02-22
- Observation count: 1

### Pattern: Directive Specificity via Tooling References
When writing behavioral guidance in documentation, include explicit tool/command references (e.g., `/iflow:remember`, `systematic-debugging` skill) instead of abstract principles. Concrete references reduce interpretation variance.
- Observed in: CLAUDE.md Working Standards section
- Confidence: medium
- Last observed: 2026-02-22
- Observation count: 1

### Pattern: Domain Reviewer Approval Gates Chain Reviewer Escalation
When the domain reviewer (task-reviewer, plan-reviewer) has explicitly approved a domain-specific concern (task sizing, heuristic tolerances, format specifics), the chain reviewer (phase-reviewer) may note it but may not re-raise it as Needs Revision. Domain expertise on domain concerns is final for structural gatekeepers.
- Observed in: Feature #026, create-tasks phase — 5 chain review iterations on task-size concern approved by domain reviewer at iter 3
- Confidence: high
- Last observed: 2026-02-22
- Observation count: 1

### Pattern: Extract Behavioral Anchors to Reference Files for Evaluator Skills
When building a skill with an LLM-as-evaluator pattern (score N dimensions, generate improved version), extract behavioral anchors into a separate reference file (scoring-rubric.md) rather than embedding them in SKILL.md. This keeps the skill under token budget and allows rubric updates without modifying the skill.
- Observed in: Feature #027, design phase — SKILL.md landed at 216 lines (well under 500) because behavioral anchors lived in references/
- Confidence: high
- Last observed: Feature #027
- Observation count: 1

### Pattern: Calibration Gates Between Skill and Command Creation
After building an evaluator skill, run it on 2-3 diverse inputs and verify score differentiation (e.g., 20+ point spread) before proceeding to build dispatcher commands. Without early calibration, a rubric that fails to differentiate would only be discovered during end-to-end validation, requiring cascading rework.
- Observed in: Feature #027, plan phase — plan-reviewer iter 2 blocker: "No intermediate calibration testing — late-stage rework risk for scoring rubric"
- Confidence: high
- Last observed: Feature #027
- Observation count: 1

### Pattern: Compose-Then-Write for Multi-Transformation File Updates
For patterns where multiple transformations apply to one file, build the complete content in memory first and perform a single write rather than multiple sequential writes. Prevents partial-update states and reduces error surface.
- Observed in: Feature #027, implementation iter 7 — quality reviewer flagged 3 sequential writes to same file; restructured to compose-then-write
- Confidence: high
- Last observed: Feature #027
- Observation count: 1
