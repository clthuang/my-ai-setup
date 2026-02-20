# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

![Workflow Overview](../../docs/workflow-overview.png)

## Components

| Type | Count |
|------|-------|
| Skills | 27 |
| Agents | 28 |
| Commands | 22 |
| Hooks | 7 |
| MCP Tools | 2 |

## Commands

**Start:**
| Command | Description |
|---------|-------------|
| `/iflow-dev:brainstorm [topic]` | 7-stage PRD creation with research subagents and domain enrichment |
| `/iflow-dev:create-feature <desc>` | Start building (creates folder + branch) |

**Build phases** (run in order):
| Command | Output |
|---------|--------|
| `/iflow-dev:specify [--feature=ID]` | spec.md |
| `/iflow-dev:design` | design.md (4-stage workflow) |
| `/iflow-dev:create-plan` | plan.md |
| `/iflow-dev:create-tasks` | tasks.md |
| `/iflow-dev:implement` | Code changes |
| `/iflow-dev:finish` | Merge, retro, cleanup |

**Anytime:**
| Command | Purpose |
|---------|---------|
| `/iflow-dev:show-status` | See current feature state |
| `/iflow-dev:list-features` | See all active features |
| `/iflow-dev:retrospect` | Capture learnings |
| `/iflow-dev:add-to-backlog <idea>` | Capture ideas for later |
| `/iflow-dev:cleanup-brainstorms` | Delete old scratch files |
| `/iflow-dev:sync-cache` | Reload plugin after changes |
| `/iflow-dev:secretary` | Intelligent task routing to commands/agents |
| `/iflow-dev:root-cause-analysis` | Investigate bugs and failures to find all root causes |
| `/iflow-dev:create-project <prd>` | Create project from PRD with AI-driven decomposition |
| `/iflow-dev:create-specialist-team` | Create ephemeral specialist teams for complex tasks |
| `/iflow-dev:init-ds-project <name>` | Scaffold a new data science project |
| `/iflow-dev:review-analysis <file>` | Review data analysis for statistical pitfalls |
| `/iflow-dev:review-ds-code <file>` | Review DS Python code for anti-patterns |
| `/iflow-dev:yolo [on\|off]` | Toggle YOLO autonomous mode |

## Review System

The iflow workflow uses a two-tier review pattern for quality assurance:

### Two-Tier Review Pattern

| Component | Role | Question |
|-----------|------|----------|
| **Phase Skeptic** | Challenges artifact quality | "Is this artifact robust?" |
| **Phase Reviewer** | Validates handoff completeness | "Can the next phase proceed?" |

### Specify Phase Workflow

```
spec-reviewer (Skeptic) → "Is spec testable and bounded?"
    ↓
phase-reviewer (Gatekeeper) → "Has what design needs?"
```

### Design Phase Workflow

The `/iflow-dev:design` command uses a 5-stage workflow for robust design artifacts:

```
Stage 0: PRIOR ART RESEARCH → Existing solutions, patterns, standards, evidence gathering
    ↓
Stage 1: ARCHITECTURE DESIGN → High-level structure, components, evidence-grounded decisions, risks
    ↓
Stage 2: INTERFACE DESIGN → Precise contracts between components
    ↓
Stage 3: DESIGN REVIEW LOOP → design-reviewer challenges assumptions using independent verification (1-3 iterations)
    ↓
Stage 4: HANDOFF REVIEW → phase-reviewer ensures plan phase readiness
```

### Create Plan Phase Workflow

The `/iflow-dev:create-plan` command uses a 2-stage review workflow:

```
Stage 1: PLAN-REVIEWER (Skeptical Review)
    │   • Failure modes - What could go wrong?
    │   • Untested assumptions - What's assumed but not validated?
    │   • Dependency accuracy - Are dependencies correct and complete?
    │   • TDD order - Interface → Tests → Implementation sequence?
    ↓
Stage 2: PHASE-REVIEWER (Execution Readiness)
    │   • Can an engineer break this into tasks?
    │   • Are all design items covered?
    ↓
[User Prompt: Run /create-tasks?]
```

### Implementation Review

The `/iflow-dev:implement` command uses three reviewers:

| Reviewer | Focus | Validation |
|----------|-------|------------|
| implementation-reviewer | Requirements compliance | 4-level: Tasks→Spec→Design→PRD |
| code-quality-reviewer | Maintainability | SOLID, readability, testing |
| security-reviewer | Vulnerabilities | OWASP Top 10, injection, auth |

## Agents

| Agent | Purpose |
|-------|---------|
| advisor | Applies strategic/domain advisory lens to brainstorm problems |
| analysis-reviewer | Reviews data analysis for statistical pitfalls and methodology |
| brainstorm-reviewer | Reviews brainstorm artifacts for completeness before promotion |
| code-quality-reviewer | Reviews implementation quality by severity |
| code-simplifier | Identifies unnecessary complexity and suggests simplifications |
| codebase-explorer | Analyzes codebase for patterns and constraints |
| design-reviewer | Challenges design assumptions and finds gaps (skeptic) |
| documentation-researcher | Researches documentation state and identifies update needs |
| documentation-writer | Writes and updates documentation |
| ds-code-reviewer | Reviews DS Python code for anti-patterns and best practices |
| generic-worker | General-purpose implementation agent |
| implementation-reviewer | Validates implementation against full requirements chain (4-level) |
| implementer | Task implementation with TDD and self-review |
| internet-researcher | Searches web for best practices and standards |
| investigation-agent | Read-only research before implementation |
| phase-reviewer | Validates artifacts have what next phase needs (gatekeeper) |
| plan-reviewer | Skeptical plan reviewer for failure modes and TDD compliance |
| prd-reviewer | Critical review of PRD drafts |
| project-decomposer | Decomposes project PRD into ordered features with dependencies |
| project-decomposition-reviewer | Validates project decomposition quality |
| rca-investigator | Finds all root causes through 6-phase systematic investigation |
| retro-facilitator | Runs data-driven AORTA retrospective with full intermediate context |
| secretary | Intelligent task routing with discovery, interpretation, and delegation |
| secretary-reviewer | Validates secretary routing recommendations |
| security-reviewer | Reviews implementation for security vulnerabilities |
| skill-searcher | Finds relevant existing skills |
| spec-reviewer | Skeptically reviews spec.md for testability and assumptions |
| task-reviewer | Validates task breakdown quality and executability |

## MCP Tools

The memory server (`mcp/memory_server.py`) exposes two tools for long-term semantic memory:

| Tool | Purpose |
|------|---------|
| `store_memory` | Save a learning (pattern, anti-pattern, or heuristic) to long-term memory |
| `search_memory` | Search long-term memory for relevant learnings by topic |

## Installation

```bash
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```
