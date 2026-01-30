---
name: verifying
description: Runs phase-appropriate verification with fresh perspective. Use when checking phase quality. Reports issues by severity with fix suggestions.
---

# Verification

Check work quality with fresh perspective.

## Determine Current Phase

Read feature folder to determine what to verify:
- brainstorm.md exists, no spec.md → Verify brainstorm
- spec.md exists, no design.md → Verify spec
- design.md exists, no plan.md → Verify design
- plan.md exists, no tasks.md → Verify plan
- tasks.md exists, implementation incomplete → Verify tasks
- Implementation complete → Quality review

## Verification Checklists

### Brainstorm Verification
- [ ] Problem clearly stated?
- [ ] Multiple options explored?
- [ ] Decision rationale documented?
- [ ] Open questions captured?

### Spec Verification
- [ ] Each criterion testable?
- [ ] No implementation details (what, not how)?
- [ ] No unnecessary features (YAGNI)?
- [ ] Scope clearly bounded?

### Design Verification
- [ ] KISS: Simplest approach?
- [ ] Interfaces defined before implementation?
- [ ] No over-engineering?
- [ ] Dependencies identified?

### Plan Verification
- [ ] Dependencies mapped correctly?
- [ ] Order makes sense?
- [ ] All spec items covered?
- [ ] Risks identified?

### Tasks Verification
- [ ] Each task small (5-15 min)?
- [ ] Each task independently testable?
- [ ] TDD steps included?
- [ ] All plan items covered?

### Quality Review (Post-Implementation)
- [ ] Code is readable?
- [ ] No dead code?
- [ ] Tests pass?
- [ ] No obvious bugs?
- [ ] KISS and YAGNI followed?

## Report Format

```
Verification: {phase}

🔴 Blockers (must fix):
- {Issue}: {description}
  Fix: {suggestion}

🟡 Warnings (should fix):
- {Issue}: {description}
  Fix: {suggestion}

🟢 Notes (consider):
- {Observation}

Result: {PASS / NEEDS FIXES}
```

## Circuit Breaker

Track verification attempts per phase.
After 3 failures on same phase:

```
Verification has failed 3 times for {phase}.

This usually indicates:
- Requirements unclear → Loop back to brainstorm
- Approach flawed → Reconsider design
- Criteria too strict → Review expectations

What would you like to do?
1. Try fixing issues again
2. Loop back to earlier phase
3. Proceed anyway (your judgment)
4. Discuss with me
```

## Completion

If PASS: "Verification passed. Ready for next phase."
If NEEDS FIXES: "Issues found. Fix and re-run /verify, or proceed anyway."
