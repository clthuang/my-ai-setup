# Developer Guide

This repo uses a git-flow branching model with automated releases via conventional commits.

## Branch Structure

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only (tagged versions) |
| `develop` | Integration branch (default for development) |
| `feature/*` | Feature branches (created by iflow workflow) |

## Plugin Names

The plugin has different names depending on the context:

| Context | Plugin Name | Commands | Branch |
|---------|-------------|----------|--------|
| Development | `iflow-dev` | `/iflow-dev:*` | develop |
| Public | `iflow` | `/iflow:*` | main |

## Development Workflow

1. Create feature branch from `develop`
2. Use conventional commits (`feat:`, `fix:`, `BREAKING CHANGE:`)
3. Merge to `develop` via `/iflow:finish` or PR
4. Release when ready using the release script

## Conventional Commits

Commit prefixes determine version bumps:

| Prefix | Version Bump | Example |
|--------|--------------|---------|
| `feat:` | Minor (1.0.0 → 1.1.0) | `feat: add new command` |
| `fix:` | Patch (1.0.0 → 1.0.1) | `fix: correct typo in output` |
| `BREAKING CHANGE:` | Major (1.0.0 → 2.0.0) | `BREAKING CHANGE: rename API` |

Scope is optional: `feat(hooks):` works the same as `feat:`.

## Release Process

From the develop branch with a clean working tree:

```bash
git checkout develop
./scripts/release.sh
```

The script will:
1. Validate preconditions (on develop, clean tree, has origin)
2. Calculate version from conventional commits since last tag
3. Update version in `plugins/iflow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
4. Convert marketplace to public format (`iflow` instead of `iflow-dev`)
5. Commit, push develop, merge to main
6. Create and push git tag
7. Restore dev format on develop branch

## Local Development Setup

To use the development version of the plugin:

```
/plugin uninstall iflow@my-local-plugins
/plugin marketplace update my-local-plugins
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

Skills are instructions Claude follows for specific development practices.

### Feature Workflow
| Skill | Purpose |
|-------|---------|
| `brainstorming` | Ideation with YAGNI discipline |
| `specifying` | Requirements and acceptance criteria |
| `designing` | Architecture and interfaces |
| `planning` | Implementation approach |
| `breaking-down-tasks` | Create actionable tasks |
| `implementing` | Code execution with TDD |
| `verifying` | Phase-appropriate verification |
| `updating-docs` | Guide documentation updates |
| `retrospecting` | Capture learnings |

### Advanced Disciplines
| Skill | Purpose |
|-------|---------|
| `implementing-with-tdd` | RED-GREEN-REFACTOR enforcement |
| `systematic-debugging` | Root cause investigation |
| `verifying-before-completion` | Evidence before claims |
| `subagent-driven-development` | Three-agent workflow per task |
| `dispatching-parallel-agents` | Concurrent investigation |

### Infrastructure
| Skill | Purpose |
|-------|---------|
| `finishing-branch` | Branch completion options |
| `writing-skills` | TDD for skill authoring |
| `workflow-state` | Phase sequence and state management |
| `detecting-kanban` | Kanban availability with TodoWrite fallback |

## Agents

**Implementation:**
- `implementer` — Task implementation with self-review, TDD
- `generic-worker` — General-purpose implementation

**Quality Review:**
- `spec-reviewer` — Verify implementation matches specification
- `code-quality-reviewer` — Code quality assessment
- `quality-reviewer` — Post-implementation quality check
- `final-reviewer` — Validates implementation matches original spec
- `chain-reviewer` — Validates artifact quality and phase handoffs

**Research:**
- `investigation-agent` — Read-only context gathering

## Hooks

Hooks execute automatically at lifecycle points.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start` | Session start/resume/clear/compact | Inject active feature context |
| `pre-commit-guard` | Before git commit commands | Warns when committing to main/master; prompts to confirm or use feature branch |

Defined in `plugins/iflow/hooks/hooks.json`.

## Knowledge Bank

Learnings accumulate in `docs/knowledge-bank/`:

- **constitution.md** — Core principles (KISS, YAGNI, etc.)
- **patterns.md** — Approaches that worked
- **anti-patterns.md** — Things to avoid
- **heuristics.md** — Decision guides

Updated via `/iflow:retrospect` after feature completion.

## Creating Components

See [Component Authoring Guide](./docs/guides/component-authoring.md).

**Skills:** `plugins/iflow/skills/{name}/SKILL.md` — Instructions Claude follows
**Agents:** `plugins/iflow/agents/{name}.md` — Isolated workers with specific focus
**Commands:** `plugins/iflow/commands/{name}.md` — User-invocable entry points
**Hooks:** `plugins/iflow/hooks/` — Lifecycle automation scripts

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

- [Component Authoring Guide](./docs/guides/component-authoring.md)
