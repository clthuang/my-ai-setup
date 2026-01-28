# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Meta-repository for developing and documenting Claude Code configuration patterns—skills, subagents, plugins, commands, and hooks. Contains design documents and validation tooling; actual plugin implementations are created per the patterns documented here.

## Current State

This is a **documentation and design repository**—no plugin components exist yet:

- `docs/prds/claude_code_special_force_design.md` - Architecture design (three-tier config hierarchy)
- `docs/guides/component-authoring.md` - Component specifications (skills, agents, plugins, hooks)
- `for_windsurf/rules/global_rules.md` - Engineering principles template
- `validate.sh` - Validation script (ready for when components are added)

## Commands

```bash
# Validate components (run after adding skills/agents/plugins/commands)
./validate.sh
```

Note: Currently validates nothing since no `skills/`, `agents/`, `commands/`, or `.claude-plugin/` directories exist.

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