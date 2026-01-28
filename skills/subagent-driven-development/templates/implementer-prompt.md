# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent.

## Template

```markdown
Task tool (general-purpose):
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description

    [FULL TEXT of task from plan - paste it here, don't make subagent read file]

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    ## Before You Begin

    If you have questions about:
    - The requirements or acceptance criteria
    - The approach or implementation strategy
    - Dependencies or assumptions
    - Anything unclear in the task description

    **Ask them now.** Raise any concerns before starting work.

    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify implementation works
    4. Commit your work
    5. Self-review (see below)
    6. Report back

    Work from: [directory]

    **While you work:** If you encounter something unexpected or unclear,
    **ask questions**. It's always OK to pause and clarify.
    Don't guess or make assumptions.

    ## Before Reporting Back: Self-Review

    Review your work with fresh eyes. Ask yourself:

    **Completeness:**
    - Did I fully implement everything in the spec?
    - Did I miss any requirements?
    - Are there edge cases I didn't handle?

    **Quality:**
    - Is this my best work?
    - Are names clear and accurate?
    - Is the code clean and maintainable?

    **Discipline:**
    - Did I avoid overbuilding (YAGNI)?
    - Did I only build what was requested?
    - Did I follow existing patterns in the codebase?

    **Testing:**
    - Do tests actually verify behavior (not just mock behavior)?
    - Did I follow TDD if required?
    - Are tests comprehensive?

    If you find issues during self-review, fix them now before reporting.

    ## Report Format

    When done, report:
    - What you implemented
    - What you tested and test results
    - Files changed
    - Self-review findings (if any)
    - Any issues or concerns
```

## Usage Notes

1. **Paste full task text** - Don't make subagent read plan file
2. **Include context** - Subagent needs to understand where task fits
3. **Encourage questions** - Subagent should ask before guessing
4. **Require self-review** - Catches issues before spec review
5. **Specify working directory** - Clear about where to work

## Example

```markdown
Task tool (general-purpose):
  description: "Implement Task 3: Add validation hook"
  prompt: |
    You are implementing Task 3: Add validation hook

    ## Task Description

    Create a PreToolUse hook that validates file paths before Bash commands.
    The hook should:
    - Check if path exists
    - Verify path is within project directory
    - Block commands targeting system directories

    ## Context

    This is part of the security hardening initiative. Tasks 1-2 added the
    hook infrastructure. This task uses that infrastructure for validation.

    ## Before You Begin

    [... rest of template ...]
```
