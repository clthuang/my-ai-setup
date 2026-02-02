# Brainstorm: Enhanced Brainstorm-to-PRD Workflow

## Problem Statement

The current workflow jumps from **brainstorm** (loose exploration) directly to **specification** (technical details). This skips a critical formalization step where:
- Ambiguities get resolved
- Goals become concrete
- Requirements are fully enumerated

Additionally, the current brainstorm phase:
- Relies solely on conversation — doesn't leverage subagents to research, review codebase, or critically evaluate
- May produce PRDs based on incomplete information
- Can be blindsided by existing patterns/constraints in the codebase

## Goals

1. **Document the 'what' before the 'how'** — PRD captures requirements/outcomes, spec captures technical approach
2. **Better stakeholder communication** — PRD is readable by non-technical folks
3. **Quality gate** — Force rigorous thinking before implementation
4. **Evidence-based decisions** — All technical claims verified, assumptions flagged
5. **Intellectual honesty** — Welcome uncertainty, reject false certainty

## Approaches Considered

### Approach A: Evolve Brainstorm Phase
Modify the existing brainstorming skill to add subagent calls and change output format.

- Pros: Minimal structural change, one phase does more work
- Cons: Brainstorm phase becomes heavy/complex, harder to test, conflates exploration with formalization

### Approach B: Two-Phase Split (Brainstorm + PRD)
Add a new PRD phase between brainstorm and specification.

- Pros: Clean separation of concerns, each phase has clear purpose
- Cons: More phases = more overhead, adds complexity

### Approach C: Brainstorm Produces PRD (Single Phase, Enhanced)
Keep single "brainstorm" command but internally runs research subagents and outputs PRD format.

- Pros: User-facing simplicity, research happens automatically
- Cons: "Brainstorm" name becomes misleading, less flexibility

## Chosen Direction

**Enhanced Brainstorm → PRD Flow** — The brainstorm command becomes a multi-stage process:

```
┌─────────────────────────────────────────────────────────────┐
│                    BRAINSTORM COMMAND                       │
├─────────────────────────────────────────────────────────────┤
│ 1. CLARIFY                                                  │
│    • Ask probing questions                                  │
│    • Resolve ambiguities                                    │
│    • Understand goals, constraints, context                 │
│                                                             │
│ 2. RESEARCH (Subagents)                                     │
│    • Internet research - best practices, prior art          │
│    • Codebase exploration - existing patterns, constraints  │
│    • Skill search - relevant existing capabilities          │
│    → Output: research notes with sources/references         │
│                                                             │
│ 3. DRAFT PRD                                                │
│    • Goals, success criteria                                │
│    • User stories, use cases                                │
│    • Edge cases (informed by research)                      │
│    • Constraints, requirements, anti-goals                  │
│    → Each decision/claim must cite evidence                 │
│                                                             │
│ 4. CRITICAL REVIEW (Subagent)                               │
│    • Challenge assumptions                                  │
│    • Identify gaps, blind spots                             │
│    • Suggest improvements                                   │
│    → Each critique includes: what's wrong, why it matters,  │
│      evidence, suggested fix                                │
│                                                             │
│ 5. AUTO-CORRECT                                             │
│    • Apply actionable improvements from review              │
│    • Fix gaps that have clear solutions                     │
│    → Each correction notes what changed and why             │
│                                                             │
│ 6. USER DECISION                                            │
│    • Refine further (loop back)                             │
│    • Turn into feature                                      │
│    • Abandon                                                │
└─────────────────────────────────────────────────────────────┘
```

**Output:** `docs/brainstorms/{timestamp}-{slug}.prd.md`

## PRD Format

```markdown
# PRD: {Feature Name}

## Status
- Created: {date}
- Last updated: {date}
- Status: Draft | Ready for Review | Approved | Abandoned

## Problem Statement
{What problem are we solving? Why does it matter?}

### Evidence
- {Source}: {Finding that supports this problem exists}

## Goals
1. {Goal 1}
2. {Goal 2}

## Success Criteria
- [ ] {Measurable criterion 1}
- [ ] {Measurable criterion 2}

## User Stories

### Story 1: {Title}
**As a** {role}
**I want** {capability}
**So that** {benefit}

**Acceptance criteria:**
- {criterion}

## Use Cases

### UC-1: {Title}
**Actors:** {who}
**Preconditions:** {what must be true}
**Flow:**
1. {step}
2. {step}
**Postconditions:** {what is true after}
**Edge cases:**
- {edge case with handling}

## Edge Cases & Error Handling
| Scenario | Expected Behavior | Rationale |
|----------|-------------------|-----------|
| {case}   | {behavior}        | {why}     |

## Constraints

### Behavioral Constraints (Must NOT do)
- {Behavior to avoid} — Rationale: {why this would be harmful}

### Technical Constraints
- {Technical limitation} — Evidence: {source}

## Requirements

### Functional
- FR-1: {requirement}

### Non-Functional
- NFR-1: {requirement}

## Non-Goals
Strategic decisions about what this feature will NOT aim to achieve.

- {Non-goal} — Rationale: {why we're explicitly not pursuing this}

## Out of Scope (This Release)
Items excluded from current scope but may be considered later.

- {Item} — Future consideration: {when/why it might be added}

## Research Summary

### Internet Research
- {Finding} — Source: {URL/reference}

### Codebase Analysis
- {Pattern/constraint found} — Location: {file:line}

### Existing Capabilities
- {Relevant skill/feature} — How it relates: {explanation}

## Review History
### Review 1 ({date})
**Findings:**
- {issue} — Severity: {blocker|warning|suggestion}

**Corrections Applied:**
- {what changed} — Reason: {reference to finding}

## Open Questions
- {Question that needs resolution}

## Next Steps
Ready for /iflow:create-feature to begin implementation.
```

## Quality Criteria

### 1. Completeness
- [ ] Problem statement is clear and specific
- [ ] Goals are defined (don't need evidence, just clarity)
- [ ] Solutions/approaches cite evidence for feasibility
- [ ] User stories cover primary personas
- [ ] Use cases cover main flows
- [ ] Edge cases identified and addressed
- [ ] Constraints documented (behavioral + technical)
- [ ] Non-goals explicitly stated
- [ ] Scope is clearly bounded with trade-offs stated

### 2. Intellectual Honesty
- [ ] Unchecked assumptions are flagged as assumptions
- [ ] Uncertainty is explicitly acknowledged (not hidden)
- [ ] No false certainty — if we don't know, we say so
- [ ] Judgment calls are labeled as such with reasoning
- [ ] Vague references are replaced with specifics

### 3. Evidence Standards
- [ ] Technical capabilities verified against codebase/docs, not assumed
- [ ] External claims have sources/references
- [ ] Research findings cite where they came from
- [ ] "It should work" → replaced with "Verified at {location}" or "Assumption: needs verification"

### 4. Clarity
- [ ] Success criteria are measurable
- [ ] No ambiguous language without explicit acknowledgment
- [ ] Technical terms defined
- [ ] Scope boundaries are explicit

### 5. Scoping Discipline
- [ ] Trade-offs are stated, not hidden
- [ ] Future possibilities noted but deferred (not crammed in)
- [ ] One coherent focus, not kitchen sink
- [ ] Out of scope items have rationale

### 6. Review Focus
The critical reviewer should challenge:
- Unchecked assumptions
- Sloppiness in reasoning
- Vague references
- Unjustified judgment calls
- False certainty masking uncertainty
- Technical claims without verification

## Implementation Requirements

### New Agents Needed
Each agent requires both an agent definition and a corresponding skill.

1. **iflow:internet-researcher**
   - Agent: `plugins/iflow-dev/agents/internet-researcher.md`
   - Skill: `plugins/iflow-dev/skills/researching-internet/SKILL.md`
   - Purpose: Searches web for best practices, prior art, standards
   - Tools: WebSearch, WebFetch

2. **iflow:codebase-explorer**
   - Agent: `plugins/iflow-dev/agents/codebase-explorer.md`
   - Skill: `plugins/iflow-dev/skills/exploring-codebase/SKILL.md`
   - Purpose: Analyzes existing patterns, constraints, related code
   - Tools: Glob, Grep, Read

3. **iflow:skill-searcher**
   - Agent: `plugins/iflow-dev/agents/skill-searcher.md`
   - Skill: `plugins/iflow-dev/skills/searching-skills/SKILL.md`
   - Purpose: Finds relevant existing skills/capabilities in the plugin
   - Tools: Glob, Grep, Read

4. **iflow:prd-reviewer**
   - Agent: `plugins/iflow-dev/agents/prd-reviewer.md`
   - Skill: `plugins/iflow-dev/skills/reviewing-prd/SKILL.md`
   - Purpose: Critical review of PRD drafts (challenges assumptions, identifies gaps, flags false certainty)
   - Tools: Read

### Skill Changes
- Modify `brainstorming/SKILL.md` to implement the 6-stage flow
- Update output format from `brainstorm.md` to PRD format
- Add subagent orchestration for research and review stages

## Open Questions

- How should reworking previous PRDs integrate with this flow?
- Should there be a maximum number of review/correct cycles?
- How do research subagents report failures (e.g., no relevant codebase patterns found)?

## Next Steps

Ready for /iflow:create-feature to define implementation requirements.

---

## References

- [Atlassian PRD Guide](https://www.atlassian.com/agile/product-management/requirements)
- [ProductPlan PRD Glossary](https://www.productplan.com/glossary/product-requirements-document/)
- [PRDs for AI Coding Agents](https://medium.com/@haberlah/how-to-write-prds-for-ai-coding-agents-d60d72efb797)
