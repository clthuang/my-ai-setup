# iflow Plugin

> Structured feature development workflow for Claude Code

## Installation

```bash
/plugin marketplace add clthuang/my-ai-setup
/plugin install iflow@my-local-plugins
```

## Quick Start

**Explore an idea:**
```bash
/iflow:brainstorm "your idea here"
```

**Build something:**
```bash
/iflow:create-feature "add user authentication"
```

Then follow the phases:
```
/iflow:specify → /iflow:design → /iflow:create-plan → /iflow:create-tasks → /iflow:implement → /iflow:finish-feature
```

## Commands

### Core Workflow

| Command | Purpose |
|---------|---------|
| `/iflow:brainstorm [topic]` | Explore ideas, produce evidence-backed PRD |
| `/iflow:create-feature <desc>` | Skip brainstorming, create feature directly |
| `/iflow:create-project <prd>` | Create project from PRD with AI-driven decomposition into features |
| `/iflow:specify` | Write requirements (spec.md) |
| `/iflow:design` | Define architecture (design.md) |
| `/iflow:create-plan` | Plan implementation (plan.md) |
| `/iflow:create-tasks` | Break into tasks (tasks.md) |
| `/iflow:implement` | Write code with TDD and review |
| `/iflow:finish-feature` | Merge, run retro, cleanup branch (iflow features) |
| `/iflow:wrap-up` | Wrap up implementation - review, retro, merge or PR |

### Utilities

| Command | Purpose |
|---------|---------|
| `/iflow:show-status` | See current feature progress |
| `/iflow:list-features` | List active features and branches |
| `/iflow:retrospect` | Run retrospective on a feature |
| `/iflow:add-to-backlog` | Capture ad-hoc ideas and todos |
| `/iflow:remember` | Capture a learning to long-term memory |
| `/iflow:cleanup-brainstorms` | Delete old brainstorm scratch files |
| `/iflow:secretary` | Intelligent task routing to agents (supports YOLO mode with orchestrate subcommand) |
| `/iflow:create-specialist-team` | Create ephemeral specialist teams for complex tasks |
| `/iflow:root-cause-analysis` | Investigate bugs systematically |
| `/iflow:review-ds-analysis <file>` | Review data analysis for statistical pitfalls |
| `/iflow:review-ds-code <file>` | Review DS Python code for anti-patterns |
| `/iflow:init-ds-project <name>` | Scaffold a new data science project |
| `/iflow:sync-cache` | Sync plugin source files to cache |
| `/iflow:yolo [on\|off]` | Toggle YOLO autonomous mode on or off |

## Skills

Skills are internal capabilities that Claude uses automatically during the workflow. You don't invoke them directly.

### Workflow Phases

| Skill | Purpose |
|-------|---------|
| brainstorming | Guides 6-stage process producing evidence-backed PRDs with advisory team analysis and structured problem-solving |
| structured-problem-solving | Applies SCQA framing and type-specific decomposition to problems during brainstorming |
| specifying | Creates precise specifications with acceptance criteria |
| designing | Creates design.md with architecture and contracts |
| decomposing | Orchestrates project decomposition pipeline (AI decomposition, review, feature creation) |
| planning | Produces plan.md with dependencies and ordering |
| breaking-down-tasks | Breaks plans into small, actionable tasks with dependency tracking |
| implementing | Guides phased TDD implementation (Interface → RED-GREEN → REFACTOR) |
| finishing-branch | Guides branch completion with PR or merge options |

### Quality & Review

| Skill | Purpose |
|-------|---------|
| reviewing-artifacts | Comprehensive quality criteria for PRD, spec, design, plan, and tasks |
| implementing-with-tdd | Enforces RED-GREEN-REFACTOR cycle with rationalization prevention |
| workflow-state | Defines phase sequence and validates transitions |
| workflow-transitions | Shared workflow boilerplate for phase commands (validation, branch check, commit, state update) |

### Investigation

| Skill | Purpose |
|-------|---------|
| systematic-debugging | Guides four-phase root cause investigation |
| root-cause-analysis | Structured 6-phase process for finding ALL contributing causes |

### Domain Knowledge

| Skill | Purpose |
|-------|---------|
| game-design | Game design frameworks, engagement/retention analysis, aesthetic direction, and feasibility evaluation |
| crypto-analysis | Crypto/Web3 frameworks for protocol comparison, DeFi taxonomy, tokenomics, trading strategies, MEV classification, market structure, and risk assessment |
| data-science-analysis | Data science frameworks for methodology assessment, pitfall analysis, and modeling approach recommendations (brainstorming domain) |
| writing-ds-python | Clean DS Python code: anti-patterns, pipeline rules, type hints, testing strategy, dependency management |
| structuring-ds-projects | Cookiecutter v2 project layout, notebook conventions, data immutability, the 3-use rule |
| spotting-ds-analysis-pitfalls | 15 common statistical pitfalls with diagnostic decision tree and mitigation checklists |
| choosing-ds-modeling-approach | Predictive vs causal modeling, method selection flowchart, Rubin/Pearl frameworks, hybrid approaches |

### Specialist Teams

| Skill | Purpose |
|-------|---------|
| creating-specialist-teams | Creates ephemeral specialist teams via template injection into generic-worker |

### Maintenance

| Skill | Purpose |
|-------|---------|
| retrospecting | Runs data-driven AORTA retrospective using retro-facilitator agent |
| updating-docs | Automatically updates documentation using agents |
| writing-skills | Applies TDD approach to skill documentation |
| detecting-kanban | Detects Vibe-Kanban and provides TodoWrite fallback |
| capturing-learnings | Guides model-initiated learning capture with configurable modes |

## Agents

Agents run as specialized subprocesses delegated by the workflow. They operate autonomously within their defined scope.

### Reviewers

| Agent | Purpose |
|-------|---------|
| brainstorm-reviewer | Reviews brainstorm artifacts with universal + type-specific criteria before promotion |
| code-quality-reviewer | Reviews implementation quality after spec compliance is confirmed |
| design-reviewer | Challenges design assumptions and finds gaps |
| implementation-reviewer | Validates implementation against full requirements chain |
| phase-reviewer | Validates artifact completeness for next phase transition |
| plan-reviewer | Skeptically reviews plans for failure modes and feasibility |
| prd-reviewer | Critically reviews PRD drafts for quality and completeness |
| project-decomposition-reviewer | Validates project decomposition quality (coverage, sizing, dependencies) |
| spec-reviewer | Reviews spec.md for testability, assumptions, and scope discipline |
| security-reviewer | Reviews implementation for security vulnerabilities |
| task-reviewer | Validates task breakdown quality for immediate executability |
| ds-analysis-reviewer | Reviews data analysis for statistical pitfalls, methodology issues, and conclusion validity |
| ds-code-reviewer | Reviews DS Python code for anti-patterns, pipeline quality, and best practices |

### Workers

| Agent | Purpose |
|-------|---------|
| implementer | Implements tasks with TDD and self-review discipline |
| project-decomposer | Decomposes project PRD into ordered features with dependencies and milestones |
| generic-worker | General-purpose implementation agent for mixed-domain tasks |
| documentation-writer | Writes and updates documentation based on research findings |
| code-simplifier | Identifies unnecessary complexity and suggests simplifications |

### Advisory

| Agent | Purpose |
|-------|---------|
| advisor | Applies strategic or domain advisory lens to brainstorm problems via template injection |

### Researchers

| Agent | Purpose |
|-------|---------|
| codebase-explorer | Analyzes codebase to find relevant patterns and constraints |
| documentation-researcher | Researches documentation state and identifies update needs |
| internet-researcher | Searches web for best practices, standards, and prior art |
| investigation-agent | Read-only research agent for context gathering |
| skill-searcher | Finds relevant existing skills for a given topic |

### Orchestration

| Agent | Purpose |
|-------|---------|
| secretary | Routes user requests to appropriate specialist agents via triage and independent review |
| secretary-reviewer | Validates secretary routing recommendations before presenting to user |
| rca-investigator | Finds all root causes through 6-phase systematic investigation |
| retro-facilitator | Runs data-driven AORTA retrospective with full intermediate context |

## Task Output Format

Tasks are organized for parallel execution:

- **Dependency Graph**: Mermaid diagram showing task relationships
- **Execution Strategy**: Groups tasks by parallel executability
- **Task Details**: Each task includes:
  - Dependencies and blocking relationships
  - Exact file paths and step-by-step instructions
  - Test commands or verification steps
  - Binary "done when" criteria
  - Time estimates (5-15 min each)

## File Structure

```
docs/
├── brainstorms/           # From /iflow:brainstorm
├── features/{id}-{name}/  # From /iflow:create-feature
│   ├── spec.md, design.md, plan.md, tasks.md
│   └── .meta.json         # Phase tracking
├── projects/{id}-{name}/  # From /iflow:create-project
│   ├── prd.md             # Project PRD
│   └── roadmap.md         # Dependency graph, milestones
├── retrospectives/        # From /iflow:retrospect
└── knowledge-bank/        # Accumulated learnings
```

## Autonomous Operation (YOLO Mode)

The secretary agent can drive the entire feature workflow autonomously:

```bash
# Enable YOLO mode
/iflow:secretary mode yolo

# Build a feature end-to-end without pausing
/iflow:secretary orchestrate build a validation helper for email format

# Resume from last completed phase
/iflow:secretary continue
```

In YOLO mode, the orchestrate subcommand chains all phases automatically:
`brainstorm -> specify -> design -> create-plan -> create-tasks -> implement -> finish-feature -> merge`

All quality gates (reviewers, phase validators) still run. YOLO mode only bypasses user confirmation prompts at phase transitions.

**Safety boundaries** (YOLO mode stops and reports):
- Implementation review fails after 5 iterations
- Git merge conflict on develop
- Pre-merge validation fails after 3 fix attempts
- Hard prerequisite failures (missing design.md, plan.md, spec.md, or tasks.md)

Resume after a stop: `/iflow:secretary continue`

**Modes:** `manual` (default) | `aware` (session hints) | `yolo` (fully autonomous)

## Memory

The plugin includes a semantic memory system that persists learnings across sessions. Two MCP tools are available:

| Tool | Purpose |
|------|---------|
| `store_memory` | Save a pattern, anti-pattern, or heuristic to long-term memory |
| `search_memory` | Search past learnings by topic using semantic similarity |

Memory entries are injected automatically at session start. See [README_FOR_DEV.md](./README_FOR_DEV.md) for setup and configuration.

## For Developers

See [README_FOR_DEV.md](./README_FOR_DEV.md) for:
- Component authoring (skills, agents, hooks)
- Architecture and design principles
- Release workflow
- Validation
