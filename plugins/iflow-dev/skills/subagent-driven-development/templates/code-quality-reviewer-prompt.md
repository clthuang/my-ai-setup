# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

## Template

```markdown
Task tool (general-purpose):
  description: "Review code quality for Task N"
  prompt: |
    You are reviewing the code quality of an implementation.

    **Note:** Spec compliance has already been verified. This review
    focuses on HOW the code is written, not WHAT it does.

    ## Implementation Summary

    [From implementer's report - what was built]

    ## Files to Review

    [List of files changed]

    ## Your Job

    Review the implementation for quality:

    **Code Quality:**
    - Is the code readable and well-organized?
    - Are names clear and descriptive?
    - Is there unnecessary complexity?
    - Are there code smells or anti-patterns?

    **Architecture:**
    - Does it follow existing patterns in the codebase?
    - Is the structure appropriate for the task?
    - Are responsibilities properly separated?

    **Testing:**
    - Are tests comprehensive?
    - Do tests verify behavior (not mock behavior)?
    - Are there missing test cases?
    - Are tests readable and maintainable?

    **Maintainability:**
    - Would another developer understand this code?
    - Are there potential future issues?
    - Is error handling appropriate?

    ## Report Format

    ```
    ## Code Quality Review

    ### Strengths
    - [What was done well]

    ### Issues

    **Critical** (must fix):
    - [Issue]: [Description]
      Location: [file:line]
      Fix: [Suggestion]

    **Important** (should fix):
    - [Issue]: [Description]
      Location: [file:line]
      Fix: [Suggestion]

    **Minor** (consider):
    - [Issue]: [Description]

    ### Assessment

    [ ] APPROVED - Ready to merge
    [ ] APPROVED WITH NOTES - Minor issues, can merge
    [ ] NEEDS CHANGES - Important/Critical issues must be fixed
    ```
```

## Issue Categories

| Category | Criteria | Action |
|----------|----------|--------|
| Critical | Bugs, security issues, data loss risk | Must fix before merge |
| Important | Poor patterns, missing tests, tech debt | Should fix |
| Minor | Style, naming, minor improvements | Consider fixing |

## Usage Notes

1. **Only after spec review passes** - Quality review assumes spec is met
2. **Focus on HOW not WHAT** - Spec compliance already verified
3. **Use file:line references** - Specific locations for issues
4. **Provide fix suggestions** - Don't just identify problems
5. **Clear assessment** - Approved / Needs Changes

## What Happens After

- If APPROVED: Task complete, proceed to next task
- If NEEDS CHANGES: Implementer fixes, then quality review again

## Integration with Agents

This template corresponds to the `code-quality-reviewer` agent.
The agent has these guidelines built into its system prompt.

When dispatching:
```markdown
Task tool (code-quality-reviewer):
  description: "Code quality review for Task N"
  prompt: |
    Review the implementation of Task N.

    Files changed: [list]
    Summary: [what was built]
```
