# My AI Setup

> A structured feature development workflow for Claude Code.

**What this is:** Skills, commands, and agents that guide Claude through methodical feature development—from ideation to implementation—with verification gates and knowledge accumulation.

**Inspired by:** [spec-kit](https://github.com/github/spec-kit), [superpowers](https://github.com/obra/superpowers), [Vibe-Kanban](https://github.com/BloopAI/vibe-kanban)

Nothing here is new—these are borrowed ideas from industry experts, tuned to my workflow.

---

## Quick Start

### Installation

```bash
git clone https://github.com/clthuang/my-ai-setup.git
cd my-ai-setup
claude .

# In Claude Code session:
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```

### Two Ways to Start

**Option A: Explore first**
```bash
/iflow:brainstorm "your idea here"
```
Brainstorms are scratch files in `docs/brainstorms/`. They don't have to become features—use them to explore any idea.

**Option B: Build something**
```bash
/iflow:create-feature "add user authentication"
```
Creates feature folder + branch, then guides you through the build phases.

### Build Phases

After `/iflow:create-feature`, work through these phases:

```
/iflow:specify → /iflow:design → /iflow:create-plan → /iflow:create-tasks → /iflow:implement → /iflow:finish
```

Each phase produces an artifact (spec.md, design.md, etc.). Use `--no-review` to skip reviewer loops.

### Check Progress

```bash
/iflow:show-status       # Current feature state
/iflow:verify            # Quality check any phase
/iflow:list-features     # See all active features
```

---

## Workflow Modes

| Mode | Reviewer Loops | Use When |
|------|----------------|----------|
| **Standard** | 1 iteration | Normal features (default) |
| **Full** | Up to 3 iterations | Refactors, risky changes |

---

## File Structure

```
my-ai-setup/
├── plugins/iflow/              # Workflow plugin
│   ├── skills/                 # Instructions Claude follows
│   ├── agents/                 # Specialized workers
│   ├── commands/               # User-invocable entry points
│   └── hooks/                  # Lifecycle automation
├── docs/
│   ├── brainstorms/            # Scratch files from /iflow:brainstorm
│   │   └── {timestamp}-{topic}.md
│   ├── features/               # Created by /iflow:create-feature
│   │   └── {id}-{name}/
│   │       ├── .meta.json      # Phase tracking
│   │       ├── spec.md
│   │       ├── design.md
│   │       ├── plan.md
│   │       ├── tasks.md
│   │       └── retro.md
│   ├── backlog.md              # Ad-hoc ideas
│   └── knowledge-bank/         # Accumulated learnings
└── validate.sh
```

---

## Commands

**Start:**
| Command | What it does |
|---------|--------------|
| `/iflow:brainstorm [topic]` | Explore ideas (scratch files, no commitment) |
| `/iflow:create-feature <desc>` | Start building (creates folder + branch) |

**Build phases** (run in order):
| Command | Output |
|---------|--------|
| `/iflow:specify` | spec.md - requirements |
| `/iflow:design` | design.md - architecture |
| `/iflow:create-plan` | plan.md - implementation approach |
| `/iflow:create-tasks` | tasks.md - actionable items |
| `/iflow:implement` | Code changes |
| `/iflow:finish` | Doc review, merge, retrospective, cleanup |

**Anytime:**
| Command | Purpose |
|---------|---------|
| `/iflow:verify` | Quality check current phase |
| `/iflow:show-status` | See where you are |
| `/iflow:list-features` | See all active features |
| `/iflow:retrospect` | Capture learnings (standalone) |
| `/iflow:add-to-backlog <idea>` | Capture ideas for later |
| `/iflow:cleanup-brainstorms` | Delete old scratch files |

All phase commands support `--no-review` to skip reviewer loops.

### What /iflow:finish Does

1. Checks for uncommitted changes and incomplete tasks
2. Offers quality review (spawns quality-reviewer agent)
3. Offers documentation review (detects README, CHANGELOG, docs/*.md)
4. Lets you choose: Create PR, Merge locally, Keep branch, or Discard
5. Runs mandatory retrospective (you control what to capture)
6. Cleans up branch

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

**Quality Review:**
- `spec-reviewer` — Verify implementation matches specification
- `code-quality-reviewer` — Code quality assessment
- `quality-reviewer` — Post-implementation quality check
- `final-reviewer` — Validates implementation matches original spec
- `chain-reviewer` — Validates artifact quality and phase handoffs

**Research:**
- `investigation-agent` — Read-only context gathering

---

## Hooks

Hooks execute automatically at lifecycle points.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start` | Session start/resume/clear/compact | Inject active feature context |
| `pre-commit-guard` | Before git commit commands | Warns when committing to main/master; prompts to confirm or use feature branch |

Defined in `plugins/iflow/hooks/hooks.json`.

---

## Knowledge Bank

Learnings accumulate in `docs/knowledge-bank/`:

- **constitution.md** — Core principles (KISS, YAGNI, etc.)
- **patterns.md** — Approaches that worked
- **anti-patterns.md** — Things to avoid
- **heuristics.md** — Decision guides

Updated via `/iflow:retrospect` after feature completion.

---

## Error Recovery

When something fails:

1. **Auto-retry** for transient issues
2. **Fresh approach** if retry fails
3. **Ask human** with clear options

**Principle:** Never spin endlessly. Never fail silently. Ask.

---

## For Developers

### Design Principles

| Principle | Meaning |
|-----------|---------|
| **Everything is prompts** | Skills and agents are just instructions Claude follows |
| **Files are truth** | Artifacts persist in files; any session can resume |
| **Humans unblock** | When stuck, Claude asks—never spins endlessly |
| **Composable > Rigid** | Phases work independently; combine as needed |

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
