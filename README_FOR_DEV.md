# Developer Guide

This repo uses a git-flow branching model with automated releases via conventional commits.

## Branch Structure

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only (tagged versions) |
| `develop` | Integration branch (default for development) |
| `feature/*` | Feature branches (created by iflow workflow) |

## Two-Plugin Model

Two plugins coexist in this repository:

| Plugin | Purpose | Directory | Version Format |
|--------|---------|-----------|----------------|
| `iflow-dev` | Development work | `plugins/iflow-dev/` | X.Y.Z-dev |
| `iflow` | Stable releases | `plugins/iflow/` | X.Y.Z |

**Key points:**
- All development happens in `plugins/iflow-dev/`
- `plugins/iflow/` is **read-only** - updated only via release script
- The pre-commit hook blocks direct commits to `plugins/iflow/`
- Use `IFLOW_RELEASE=1` to bypass protection (release script only)

## Development Workflow

1. Create feature branch from `develop`
2. Use conventional commits (`feat:`, `fix:`, `BREAKING CHANGE:`)
3. Merge to `develop` via `/iflow:finish` or PR
4. Release when ready using the release script

## Version Bump Logic

Version bumps are calculated automatically based on code change volume:

| Change % | Bump | Example |
|----------|------|---------|
| ≤3% | Patch | 1.0.0 → 1.0.1 |
| 3-10% | Minor | 1.0.0 → 1.1.0 |
| >10% | Major | 1.0.0 → 2.0.0 |

The script calculates: `(lines added + lines deleted) / total codebase lines`

## Release Process

### Option 1: GitHub Actions (Recommended)

Trigger from GitHub Actions UI or CLI:

```bash
# Dry run - verify what would happen
gh workflow run release.yml --ref develop -f dry_run=true

# Real release
gh workflow run release.yml --ref develop -f dry_run=false
```

### Option 2: Local Release

From the develop branch with a clean working tree:

```bash
./scripts/release.sh
```

### What the Release Script Does

1. Validate preconditions (on develop, clean tree, has origin)
2. Calculate version from code change percentage since last tag
3. Copy `plugins/iflow-dev/` to `plugins/iflow/`
4. Convert all `iflow-dev:` references to `iflow:`
5. Update plugin.json files with appropriate versions
6. Update marketplace.json with both versions
7. Commit with `IFLOW_RELEASE=1` bypass, push develop
8. Merge develop to main, create and push git tag

## Local Development Setup

Clone the repository and install the development plugin:

```bash
git clone https://github.com/clthuang/my-ai-setup.git
cd my-ai-setup
claude
```

In Claude Code:

```
/plugin marketplace add .claude-plugin/marketplace.json
/plugin install iflow-dev@my-local-plugins
```

After making changes to plugin files, sync the cache:

```
/iflow-dev:sync-cache
```

## For Public Users

To install the released version:

```
/plugin marketplace add clthuang/my-ai-setup
/plugin install iflow
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/release.sh` | Release automation script |
| `.github/workflows/release.yml` | CI release workflow |
| `.claude-plugin/marketplace.json` | Marketplace configuration |
| `plugins/iflow/.claude-plugin/plugin.json` | Plugin manifest with version |

---

## Architecture

```
User → /command → Claude reads skill → Follows instructions
                                    → Spawns agents if needed
                                    → Updates files
                                    → Uses Vibe-Kanban/TodoWrite for tracking
```

No routing layer. No orchestration. Just well-written prompts.

## Design Principles

| Principle | Meaning |
|-----------|---------|
| **Everything is prompts** | Skills and agents are just instructions Claude follows |
| **Files are truth** | Artifacts persist in files; any session can resume |
| **Humans unblock** | When stuck, Claude asks—never spins endlessly |
| **Composable > Rigid** | Phases work independently; combine as needed |

## Skills

Skills are instructions Claude follows for specific development practices. Located in `plugins/iflow-dev/skills/{name}/SKILL.md`.

### Workflow Phases
| Skill | Purpose |
|-------|---------|
| `brainstorming` | Guides 7-stage process producing evidence-backed PRDs |
| `specifying` | Creates precise specifications with acceptance criteria |
| `designing` | Creates design.md with architecture and contracts |
| `planning` | Produces plan.md with dependencies and ordering |
| `breaking-down-tasks` | Breaks plans into small, actionable tasks with dependency tracking |
| `implementing` | Guides phased TDD implementation (Interface → RED-GREEN → REFACTOR) |
| `finishing-branch` | Guides branch completion with PR or merge options |

### Quality & Review
| Skill | Purpose |
|-------|---------|
| `reviewing-artifacts` | Comprehensive quality criteria for PRD, spec, design, plan, and tasks |
| `implementing-with-tdd` | Enforces RED-GREEN-REFACTOR cycle with rationalization prevention |
| `workflow-state` | Defines phase sequence and validates transitions |

### Investigation
| Skill | Purpose |
|-------|---------|
| `systematic-debugging` | Guides four-phase root cause investigation |
| `root-cause-analysis` | Structured 6-phase process for finding ALL contributing causes |

### Maintenance
| Skill | Purpose |
|-------|---------|
| `retrospecting` | Captures learnings using subagents after feature completion |
| `updating-docs` | Automatically updates documentation using agents |
| `writing-skills` | Applies TDD approach to skill documentation |
| `detecting-kanban` | Detects Vibe-Kanban and provides TodoWrite fallback |

## Agents

Agents are isolated subprocesses spawned by the workflow. Located in `plugins/iflow-dev/agents/{name}.md`.

**Reviewers (10):**
- `brainstorm-reviewer` — Reviews brainstorm artifacts for completeness before promotion
- `code-quality-reviewer` — Reviews implementation quality after spec compliance is confirmed
- `design-reviewer` — Challenges design assumptions and finds gaps
- `implementation-reviewer` — Validates implementation against full requirements chain (Tasks → Spec → Design → PRD)
- `phase-reviewer` — Validates artifact completeness for next phase transition
- `plan-reviewer` — Skeptically reviews plans for failure modes and feasibility
- `prd-reviewer` — Critically reviews PRD drafts for quality and completeness
- `spec-reviewer` — Reviews spec.md for testability, assumptions, and scope discipline
- `security-reviewer` — Reviews implementation for security vulnerabilities
- `task-reviewer` — Validates task breakdown quality for immediate executability

**Workers (4):**
- `implementer` — Implements tasks with TDD and self-review discipline
- `generic-worker` — General-purpose implementation agent for mixed-domain tasks
- `documentation-writer` — Writes and updates documentation based on research findings
- `code-simplifier` — Identifies unnecessary complexity and suggests simplifications

**Researchers (5):**
- `codebase-explorer` — Analyzes codebase to find relevant patterns and constraints
- `documentation-researcher` — Researches documentation state and identifies update needs
- `internet-researcher` — Searches web for best practices, standards, and prior art
- `investigation-agent` — Read-only research agent for context gathering
- `skill-searcher` — Finds relevant existing skills for a given topic

**Orchestration (2):**
- `secretary` — Routes user requests to appropriate specialist agents
- `rca-investigator` — Finds all root causes through 6-phase systematic investigation

## Hooks

Hooks execute automatically at lifecycle points.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `sync-cache` | SessionStart | Syncs plugin source to Claude cache |
| `cleanup-locks` | SessionStart | Removes stale lock files |
| `session-start` | SessionStart | Injects active feature context |
| `inject-secretary-context` | SessionStart | Injects available agent/command context for secretary |
| `cleanup-sandbox` | (utility) | Cleans up agent_sandbox/ temporary files |
| `pre-commit-guard` | PreToolUse (Bash) | Branch protection and iflow directory protection |

Defined in `plugins/iflow-dev/hooks/hooks.json`.

### Hook Protection

The `pre-commit-guard` hook enforces two protections:

1. **Protected branches**: Prompts for confirmation when committing to main/master/develop
2. **Production plugin protection**: Blocks commits that touch `plugins/iflow/`

To bypass protection (release script only):
```bash
IFLOW_RELEASE=1 git commit -m "chore(release): v1.2.0"
```

## Workflow Details

### Create-Tasks Workflow

The `/create-tasks` command uses a two-stage review process:

1. **Task Breakdown**: `breaking-down-tasks` skill produces `tasks.md` with:
   - Mermaid dependency graph
   - Parallel execution groups
   - Detailed task specifications (files, steps, tests, done criteria)

2. **Task Review**: `task-reviewer` validates (up to 3 iterations):
   - Plan fidelity (every plan item has tasks)
   - Task executability (any engineer can start immediately)
   - Task size (5-15 min each)
   - Dependency accuracy (parallel groups correct)
   - Testability (binary done criteria)

3. **Phase Review**: `phase-reviewer` validates readiness for implementation phase

4. **Completion**: Prompts user to start `/implement`

### Implement Workflow

The `/implement` command uses a multi-phase execution flow:

1. **Implementation**: Subagents -> Interface scaffold -> RED-GREEN loop -> REFACTOR
2. **Simplification**: `code-simplifier` removes unnecessary complexity
3. **Review** (iterative): `implementation-reviewer` -> `code-quality-reviewer` -> `security-reviewer` (up to 2-3 iterations)
4. **Completion**: Prompts user to run `/finish`

## Knowledge Bank

Learnings accumulate in `docs/knowledge-bank/`:

- **constitution.md** — Core principles (KISS, YAGNI, etc.)
- **patterns.md** — Approaches that worked
- **anti-patterns.md** — Things to avoid
- **heuristics.md** — Decision guides

Updated via `/iflow:retrospect` after feature completion.

## Creating Components

See [Component Authoring Guide](./docs/dev_guides/component-authoring.md).

All components are created in the `plugins/iflow-dev/` directory:

**Skills:** `plugins/iflow-dev/skills/{name}/SKILL.md` — Instructions Claude follows
**Agents:** `plugins/iflow-dev/agents/{name}.md` — Isolated workers with specific focus
**Commands:** `plugins/iflow-dev/commands/{name}.md` — User-invocable entry points
**Hooks:** `plugins/iflow-dev/hooks/` — Lifecycle automation scripts

## Validation

```bash
./validate.sh    # Check all components
```

## Error Recovery

When something fails:

1. **Auto-retry** for transient issues
2. **Fresh approach** if retry fails
3. **Ask human** with clear options

**Principle:** Never spin endlessly. Never fail silently. Ask.

## Contributing

1. Fork the repository
2. Create feature branch
3. Run `./validate.sh`
4. Submit PR

## References

- [Component Authoring Guide](./docs/dev_guides/component-authoring.md)
