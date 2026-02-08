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
/iflow:specify → /iflow:design → /iflow:create-plan → /iflow:create-tasks → /iflow:implement → /iflow:finish
```

## Commands

### Core Workflow

| Command | Purpose |
|---------|---------|
| `/iflow:brainstorm [topic]` | Explore ideas, produce evidence-backed PRD |
| `/iflow:create-feature <desc>` | Skip brainstorming, create feature directly |
| `/iflow:specify` | Write requirements (spec.md) |
| `/iflow:design` | Define architecture (design.md) |
| `/iflow:create-plan` | Plan implementation (plan.md) |
| `/iflow:create-tasks` | Break into tasks (tasks.md) |
| `/iflow:implement` | Write code with TDD and review |
| `/iflow:finish` | Merge, run retro, cleanup branch |

### Utilities

| Command | Purpose |
|---------|---------|
| `/iflow:show-status` | See current feature progress |
| `/iflow:list-features` | List active features and branches |
| `/iflow:retrospect` | Run retrospective on a feature |
| `/iflow:add-to-backlog` | Capture ad-hoc ideas and todos |
| `/iflow:cleanup-brainstorms` | Delete old brainstorm scratch files |
| `/iflow:secretary` | Intelligent task routing to agents |
| `/iflow:root-cause-analysis` | Investigate bugs systematically |
| `/iflow:sync-cache` | Sync plugin source files to cache |

## Skills

Skills are internal capabilities that Claude uses automatically during the workflow. You don't invoke them directly.

### Workflow Phases

| Skill | Purpose |
|-------|---------|
| brainstorming | Guides 7-stage process producing evidence-backed PRDs with optional structured problem-solving and domain skill enrichment |
| structured-problem-solving | Applies SCQA framing and type-specific decomposition to problems during brainstorming |
| specifying | Creates precise specifications with acceptance criteria |
| designing | Creates design.md with architecture and contracts |
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

### Maintenance

| Skill | Purpose |
|-------|---------|
| retrospecting | Captures learnings using subagents after feature completion |
| updating-docs | Automatically updates documentation using agents |
| writing-skills | Applies TDD approach to skill documentation |
| detecting-kanban | Detects Vibe-Kanban and provides TodoWrite fallback |

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
| spec-reviewer | Reviews spec.md for testability, assumptions, and scope discipline |
| security-reviewer | Reviews implementation for security vulnerabilities |
| task-reviewer | Validates task breakdown quality for immediate executability |

### Workers

| Agent | Purpose |
|-------|---------|
| implementer | Implements tasks with TDD and self-review discipline |
| generic-worker | General-purpose implementation agent for mixed-domain tasks |
| documentation-writer | Writes and updates documentation based on research findings |
| code-simplifier | Identifies unnecessary complexity and suggests simplifications |

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
| secretary | Routes user requests to appropriate specialist agents |
| rca-investigator | Finds all root causes through 6-phase systematic investigation |

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
└── knowledge-bank/        # Accumulated learnings
```

## For Developers

See [README_FOR_DEV.md](./README_FOR_DEV.md) for:
- Component authoring (skills, agents, hooks)
- Architecture and design principles
- Release workflow
- Validation
