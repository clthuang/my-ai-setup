---
name: verifying-before-completion
description: Requires verification evidence before any completion claims. Use when about to claim work is complete, fixed, or passing.
---

# Verification Before Completion

Claiming work is complete without verification is dishonesty, not efficiency.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

Before claiming any status:

1. **IDENTIFY:** What command proves this claim?
2. **RUN:** Execute the FULL command (fresh, complete)
3. **READ:** Full output, check exit code, count failures
4. **VERIFY:** Does output confirm the claim?
5. **ONLY THEN:** Make the claim with evidence

Skip any step = lying, not verifying.

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test output: 0 failures | "Should pass", previous run |
| Build succeeds | Build output: exit 0 | Linter passing |
| Bug fixed | Test symptom: passes | "Code changed" |
| Requirements met | Line-by-line check | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification
- About to commit/push without verification
- Trusting agent success reports
- Thinking "just this once"

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Agent said success" | Verify independently |

## Key Pattern

```
✅ [Run test] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**No shortcuts for verification.** Run the command. Read the output. THEN claim the result.
