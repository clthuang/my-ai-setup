---
description: Intelligent task routing - discover agents and delegate work
argument-hint: [help|mode [manual|aware|yolo]|orchestrate <desc>|<request>]
---

# /iflow-dev:secretary Command

Route requests to the most appropriate specialist agent.

## Subcommand Routing

Parse the first word of the argument:
- `help` → Help subcommand
- `mode` → Mode subcommand
- `orchestrate` or `continue` → Orchestrate subcommand
- anything else → Request handler (performs routing inline)
- no argument → Brief usage

## Subcommand: help

If argument is `help`:

Display usage instructions:

```
Secretary - Intelligent Task Routing

Usage:
  /iflow-dev:secretary help              Show this help
  /iflow-dev:secretary mode              Show current activation mode
  /iflow-dev:secretary mode <mode>       Set activation mode (manual|aware|yolo)
  /iflow-dev:secretary orchestrate <desc> Run full workflow autonomously (YOLO only)
  /iflow-dev:secretary <request>         Route request to best agent

Modes:
  manual   - Only activates via explicit /secretary command (default)
  aware    - Injects routing hints at session start
  yolo     - Fully autonomous: runs entire workflow without pausing

Orchestration (YOLO mode only):
  /iflow-dev:secretary orchestrate build a login system
  /iflow-dev:secretary continue          Resume from last completed phase

Examples:
  /iflow-dev:secretary review auth for security issues
  /iflow-dev:secretary help me improve test coverage
  /iflow-dev:secretary find and fix performance problems

The secretary will:
1. Discover available agents across all plugins
2. Interpret your request (ask clarifying questions if needed)
3. Match to the best specialist agent with mode recommendation
4. Validate routing via reviewer (for uncertain matches)
5. Confirm with you before delegating
6. Execute the delegation and report results
```

## Subcommand: mode

If argument is `mode` (no value):

1. Read config from `.claude/iflow-dev.local.md`
2. If config not found: Report "Config not found. Using defaults (manual mode)."
3. If config found: Extract and display `activation_mode` value

Display format:
```
Current mode: {mode}

Available modes:
  manual - Only activates via explicit /secretary command
  aware  - Injects routing hints at session start
  yolo   - Fully autonomous: runs entire workflow without pausing
```

If argument is `mode <value>` where value is `manual`, `aware`, or `yolo`:

1. Check if `.claude/iflow-dev.local.md` exists
2. If exists:
   - Use Edit tool to update `activation_mode` line
   - Report "Mode updated to {value}"
3. If not exists:
   - Create `.claude/` directory if needed (via Bash: mkdir -p)
   - Use Write tool to create config with specified mode:
     ```
     ---
     activation_mode: {value}
     ---
     ```
   - Report "Config created at .claude/iflow-dev.local.md with mode: {value}"

If argument is `mode <invalid>`:

Report error:
```
Invalid mode: {invalid}

Valid modes are:
  manual - Only activates via explicit /secretary command
  aware  - Injects routing hints at session start
  yolo   - Fully autonomous: runs entire workflow without pausing
```

## Subcommand: orchestrate

If argument starts with `orchestrate` or `continue`:

### Prerequisites

1. Read `.claude/iflow-dev.local.md`
2. Extract `activation_mode`
3. If mode is NOT `yolo`:
   ```
   Orchestration requires YOLO mode.

   Current mode: {mode}
   Set YOLO mode first: /iflow-dev:secretary mode yolo
   ```
   Stop here.

### Detect Workflow State

1. Glob `docs/features/*/.meta.json`
2. Read each file, look for `"status": "active"`
3. If active feature found:
   - Extract `lastCompletedPhase` from .meta.json
   - Report: "Active feature: {id}-{slug}, last phase: {lastCompletedPhase}"
4. If no active feature AND description provided after "orchestrate":
   - This is a new feature request, start from brainstorm
5. If no active feature AND no description (bare `orchestrate` or `continue`):
   ```
   No active feature found and no description provided.

   Usage:
     /iflow-dev:secretary orchestrate <description>  Start new feature
     /iflow-dev:secretary continue                   Resume active feature
   ```
   Stop here.

### Determine Next Command

| lastCompletedPhase | Next Command |
|---|---|
| (no active feature) | iflow-dev:brainstorm |
| null (feature exists, no phases) | iflow-dev:specify |
| brainstorm | iflow-dev:specify |
| specify | iflow-dev:design |
| design | iflow-dev:create-plan |
| create-plan | iflow-dev:create-tasks |
| create-tasks | iflow-dev:implement |
| implement | iflow-dev:finish-feature |
| finish-feature | Already complete — report "Feature already completed." and stop |

### Execute in Main Session

Invoke the next command via Skill (NOT Task) so it runs in the main session and the user sees all output:

```
Skill({
  skill: "iflow-dev:{next-command}",
  args: "[YOLO_MODE] {description or feature context}"
})
```

The existing command chaining and YOLO overrides handle everything from here. Each phase:
- Auto-selects at AskUserQuestion prompts (YOLO overrides in workflow-transitions)
- Runs full executor-reviewer cycles (all reviewer agents still execute)
- Auto-invokes the next command at completion

### Hard Stops

The chain breaks and reports to user when:
- **Circuit breaker**: 5 review iterations without approval in implementation
- **Git merge conflict**: Cannot auto-resolve in /finish-feature
- **Hard prerequisite failure**: Missing design.md (blocks create-plan), plan.md (blocks create-tasks), spec.md or tasks.md (blocks implement)
- **Pre-merge validation failure**: 3 fix attempts exhausted

These are handled by the individual commands. The orchestrator does NOT need to catch them — the Skill invocation naturally surfaces them.

## Subcommand: <request>

If argument is anything other than `help`, `mode`, `orchestrate`, or `continue`:

> **Routing boundary directive**
>
> During steps 1-6, you are ROUTING, not executing. Do not use Edit, Write, or Bash.
> Only use Read, Glob, Grep for discovery, AskUserQuestion for clarification,
> and Task for secretary-reviewer. Step 7 (DELEGATE) lifts this restriction.

**Read config first** — Read `.claude/iflow-dev.local.md`. Extract `activation_mode`. If `yolo`, set `[YOLO_MODE]` flag.

**YOLO Mode Overrides** (apply when `[YOLO_MODE]` is active):
- Step 2 (CLARIFY): Skip — infer intent from request text
- Step 5 (REVIEW): Skip reviewer gate
- Step 6 (RECOMMEND): Auto-select highest-confidence match in Standard mode
- Step 7 (DELEGATE): If workflow pattern detected, redirect to orchestrate subcommand handler directly. Otherwise proceed immediately.

---

### Step 1: DISCOVER

Build an index of available agents:

```
1. Primary: Glob ~/.claude/plugins/cache/*/*/agents/*.md
   - For each file: extract plugin name from path, read frontmatter (including `model` field), build agent record

2. Fallback (if step 1 found 0 agents): Glob plugins/*/agents/*.md
   - Process same as step 1

3. Merge and deduplicate by plugin:name

4. If still 0 agents: proceed to Step 4 — do NOT error out.
   Keyword matching (Specialist Fast-Path + Workflow Pattern Recognition)
   provides routing without filesystem discovery.
```

**YAML Frontmatter Parsing:**
- Find content between first two "---" lines
- For each line: split on first ":" to get key/value
- Handle arrays (lines starting with "- " or bracket notation)
- Skip agents with malformed frontmatter

---

### Step 2: CLARIFY

Analyze the user request for ambiguity:

**Ambiguity Signals:**
- Vague terms: "better", "improve", "fix", "help", "something"
- Multiple domains mentioned: "auth and UI", "tests and docs"
- Missing action verb
- Missing scope/target

**If Ambiguous:**
1. Generate clarifying questions (max 3)
2. Use AskUserQuestion with concrete options where possible
3. Incorporate answers to form clarified intent

**If Clear:**
- Proceed directly to Step 3

**Example Clarification:**
```
AskUserQuestion:
  questions: [{
    question: "What aspect of 'improve the code' are you most interested in?",
    header: "Clarification",
    options: [
      { label: "Security", description: "Check for vulnerabilities" },
      { label: "Performance", description: "Optimize for speed/memory" },
      { label: "Quality", description: "Clean code, best practices" },
      { label: "All of the above", description: "Comprehensive review" }
    ],
    multiSelect: false
  }]
```

**Clarification Timeout/Fallback:**
- Track clarification attempts (max 3)
- If user provides empty/unclear response, re-prompt with simpler options
- After 3 failed attempts or timeout, proceed with best-effort interpretation:
  1. Extract most concrete terms from original request
  2. Match against agent descriptions using keyword overlap
  3. If any agent scores >50%, recommend it with disclaimer: "Based on limited context, I suggest..."
  4. If no agent >50%, report "Unable to interpret request. Please try rephrasing or use a specific agent."

---

### Step 3: TRIAGE

When the clarified intent suggests brainstorming (creative exploration, new ideas, problem analysis), run triage:

1. Read the archetypes reference file:
   - Glob `~/.claude/plugins/cache/*/iflow*/*/skills/brainstorming/references/archetypes.md` — use first match
   - Fallback: Glob `plugins/*/skills/brainstorming/references/archetypes.md`
   - If not found: skip triage, proceed to Step 4 with no archetype context
2. Extract keywords from the clarified user intent
3. Match against each archetype's signal words — count hits per archetype
4. Select archetype with highest overlap (ties: prefer domain-specific archetype)
5. If zero matches: default to "exploring-an-idea"
6. Load the archetype's default advisory team from the reference
7. Optionally override team if model judgment warrants it (explain reasoning)
8. Store `archetype` and `advisory_team` for Step 7

Triage results are only used when Step 7 routes to brainstorming. Otherwise discarded.

---

### Step 4: MATCH

Match clarified intent to discovered agents. Check patterns in this priority order:

#### Specialist Fast-Path

Before running semantic matching, check against known specialist patterns:

| Pattern (case-insensitive) | Agent | Confidence |
|---|---|---|
| "review" + ("security" / "vulnerability" / "owasp") | iflow-dev:security-reviewer | 95% |
| "review" + ("code quality" / "clean code" / "best practice") | iflow-dev:code-quality-reviewer | 95% |
| "review" + ("implementation" / "against spec" / "against requirements") | iflow-dev:implementation-reviewer | 95% |
| "review" + ("design" / "architecture") | iflow-dev:design-reviewer | 95% |
| "review" + ("spec" / "requirements" / "acceptance criteria") | iflow-dev:spec-reviewer | 95% |
| "review" + ("plan" / "implementation plan") | iflow-dev:plan-reviewer | 95% |
| "review" + ("data" / "analysis" / "statistical" / "methodology") | iflow-dev:ds-analysis-reviewer | 95% |
| "review" + ("notebook" / "pandas" / "sklearn" / "DS code") | iflow-dev:ds-code-reviewer | 95% |
| "simplify" / "reduce complexity" / "clean up code" | iflow-dev:code-simplifier | 95% |
| "explore" + ("codebase" / "code" / "patterns" / "how does") | iflow-dev:codebase-explorer | 95% |
| "deepen tests" / "add edge case tests" / "test deepening" | iflow-dev:test-deepener | 95% |

**Fast-path rules:**
1. Match is keyword overlap, not semantic — must hit the exact pattern
2. If fast-path matches → skip Discovery, skip semantic matching, skip reviewer gate
3. Go directly to Step 6 (Recommender) with the matched agent at 95% confidence
4. User still confirms via AskUserQuestion before delegation (unless YOLO)

**If no fast-path match** → proceed to remaining matching below.

#### Workflow Pattern Recognition

| Pattern Keywords | Workflow |
|-----------------|----------|
| "new feature", "add capability", "create feature" | iflow-dev:brainstorm |
| "brainstorm", "explore", "ideate", "what if", "think about" | iflow-dev:brainstorm |
| "add command", "add hook", "add agent", "add skill", "create component", "modify plugin", "new command", "new hook", "new agent", "new skill", "extend plugin" | iflow-dev:brainstorm |
| "design", "architecture" | iflow-dev:design |
| "specify", "spec", "requirements" | iflow-dev:specify |

**Development Task Heuristic:**
If the request describes modifying, adding to, or extending the plugin system (commands, hooks, agents, skills, workflows), treat it as a feature request → route via Workflow Guardian below.

#### Investigative Question Detection

| Pattern Keywords | Route To |
|-----------------|----------|
| "why", "what caused", "how did this happen", "what went wrong", "how come", "what's causing", "what broke" | investigation-agent |
| "investigate", "debug", "trace", "analyze failure", "diagnose" | investigation-agent |
| Any of the above + "fix", "resolve", "prevent", "stop this from" | rca-investigator |

**Priority rule:** If both investigation and action keywords are present ("why did X break and how do I fix it?"), "fix"/"resolve"/"prevent" takes precedence → route to `rca-investigator`. Default to `investigation-agent` when unclear.

If workflow_match or investigative match detected, set in output and skip semantic agent matching.

#### Workflow Guardian

When a workflow pattern is detected (feature request, "build X", "implement X", "plan X", "code X"), determine the correct phase:

1. Glob `docs/features/*/.meta.json`
2. Read each file, look for `"status": "active"`
3. If NO active feature:
   - Route to `iflow-dev:brainstorm`
   - Explain: "No active feature. Starting from brainstorm to ensure proper research and planning."
4. If active feature found:
   - Extract `lastCompletedPhase` from .meta.json
   - Determine next phase:

     | lastCompletedPhase | Route to |
     |---|---|
     | null (feature created, no phases done) | iflow-dev:brainstorm |
     | brainstorm | iflow-dev:specify |
     | specify | iflow-dev:design |
     | design | iflow-dev:create-plan |
     | create-plan | iflow-dev:create-tasks |
     | create-tasks | iflow-dev:implement |
     | implement | iflow-dev:finish-feature |
     | finish-feature | Report: "Feature already completed." Stop. |

   - If the next phase matches what the user asked for → route with: "All prerequisite phases complete. Proceeding to {phase}."
   - If the next phase is earlier than what the user asked for → route to the next phase with: "You asked to {user request}, but {next phase} hasn't been completed yet. Routing to {next phase} to ensure proper planning."

Note: Workflow Guardian applies ONLY to workflow pattern matches. Specialist agent routing (reviews, investigations, debugging) bypasses this entirely.

#### Semantic Agent Matching

If no fast-path, workflow, or investigative match:

```
1. If agent count <= 20:
   - Consider all agents for semantic matching

2. If agent count > 20:
   - Extract keywords from user intent (nouns, verbs, domain terms)
   - Pre-filter to top 10 agents by keyword overlap with description
   - Consider these 10 for semantic matching

3. For each candidate agent:
   - Evaluate semantic fit between intent and agent description
   - Consider agent's tools vs task requirements
   - Assign confidence score (0-100)
   - Document reasoning

4. Return matches sorted by confidence
```

**Confidence Thresholds:**
- >70%: Strong match, recommend as primary
- 50-70%: Show as alternative option (but if best match is in this range, also show "no strong match" warning)
- <50%: Do not show

**Note:** If the BEST match is <70%, the "No Suitable Match" path in Step 7 applies.

#### Complexity Analysis

After matching, assess task complexity for mode recommendation:

| Signal | Points |
|--------|--------|
| Multi-file changes likely | +1 |
| Breaking changes / rewrite / migrate | +2 |
| Cross-domain (API + UI + tests) | +1 |
| Unclear scope / many unknowns | +1 |
| Simple / bounded / single file | -1 |

Score ≤ 1 → recommend Standard mode
Score ≥ 2 → recommend Full mode

---

### Step 5: REVIEW

Before presenting the recommendation, evaluate whether independent validation is needed:

**Skip reviewer when:**
- Best match confidence >85% AND match is a direct agent (not a workflow pattern)
- `[YOLO_MODE]` is active

**Invoke reviewer when:**
- Best match confidence <=85%
- Multiple matches within 15 points of each other (ambiguous ranking)
- Match is a workflow route (brainstorm/specify/design) — workflow misroutes are costlier

When invoking the reviewer:
```
Task({
  subagent_type: "iflow-dev:secretary-reviewer",
  model: "haiku",
  description: "Validate routing recommendation",
  prompt: "Discovered agents: {agent list with descriptions}\n
           User intent: {clarified intent}\n
           Routing: {recommended agent} ({confidence}% match)\n
           Mode recommendation: {Standard or Full}\n
           Validate agent fit, confidence calibration, missed specialists, and mode appropriateness."
})
```

**Handle reviewer response:**
- If reviewer approves → present original recommendation
- If reviewer objects (has blockers) → adjust recommendation per reviewer suggestions, note "adjusted after review"
- If reviewer fails or times out → proceed with original recommendation (note the failure internally)

---

### Step 6: RECOMMEND

Present recommendation to user for confirmation:

```
AskUserQuestion:
  questions: [{
    question: "Route to {agent} ({confidence}% match)?",
    header: "Routing",
    options: [
      { label: "Accept - Standard", description: "{reason} (recommended for this scope)" },
      { label: "Accept - Full", description: "{reason} (extra verification for complex tasks)" },
      // Include alternatives >50% (max 2):
      { label: "Use {alt-agent}", description: "Alternative: {alt-confidence}% match" },
      { label: "Cancel", description: "Abort request" }
    ],
    multiSelect: false
  }]
```

Pre-select the recommended mode based on complexity analysis (Standard or Full first in list).

**User Response Handling:**
- "Accept - Standard" → Proceed with Standard mode delegation
- "Accept - Full" → Proceed with Full mode delegation
- "Use {alt-agent}" → Proceed to delegation with selected alternative
- "Cancel" → Report "Request cancelled" and stop
- Custom text (via Other) → Parse as "plugin:agent" format, validate, delegate if valid

---

### Step 7: DELEGATE

Execute the delegation:

**If workflow_match:**
```
Skill({
  skill: "{workflow_match}",
  args: "{user_context}"
})
```

**When workflow_match is "iflow-dev:brainstorm" AND triage completed:**
```
Skill({
  skill: "iflow-dev:brainstorm",
  args: "{user_context} [ARCHETYPE: {archetype}] [ADVISORY_TEAM: {comma-separated advisor names}]"
})
```

**If agent match:**
```
Task({
  subagent_type: "{plugin}:{agent}",
  model: "{agent_record.model}",
  description: "Brief task summary",
  prompt: `
    Task: {clarified_intent}

    Context:
    {context_summary}

    Requirements:
    {specific_requirements}

    Return your findings in structured format.
  `
})
```

**After Delegation:**
- Present subagent results to user
- Offer follow-up options if appropriate

#### No Suitable Match (best match <50%)

When no existing agent scores above 50%, run scoping research:

1. Extract key terms from the clarified intent
2. Glob for files matching those terms — count results and identify directories
3. Grep for pattern spread — identify how many domains are involved

**Route based on scoping findings:**

| Finding | Route |
|---------|-------|
| Simple: ≤2 files affected, single domain, bounded task | Call `EnterPlanMode` directly — "This task is straightforward. Switching to plan mode." |
| Complex: 3+ files, multiple domains, or unfamiliar technology | Invoke `Skill({ skill: "iflow-dev:create-specialist-team", args: "{clarified_intent}" })` |

**Fallback:** If specialist team creation fails, offer retry/rephrase/cancel via AskUserQuestion.

---

### Error Handling

**Agent Parse Failure:**
- Log warning internally, skip the problematic file, continue with remaining agents

**Delegation Failure:**
```
AskUserQuestion:
  questions: [{
    question: "Delegation to {agent} failed: {error}. What would you like to do?",
    header: "Error",
    options: [
      { label: "Retry", description: "Try again with same agent" },
      { label: "Choose different agent", description: "Pick an alternative" },
      { label: "Cancel", description: "Abort request" }
    ],
    multiSelect: false
  }]
```

---

### Rules

1. **Always confirm before delegating** — Never auto-delegate without user approval (unless YOLO)
2. **Show reasoning** — Always explain why an agent was recommended
3. **Respect cancellation** — If user cancels, stop immediately
4. **Minimal context** — Pass only task-relevant information to subagents
5. **Handle errors gracefully** — Offer recovery options, don't crash
6. **Skip self** — Never recommend secretary as a match for tasks
7. **Prefer specialists** — Match to most specific agent, not generic workers
8. When no specialist matches (best <50%), run scoping research and auto-resolve (plan mode for simple, specialist team for complex)
9. **Never execute work** — Discover, interpret, match, delegate. Never investigate the user's problem, design solutions, or produce artifacts.

## No Arguments

If no argument provided:

Display brief usage:
```
Usage: /iflow-dev:secretary [help|mode|orchestrate|<request>]

Quick examples:
  /iflow-dev:secretary help
  /iflow-dev:secretary review auth module
  /iflow-dev:secretary mode yolo
  /iflow-dev:secretary orchestrate build a login system

Run /iflow-dev:secretary help for full documentation.
```
