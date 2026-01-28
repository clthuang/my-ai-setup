# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Meta-repository for developing and documenting Claude Code configuration patterns—skills, subagents, plugins, commands, and hooks. Contains design documents and validation tooling; actual plugin implementations are created per the patterns documented here.

## Current State

This is a **documentation and design repository**—no plugin components exist yet:

- `docs/prds/claude_code_special_force_design.md` - Main design document (centralized config architecture)
- `for_windsurf/rules/global_rules.md` - Engineering principles template
- `validate.sh` - Validation script (ready for when components are added)

## Commands

```bash
# Validate components (run after adding skills/agents/plugins/commands)
./validate.sh
```

Note: Currently validates nothing since no `skills/`, `agents/`, `commands/`, or `.claude-plugin/` directories exist.

## Component Authoring Standards

### Skills (`skills/*/SKILL.md`)
- **Name**: lowercase, hyphens, gerund form (`creating-tests`, `reviewing-code`)
- **Description**: Third-person, includes WHAT it does AND WHEN to use it
- **Size**: Under 500 lines; use reference files for details

### Agents (`agents/*.md`)
- Single responsibility per agent
- Explicit `tools:` list to restrict capabilities
- Define output format for parent consumption

### Plugins
- Valid `plugin.json` with name, version, description
- README.md documenting usage
- Semantic versioning (MAJOR.MINOR.PATCH)

## Validation

The `validate.sh` script checks:
- YAML frontmatter syntax and required fields
- Name format (lowercase, hyphens)
- Description quality (length, trigger phrases)
- SKILL.md line count (<500)
- plugin.json and marketplace.json structure

## Naming Conventions

| Component | Format | Example |
|-----------|--------|---------|
| Skill name | gerund, lowercase | `creating-tests` |
| Agent name | action, lowercase | `code-reviewer` |
| Plugin name | noun, lowercase | `datascience-team` |

## Token Budget

- Skill metadata: ~100 tokens each
- Full SKILL.md: Target <5,000 tokens
- Skills list in system prompt: 15,000-character limit