# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

## Components

| Type | Count |
|------|-------|
| Skills | 18 |
| Agents | 13 |
| Commands | 14 |
| Hooks | 2 |

## Commands

**Start:**
| Command | Description |
|---------|-------------|
| `/iflow:brainstorm [topic]` | 6-stage PRD creation with research subagents |
| `/iflow:create-feature <desc>` | Start building (creates folder + branch) |

**Build phases** (run in order):
| Command | Output |
|---------|--------|
| `/iflow:specify` | spec.md |
| `/iflow:design` | design.md |
| `/iflow:create-plan` | plan.md |
| `/iflow:create-tasks` | tasks.md |
| `/iflow:implement` | Code changes |
| `/iflow:finish` | Merge, retro, cleanup |

**Anytime:**
| Command | Purpose |
|---------|---------|
| `/iflow:verify` | Quality check current phase |
| `/iflow:show-status` | See current feature state |
| `/iflow:list-features` | See all active features |
| `/iflow:retrospect` | Capture learnings |
| `/iflow:add-to-backlog <idea>` | Capture ideas for later |
| `/iflow:cleanup-brainstorms` | Delete old scratch files |

## Installation

```bash
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```
