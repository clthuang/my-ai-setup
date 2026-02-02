---
name: reviewing-artifacts
description: Comprehensive quality criteria for PRD and spec artifact review. Use when reviewing artifact quality or validating phase transitions.
---

# Reviewing Artifacts

Quality criteria and review checklists for workflow artifacts.

## PRD Quality Criteria

### 1. Problem Definition

- [ ] Problem statement is specific and bounded
- [ ] Target user/persona identified
- [ ] Impact/value proposition clear
- [ ] Not a solution masquerading as a problem

### 2. Requirements Completeness

- [ ] Functional requirements enumerated
- [ ] Non-functional requirements stated (performance, security, etc.)
- [ ] Constraints documented (technical, business, regulatory)
- [ ] Success criteria are measurable

### 3. Evidence Standards

- [ ] Technical claims verified against codebase
- [ ] External claims have sources
- [ ] Assumptions explicitly labeled
- [ ] "Should work" replaced with "Verified at {location}" or "Assumption"

### 4. Intellectual Honesty

- [ ] Uncertainty acknowledged, not hidden
- [ ] Trade-offs stated explicitly
- [ ] Judgment calls labeled with reasoning
- [ ] No false certainty

### 5. Scope Discipline

- [ ] Clear boundaries (in scope / out of scope)
- [ ] Future possibilities deferred, not crammed in
- [ ] One coherent focus
- [ ] Out of scope items have rationale

---

## Spec Quality Criteria

### 1. Problem Precision

- [ ] Problem statement is ONE sentence
- [ ] Specific enough to test against
- [ ] No implementation details leaked
- [ ] Who is affected is explicit

### 2. Success Criteria Quality

- [ ] Each criterion is measurable
- [ ] Each criterion is independently testable
- [ ] Criteria cover all key outcomes
- [ ] No vague language ("fast", "good", "easy")

### 3. Scope Boundaries

- [ ] In Scope items are exhaustive
- [ ] Out of Scope items prevent scope creep
- [ ] No ambiguity about what's included
- [ ] Scope aligns with PRD (if exists)

### 4. Acceptance Criteria

- [ ] Given/When/Then format for each feature aspect
- [ ] Covers happy path
- [ ] Covers key error paths
- [ ] Specific enough to write tests from

### 5. Implementation Independence

- [ ] Describes WHAT, not HOW
- [ ] No technology choices embedded
- [ ] No architecture decisions
- [ ] Could be implemented multiple ways

### 6. Traceability

- [ ] Each requirement has a unique ID or clear name
- [ ] Dependencies are explicit
- [ ] Open questions are listed (not hidden)

---

## Severity Classification

| Issue Type | Severity | Blocks? |
|------------|----------|---------|
| Missing required section | blocker | Yes |
| Vague/untestable criterion | blocker | Yes |
| Scope ambiguity | blocker | Yes |
| Implementation detail leaked | warning | No |
| Missing edge case coverage | warning | No |
| Style/formatting issue | note | No |

---

## Usage by Chain Reviewer

When chain-reviewer validates **prd.md -> spec.md** (brainstorm -> specify transition):

1. Apply "PRD Quality Criteria" checklist
2. Focus on: Problem precision, Evidence standards, Scope discipline
3. Mark issues as blocker/warning/note
4. Summarize: "Can specify phase proceed with this PRD?"

When chain-reviewer validates **spec.md -> design.md** (specify -> design transition):

1. Apply "Spec Quality Criteria" checklist
2. Focus on: Problem precision, Success criteria, Acceptance criteria
3. Mark issues as blocker/warning/note
4. Summarize: "Can design phase proceed with this spec?"

---

## Quick Reference

**PRD must answer:** What problem? Who has it? Why solve it now? What's in/out?

**Spec must answer:** What exactly? How do we know it's done? What's the scope?

**Both must avoid:** False certainty, scope creep, implementation details.
