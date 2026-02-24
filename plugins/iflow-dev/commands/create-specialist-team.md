---
description: Create ephemeral specialist teams for complex tasks
argument-hint: <task description>
---

# /iflow-dev:create-specialist-team Command

Create and deploy a team of specialists for a complex task.

## No Arguments

If no argument provided:

Display brief usage:
```
Usage: /iflow-dev:create-specialist-team <task description>

Creates an ephemeral team of specialists to analyze or implement a complex task.

Examples:
  /iflow-dev:create-specialist-team "analyze auth security and suggest improvements"
  /iflow-dev:create-specialist-team "research caching strategies for our API"
  /iflow-dev:create-specialist-team "implement and test a rate limiter"
```

## Main Flow

### Step 1: Analyze Task

Parse the task description to determine:

1. **Domains** — what areas of expertise are needed (security, performance, testing, etc.)
2. **Capabilities** — what tools are required (read-only analysis vs implementation)
3. **Team size** — how many specialists (cap at 5)
4. **Coordination pattern**:
   - **Sequential pipeline** — output of one feeds into next (e.g., analyze → implement → test)
   - **Parallel fan-out** — independent specialists working simultaneously (e.g., security + performance + quality review)

### Step 2: Select Templates and Confirm

Available templates (locate via two-location Glob: `~/.claude/plugins/cache/*/iflow*/*/skills/creating-specialist-teams/references/`, fallback `plugins/*/skills/creating-specialist-teams/references/`):

| Template | Best For |
|----------|----------|
| `code-analyzer.template.md` | Read-only code analysis, pattern detection, structural findings |
| `research-specialist.template.md` | Evidence gathering, best practices research, comparisons |
| `implementation-specialist.template.md` | Writing code with TDD, making changes |
| `domain-expert.template.md` | Advisory analysis, architectural recommendations |
| `test-specialist.template.md` | Test coverage, edge cases, test implementation |

Map task domains to templates. Assign specific focus areas to each specialist.

**Present team for approval:**
```
AskUserQuestion:
  questions: [{
    question: "Proposed team for '{task}'. Deploy?",
    header: "Team",
    options: [
      { label: "Deploy", description: "{n} specialists: {list with roles}" },
      { label: "Customize", description: "Modify team composition" },
      { label: "Cancel", description: "Abort" }
    ],
    multiSelect: false
  }]
```

**If user selects "Customize":**
```
AskUserQuestion:
  questions: [{
    question: "Select specialists for this team:",
    header: "Customize",
    options: [
      { label: "Code Analyzer", description: "Read-only analysis of codebase patterns" },
      { label: "Research Specialist", description: "Web research for best practices" },
      { label: "Implementation Specialist", description: "Write code with TDD" },
      { label: "Domain Expert", description: "Advisory recommendations" }
    ],
    multiSelect: true
  }]
```
Then re-confirm the customized team.

**YOLO override:** If args contain `[YOLO_MODE]`, skip team approval and auto-deploy recommended team.

### Step 3: Inject Context

For each selected template:

1. Read the scaffold template via two-location Glob:
   ```
   Glob ~/.claude/plugins/cache/*/iflow*/*/skills/creating-specialist-teams/references/{type}.template.md — read first match.
   Fallback: Read plugins/iflow-dev/skills/creating-specialist-teams/references/{type}.template.md (dev workspace).
   ```

2. Gather codebase context relevant to the task:
   - Glob for files related to the task keywords
   - Grep for relevant code patterns
   - Limit context to most relevant 10-15 files

3. Fill template placeholders:
   - `{TASK_DESCRIPTION}` — the specific assignment for this specialist
   - `{CODEBASE_CONTEXT}` — relevant files and patterns found
   - `{SUCCESS_CRITERIA}` — what constitutes successful output
   - `{OUTPUT_FORMAT}` — structured format for findings
   - `{SCOPE_BOUNDARIES}` — what the specialist should NOT do

### Step 4: Deploy Specialists

Dispatch each specialist via generic-worker:

```
Task({
  subagent_type: "iflow-dev:generic-worker",
  model: "opus",
  description: "{role}: {brief assignment}",
  prompt: "{filled template content}"
})
```

**Coordination patterns:**
- **Parallel fan-out**: Dispatch specialists in batches of `max_concurrent_agents` (from session context, default 5). If team size exceeds the limit, dispatch in waves — wait for each wave to complete before the next.
- **Sequential pipeline**: Dispatch first specialist, wait for result, include result in next specialist's context

### Step 5: Synthesize Results

After all specialists complete:

1. Collect outputs from all specialists
2. Present combined results:

```
## Specialist Team Results

### Task: {original description}
### Team: {list of specialists}

{For each specialist:}
#### {Role} Findings
{specialist output}

---

### Synthesis
{Brief summary of key findings across all specialists}

### Recommended Next Steps
{Actionable follow-ups based on combined findings}
```

3. Offer follow-up:
```
AskUserQuestion:
  questions: [{
    question: "What would you like to do with these results?",
    header: "Follow-up",
    options: [
      { label: "Implement", description: "Act on the recommendations" },
      { label: "Deep dive", description: "Investigate specific findings" },
      { label: "Done", description: "Results are sufficient" }
    ],
    multiSelect: false
  }]
```
