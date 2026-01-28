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

### 1. Start a Feature

```bash
/feature "add user authentication"
```

Claude will:
- Suggest a workflow mode (Hotfix/Quick/Standard/Full)
- Create feature folder at `docs/features/{id}-{name}/`
- Create git worktree (for Standard/Full modes)

### 2. Work Through Phases

```bash
/brainstorm    # Ideation, options exploration
/spec          # Requirements, acceptance criteria
/design        # Architecture, interfaces
/plan          # Implementation approach
/tasks         # Break into actionable items
/implement     # Execute the work
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
/status        # Current feature state
/features      # All active features
```

### 5. Complete Feature

```bash
/finish        # Merge, cleanup worktree, suggest retro
/retro         # Capture learnings (optional)
```

---

## Workflow Modes

| Mode | Phases | Verification | Use When |
|------|--------|--------------|----------|
| **Hotfix** | implement only | None | Single file fix |
| **Quick** | spec → tasks → implement | After implement | Small feature |
| **Standard** | All phases | Suggested | Normal feature |
| **Full** | All phases | Required | Large/risky change |

---

## File Structure

```
project/
├── docs/
│   ├── features/
│   │   └── {id}-{name}/
│   │       ├── brainstorm.md    # Ideas, options
│   │       ├── spec.md          # Requirements
│   │       ├── design.md        # Architecture
│   │       ├── plan.md          # Approach
│   │       ├── tasks.md         # Task list
│   │       └── retro.md         # Learnings
│   │
│   └── knowledge-bank/
│       ├── constitution.md      # Core principles
│       ├── patterns.md          # What works
│       ├── anti-patterns.md     # What to avoid
│       └── heuristics.md        # Decision guides
```

---

## Commands Reference

| Command | Purpose | Output |
|---------|---------|--------|
| `/feature` | Start new feature | Folder, worktree, mode selection |
| `/brainstorm` | Ideation phase | brainstorm.md |
| `/spec` | Specification | spec.md |
| `/design` | Architecture | design.md |
| `/plan` | Planning | plan.md |
| `/tasks` | Task breakdown | tasks.md |
| `/implement` | Execute work | Code changes |
| `/verify` | Quality check | Issue report |
| `/status` | Current state | Status summary |
| `/features` | List all features | Feature list |
| `/finish` | Complete feature | Merge, cleanup |
| `/retro` | Capture learnings | retro.md, knowledge-bank updates |

---

## Agents

**Implementation:**
- `investigation-agent` — Read-only research
- `frontend-specialist` — React, CSS, components
- `api-specialist` — API implementation
- `database-specialist` — Migrations, queries
- `generic-worker` — General implementation

**Verification:**
- `phase-verifiers` — Check artifact quality
- `quality-reviewer` — Code quality, cleanup

---

## Knowledge Bank

Learnings accumulate in `docs/knowledge-bank/`:

- **constitution.md** — Core principles (KISS, YAGNI, etc.)
- **patterns.md** — Approaches that worked
- **anti-patterns.md** — Things to avoid
- **heuristics.md** — Decision guides

Updated via `/retro` after feature completion.

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

**Skills:** `skills/{name}/SKILL.md` — Instructions Claude follows
**Agents:** `agents/{name}.md` — Isolated workers with specific focus
**Commands:** `commands/{name}.md` — User-invocable entry points

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

- [Feature Workflow Design](./docs/plans/2026-01-28-feature-workflow-design.md)
- [Component Authoring Guide](./docs/guides/component-authoring.md)
- [Superpowers](https://github.com/obra/superpowers)
- [Spec-kit](https://github.com/github/spec-kit)
