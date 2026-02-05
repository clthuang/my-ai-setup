# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

![Workflow Overview](../../docs/workflow-overview.png)

## Components

| Type | Count |
|------|-------|
| Skills | 18 |
| Agents | 19 |
| Commands | 16 |
| Hooks | 5 |

## Commands

**Start:**
| Command | Description |
|---------|-------------|
| `/iflow-dev:brainstorm [topic]` | 7-stage PRD creation with research subagents |
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

## Review System

The iflow workflow uses a two-tier review pattern for quality assurance:

### Two-Tier Review Pattern

| Component | Role | Question |
|-----------|------|----------|
| **Phase Skeptic** | Challenges artifact quality | "Is this artifact robust?" |
| **Phase Reviewer** | Validates handoff completeness | "Can the next phase proceed?" |

### Specify Phase Workflow

```
spec-skeptic (Skeptic) → "Is spec testable and bounded?"
    ↓
phase-reviewer (Gatekeeper) → "Has what design needs?"
```

### Design Phase Workflow

The `/iflow-dev:design` command uses a 4-stage workflow for robust design artifacts:

```
Stage 1: ARCHITECTURE DESIGN → High-level structure, components, decisions, risks
    ↓
Stage 2: INTERFACE DESIGN → Precise contracts between components
    ↓
Stage 3: DESIGN REVIEW LOOP → design-reviewer challenges assumptions (1-3 iterations)
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
| brainstorm-reviewer | Reviews brainstorm artifacts for completeness before promotion |
| code-quality-reviewer | Reviews implementation quality by severity |
| code-simplifier | Identifies unnecessary complexity and suggests simplifications |
| codebase-explorer | Analyzes codebase for patterns and constraints |
| design-reviewer | Challenges design assumptions and finds gaps (skeptic) |
| documentation-researcher | Researches documentation state and identifies update needs |
| documentation-writer | Writes and updates documentation |
| generic-worker | General-purpose implementation agent |
| implementation-reviewer | Validates implementation against full requirements chain (4-level) |
| implementer | Task implementation with TDD and self-review |
| internet-researcher | Searches web for best practices and standards |
| investigation-agent | Read-only research before implementation |
| phase-reviewer | Validates artifacts have what next phase needs (gatekeeper) |
| plan-reviewer | Skeptical plan reviewer for failure modes and TDD compliance |
| prd-reviewer | Critical review of PRD drafts |
| rca-investigator | Finds all root causes through 6-phase systematic investigation |
| secretary | Intelligent task routing with discovery, interpretation, and delegation |
| security-reviewer | Reviews implementation for security vulnerabilities |
| skill-searcher | Finds relevant existing skills |
| spec-skeptic | Skeptically reviews spec.md for testability and assumptions |
| task-reviewer | Validates task breakdown quality and executability |

## Installation

```bash
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```
