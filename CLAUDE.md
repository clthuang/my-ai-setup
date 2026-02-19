# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Claude Code plugin providing a structured feature development workflow—skills, commands, agents, and hooks that guide methodical development from ideation to implementation.

## Key Principles

- **No backward compatibility** - This is private tooling with no external users. Delete old code, don't maintain compatibility shims.
- **Branches for all modes** - All workflow modes (Standard, Full) create feature branches. Branches are lightweight.
- **Retro before cleanup** - Retrospective runs BEFORE branch deletion so context is still available.
- **Edit *-dev plugins only** - Never edit `plugins/iflow/` directly. Make changes in `plugins/iflow-dev/`, then run release script to sync.

## Writing Guidelines

**Agents with Write/Edit access should use judgment.** Avoid modifying:
- `.git/`, `node_modules/`, `.env*`, `*.key`, `*.pem`, lockfiles

Use `agent_sandbox/` for temporary files, experiments, and debugging.

## User Input Standards

**All interactive choices MUST use AskUserQuestion tool:**
- Required for yes/no prompts (not `(y/n)` text patterns)
- Required for numbered menus (not ASCII `1. Option` blocks)
- Required for any user selection

**AskUserQuestion format:**
```
AskUserQuestion:
  questions: [{
    "question": "Your question",
    "header": "Category",
    "options": [
      {"label": "Option", "description": "What this does"}
    ],
    "multiSelect": false
  }]
```

**Exceptions (plain text OK):**
- Informational messages with no choice ("Run /verify to check")
- Error messages with instructions
- Status output

## Commands

```bash
# Validate components
./validate.sh
```

## Key References

| Document | Use When |
|----------|----------|
| [Component Authoring Guide](docs/dev_guides/component-authoring.md) | Creating skills, agents, plugins, commands, or hooks |
| [Developer Guide](README_FOR_DEV.md) | Architecture, release process, design principles |
| [Hook Development Guide](docs/dev_guides/hook-development.md) | Writing or modifying hooks — covers PROJECT_ROOT vs PLUGIN_ROOT, JSON output, shared libs |

## Knowledge & Memory

- **Knowledge bank:** `docs/knowledge-bank/{patterns,anti-patterns,heuristics}.md` — updated by retrospectives
- **Global memory store:** `~/.claude/iflow/memory/` — cross-project entries injected at session start
- **Hook subprocess safety:** Always suppress stderr (`2>/dev/null`) for Python/external calls in hooks to prevent corrupting JSON output
- **Semantic memory CLI:** Invoke writer as module, not script: `PYTHONPATH=plugins/iflow-dev/hooks/lib .venv/bin/python -m semantic_memory.writer` — direct script execution causes `types.py` stdlib shadowing

## Quick Reference

**Naming conventions:** lowercase, hyphens, no spaces
- Skills: gerund form (`creating-tests`, `reviewing-code`)
- Agents: action/role (`code-reviewer`, `security-auditor`)
- Plugins: noun (`datascience-team`)

**Token budget:** SKILL.md <500 lines, <5,000 tokens

**Documentation sync:** When adding, removing, or renaming skills, commands, or agents in `plugins/iflow-dev/`, update:
- `README.md` and `README_FOR_DEV.md` — skill/agent/command tables and counts
- `plugins/iflow-dev/skills/workflow-state/SKILL.md` — Workflow Map section (if phase sequence or prerequisites change)

A hookify rule (`.claude/hookify.docs-sync.local.md`) will remind you on plugin component edits.

**Backlog:** Capture ad-hoc ideas with `/iflow:add-to-backlog <description>`. Review at [docs/backlog.md](docs/backlog.md).