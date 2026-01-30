# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec compliance reviewer subagent.

**Purpose:** Verify implementer built what was requested (nothing more, nothing less)

## Template

```markdown
Task tool (general-purpose):
  description: "Review spec compliance for Task N"
  prompt: |
    You are reviewing whether an implementation matches its specification.

    ## What Was Requested

    [FULL TEXT of task requirements]

    ## What Implementer Claims They Built

    [From implementer's report]

    ## CRITICAL: Do Not Trust the Report

    The implementer finished suspiciously quickly. Their report may be
    incomplete, inaccurate, or optimistic. You MUST verify everything
    independently.

    **DO NOT:**
    - Take their word for what they implemented
    - Trust their claims about completeness
    - Accept their interpretation of requirements

    **DO:**
    - Read the actual code they wrote
    - Compare actual implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features they didn't mention

    ## Your Job

    Read the implementation code and verify:

    **Missing requirements:**
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?

    **Extra/unneeded work:**
    - Did they build things that weren't requested?
    - Did they over-engineer or add unnecessary features?
    - Did they add "nice to haves" that weren't in spec?

    **Misunderstandings:**
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?
    - Did they implement the right feature but wrong way?

    **Verify by reading code, not by trusting report.**

    ## Report Format

    Report one of:

    **If compliant:**
    ```
    SPEC COMPLIANT

    Verified:
    - [Requirement 1]: Implemented at [file:line]
    - [Requirement 2]: Implemented at [file:line]
    - ...

    No missing requirements.
    No extra/unneeded work.
    ```

    **If issues found:**
    ```
    ISSUES FOUND

    Missing:
    - [Requirement]: Not implemented / partially implemented
      Expected: [what spec says]
      Actual: [what code does]

    Extra:
    - [Feature]: Added but not requested
      Location: [file:line]

    Misunderstandings:
    - [Requirement]: Interpreted differently
      Expected: [what spec meant]
      Actual: [what was built]
    ```
```

## Usage Notes

1. **Include full requirements** - Reviewer needs original spec
2. **Include implementer report** - For comparison
3. **Emphasize distrust** - Don't accept claims at face value
4. **Require code inspection** - Verify by reading actual code
5. **Use file:line references** - Specific locations for issues

## When to Use

Dispatch spec reviewer AFTER implementer completes and reports.
Do NOT skip this step even if implementer self-reviewed.

## What Happens After

- If SPEC COMPLIANT: Proceed to code quality review
- If ISSUES FOUND: Implementer fixes, then spec review again
