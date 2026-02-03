# iflow Plugin

> Structured feature development workflow for Claude Code

## Installation

**For users** (stable releases):
```bash
/plugin marketplace add clthuang/my-ai-setup
/plugin install iflow@my-local-plugins
```

**For contributors** (development version):
```bash
git clone https://github.com/clthuang/my-ai-setup.git
cd my-ai-setup
claude

# In Claude Code session:
/plugin marketplace add [path to marketplace.json]
/plugin install iflow-dev@my-local-plugins
```

The `iflow` plugin contains stable releases. The `iflow-dev` plugin tracks development and may have unreleased changes.

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

| Command | Purpose |
|---------|---------|
| `/iflow:brainstorm [topic]` | Explore ideas (scratch files) |
| `/iflow:create-feature <desc>` | Start building (creates folder + branch) |
| `/iflow:specify` | Write requirements → spec.md |
| `/iflow:design` | Define architecture → design.md |
| `/iflow:create-plan` | Plan implementation → plan.md |
| `/iflow:create-tasks` | Break into tasks → tasks.md (two-stage review) |
| `/iflow:implement` | Write code (Interface -> TDD -> Simplify -> Review) |
| `/iflow:finish` | Review, merge, retrospective, cleanup |
| `/iflow:verify` | Quality check current phase |
| `/iflow:show-status` | See current progress |
| `/iflow:list-features` | List active features |

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
