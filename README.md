# My AI Setup

> A structured feature development workflow for Claude Code.

**What this is:** Skills, commands, and agents that guide Claude through methodical feature development—from ideation to implementation—with verification gates and knowledge accumulation.

---

## Design Principles

| Principle | Meaning |
|-----------|---------|
| **Everything is prompts** | Skills and agents are just instructions Claude follows |
| **Files are truth** | Artifacts persist in files; any session can resume |
| **Humans unblock** | When stuck, Claude asks—never spins endlessly |
| **Use > Test** | Real usage is the only test; refine through use |
| **Composable > Rigid** | Phases work independently; combine as needed |
| **Suggest > Enforce** | Verification suggested, human decides |

---

## Quick Start

### 0. Installation

This repository uses a plugin marketplace architecture:
- `.claude-plugin/marketplace.json` lists local plugins
- `plugins/iflow/` contains the workflow plugin

```bash
git clone https://github.com/clthuang/my-ai-setup.git
cd my-ai-setup
claude .
```

Claude Code discovers from `plugins/iflow/`:
- Skills from `skills/{name}/SKILL.md`
- Agents from `agents/{name}.md`
- Commands from `commands/{name}.md`
- Hooks from `hooks/hooks.json`

#### Using Components in Other Projects

To use these components in another project, install this plugin:

```bash
cd your-other-project

# Install as a project plugin (recommended)
claude /plugin install ~/repos/my-ai-setup --project .

# Or install globally (available in all projects)
claude /plugin install ~/repos/my-ai-setup
```

> **Note:** Global installation makes all components available everywhere. Project-level components override global ones if names conflict.

### 1. Start a Feature

```bash
/create-feature "add user authentication"
```

Claude will:
- Suggest a workflow mode (Hotfix/Quick/Standard/Full)
- Create feature folder at `docs/features/{id}-{name}/`
- Create feature branch `feature/{id}-{name}`

### 2. Work Through Phases

```bash
/brainstorm      # Ideation, options exploration
/specify         # Requirements, acceptance criteria
/design          # Architecture, interfaces
/create-plan     # Implementation approach
/create-tasks    # Break into actionable items
/implement       # Execute the work
```

**Each phase:**
- Produces an artifact (brainstorm.md, spec.md, etc.)
- Suggests verification (`/verify`)
- Suggests next phase

**Loop back anytime:** Phases are composable, not rigid.

### 3. Verify Work

```bash
/verify        # Run phase-appropriate verification
```

Verifiers check with fresh perspective:
- Red circle: Blockers must be fixed
- Yellow circle: Warnings should be addressed
- Green circle: Notes are suggestions

### 4. Check Status

```bash
/show-status     # Current feature state
/list-features   # All active features
```

### 5. Complete Feature

```bash
/finish          # Merge, run retro, cleanup branch
/retrospect      # Capture learnings (can also run standalone)
```

---

## Workflow Modes

| Mode | Phases | Verification | Use When |
|------|--------|--------------|----------|
| **Hotfix** | implement only | None | Single file fix |
| **Quick** | specify → create-tasks → implement | After implement | Small feature |
| **Standard** | All phases | Suggested | Normal feature |
| **Full** | All phases | Required | Large/risky change |

---

## File Structure

```
my-ai-setup/
├── .claude-plugin/
│   └── marketplace.json          # Local plugins registry
├── plugins/
│   └── iflow/                    # Feature workflow plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── {skill-name}/
│       │       └── SKILL.md
│       ├── agents/
│       │   └── {agent-name}.md
│       ├── commands/
│       │   └── {command-name}.md
│       └── hooks/
│           ├── hooks.json
│           └── *.sh
├── docs/
│   ├── features/
│   │   └── {id}-{name}/
│   │       ├── brainstorm.md
│   │       ├── spec.md
│   │       ├── design.md
│   │       ├── plan.md
│   │       ├── tasks.md
│   │       └── retro.md
│   ├── backlog.md                # Ad-hoc ideas
│   ├── guides/
│   ├── knowledge-bank/
│   └── plans/
└── validate.sh
```

---

## Commands Reference

| Command | Purpose | Output |
|---------|---------|--------|
| `/create-feature` | Start new feature | Folder, branch, mode selection |
| `/brainstorm` | Ideation phase | brainstorm.md |
| `/specify` | Specification | spec.md |
| `/design` | Architecture | design.md |
| `/create-plan` | Planning | plan.md |
| `/create-tasks` | Task breakdown | tasks.md |
| `/implement` | Execute work | Code changes |
| `/verify` | Quality check | Issue report |
| `/show-status` | Current state | Status summary |
| `/list-features` | List all features | Feature list |
| `/finish` | Complete feature | Merge, retro, cleanup |
| `/retrospect` | Capture learnings | retro.md, knowledge-bank updates |
| `/add-to-backlog` | Capture ad-hoc ideas | backlog.md entry |
| `/cleanup-brainstorms` | Archive expired brainstorms | Deleted files |

---

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

---

## Agents

**Implementation:**
- `implementer` — Task implementation with self-review, TDD
- `generic-worker` — General-purpose implementation

**Review:**
- `spec-reviewer` — Verify implementation matches specification
- `code-quality-reviewer` — Code quality assessment
- `quality-reviewer` — Post-implementation quality check

**Research:**
- `investigation-agent` — Read-only context gathering

**Review:**
- `final-reviewer` — Validates implementation matches original spec
- `chain-reviewer` — Validates artifact quality and phase handoffs

---

## Hooks

Hooks execute automatically at lifecycle points.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start` | Session start/resume/clear/compact | Inject active feature context |
| `pre-commit-guard` | Before git commit commands | Workflow enforcement |

Defined in `plugins/iflow/hooks/hooks.json`.

---

## Knowledge Bank

Learnings accumulate in `docs/knowledge-bank/`:

- **constitution.md** — Core principles (KISS, YAGNI, etc.)
- **patterns.md** — Approaches that worked
- **anti-patterns.md** — Things to avoid
- **heuristics.md** — Decision guides

Updated via `/retrospect` after feature completion.

---

## Error Recovery

When something fails:

1. **Auto-retry** for transient issues
2. **Fresh approach** if retry fails
3. **Ask human** with clear options

**Principle:** Never spin endlessly. Never fail silently. Ask.

---

## For Developers

### Creating Components

See [Component Authoring Guide](./docs/guides/component-authoring.md).

**Skills:** `plugins/iflow/skills/{name}/SKILL.md` — Instructions Claude follows
**Agents:** `plugins/iflow/agents/{name}.md` — Isolated workers with specific focus
**Commands:** `plugins/iflow/commands/{name}.md` — User-invocable entry points
**Hooks:** `plugins/iflow/hooks/` — Lifecycle automation scripts

### Validation

```bash
./validate.sh    # Check all components
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Run `./validate.sh`
4. Submit PR

---

## Architecture

```
User → /command → Claude reads skill → Follows instructions
                                    → Spawns agents if needed
                                    → Updates files
                                    → Uses Vibe-Kanban/TodoWrite for tracking
```

No routing layer. No orchestration. Just well-written prompts.

---

## References

- [Component Authoring Guide](./docs/guides/component-authoring.md)
- [Feature Workflow Design](./docs/plans/2026-01-28-feature-workflow-design.md)
- [Superpowers Patterns](./docs/plans/2026-01-28-superpowers-patterns-design.md)
- [Superpowers Repository](https://github.com/obra/superpowers)
- [Spec-kit](https://github.com/github/spec-kit)
