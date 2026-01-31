# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Claude Code plugin providing a structured feature development workflow—skills, commands, agents, and hooks that guide methodical development from ideation to implementation.

## Key Principles

- **No backward compatibility** - This is private tooling with no external users. Delete old code, don't maintain compatibility shims.
- **Branches for all modes** - All workflow modes (Standard, Full) create feature branches. Branches are lightweight.
- **Retro before cleanup** - Retrospective runs BEFORE branch deletion so context is still available.

## Commands

```bash
# Validate components
./validate.sh
```

## Key References

| Document | Use When |
|----------|----------|
| [Component Authoring Guide](docs/guides/component-authoring.md) | Creating skills, agents, plugins, commands, or hooks |
| [Architecture Design](docs/prds/claude_code_special_force_design.md) | Understanding the three-tier config hierarchy |

## Quick Reference

**Naming conventions:** lowercase, hyphens, no spaces
- Skills: gerund form (`creating-tests`, `reviewing-code`)
- Agents: action/role (`code-reviewer`, `security-auditor`)
- Plugins: noun (`datascience-team`)

**Token budget:** SKILL.md <500 lines, <5,000 tokens

**Backlog:** Capture ad-hoc ideas with `/add-to-backlog <description>`. Review at [docs/backlog.md](docs/backlog.md).