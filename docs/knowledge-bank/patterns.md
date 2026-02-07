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
Maintain separate dev (iflow-dev/) and production (iflow/) plugin directories.
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

<!-- Example format:
### Pattern: Early Interface Definition
Define interfaces before implementation. Enables parallel work.
- Used in: Feature #42
- Benefit: Reduced integration issues by 50%
-->
