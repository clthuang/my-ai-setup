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

<!-- Example format:
### Pattern: Early Interface Definition
Define interfaces before implementation. Enables parallel work.
- Used in: Feature #42
- Benefit: Reduced integration issues by 50%
-->
