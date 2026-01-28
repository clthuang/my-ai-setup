# Claude Code Component Authoring Guide

Reference specifications for creating skills, subagents, plugins, commands, and hooks.

---

## Skills

**Location:** `skills/{skill-name}/SKILL.md`

**Required Structure:**
```markdown
---
name: skill-name-gerund        # lowercase, hyphens only, prefer gerund form
description: What it does. Use when [specific triggers].
---

# Skill Title

[Instructions Claude follows when active]
```

**Authoring Rules:**
1. **Name**: Use gerund form (`creating-tests`, `reviewing-code`, `generating-docs`)
2. **Description**: Include BOTH what it does AND when to use it. Write in third person.
3. **Length**: Keep SKILL.md under 500 lines. Use reference files for detailed content.
4. **Progressive Disclosure**: SKILL.md = overview. Additional files = details loaded on-demand.

**Description Quality Checklist:**
- [ ] States what the skill does
- [ ] Lists specific trigger conditions
- [ ] Includes key terms users might mention
- [ ] Written in third person ("Generates..." not "You can use this to...")

**Skill Directory Structure:**
```
skills/{skill-name}/
├── SKILL.md              # Required entry point
├── scripts/              # Executable scripts
├── references/           # Supporting docs (loaded on-demand)
└── templates/            # Output templates
```

---

## Subagents

**Location:** `agents/{agent-name}.md`

**Required Structure:**
```markdown
---
name: agent-name
description: What this agent does. Use when [delegation criteria].
tools: [Allowed tools - omit to inherit all]
model: [Optional: haiku for speed, sonnet for quality]
---

[System prompt defining agent behavior]
```

**Authoring Rules:**
1. **Single Responsibility**: Each agent does ONE thing well
2. **Tool Scoping**: Explicitly list `tools:` to restrict capabilities
3. **Context Isolation**: Agents have separate context windows—use for deep dives
4. **Output Format**: Define how results should be returned to parent

---

## Plugins

**Location:** `plugins/{plugin-name}/`

**Required Structure:**
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json           # Required manifest
├── skills/                    # Optional
├── agents/                    # Optional
├── commands/                  # Optional
├── hooks/                     # Optional
└── README.md                  # Required documentation
```

**plugin.json Schema:**
```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Clear description of what this plugin provides",
  "author": { "name": "...", "email": "..." },
  "license": "MIT",
  "keywords": ["relevant", "keywords"]
}
```

---

## Commands

**Location:** `commands/{command-name}.md`

**Required Structure:**
```markdown
---
description: What this command does
argument-hint: [optional] [arguments]
allowed-tools: [Optional tool restrictions]
---

[Instructions for Claude when command is invoked]
```

---

## Hooks

**Location:** `hooks/{hook-name}/`

**Hook Types:**

| Event | Trigger | Can Block (exit 2) |
|-------|---------|-------------------|
| PreToolUse | Before tool execution | Yes |
| PostToolUse | After tool execution | No |
| UserPromptSubmit | Before prompt processed | Yes |
| Stop | Before session ends | Yes |
| SubagentStop | Before subagent returns | Yes |
| Notification | On notifications | No |
| PreCompact | Before context compaction | No |
| SessionStart | On session start/resume | No |

---

## Naming Conventions

| Component | Format | Examples |
|-----------|--------|----------|
| Skill name | gerund, lowercase, hyphens | `creating-tests`, `reviewing-code` |
| Agent name | action/role, lowercase, hyphens | `code-reviewer`, `security-auditor` |
| Plugin name | noun, lowercase, hyphens | `datascience-team`, `authoring-toolkit` |
| Command name | verb, lowercase, hyphens | `handoff`, `review`, `analyze` |

---

## Quality Standards

### Validation Checklist

Before merging any component:
- [ ] YAML frontmatter parses without errors
- [ ] `name` uses lowercase, hyphens, no spaces
- [ ] `description` includes what AND when
- [ ] SKILL.md under 500 lines
- [ ] Scripts are executable (`chmod +x`)
- [ ] No hardcoded absolute paths (use relative paths)
- [ ] README documents usage and examples

### Skill Activation Optimization

Description quality directly affects auto-triggering:
- Generic description → ~20% activation rate
- Specific description with triggers → ~50% activation rate
- Description + examples in SKILL.md → ~90% activation rate

---

## Anti-Patterns

| Don't | Why | Do Instead |
|-------|-----|------------|
| Put everything in SKILL.md | Exceeds 500 line limit, slow to load | Use reference files |
| Vague descriptions | Poor activation rate | Include specific triggers |
| Hardcoded absolute paths | Breaks portability | Use relative paths |
| Skip tool restrictions | Security risk, context pollution | Explicit `tools:` list |
| Nest skills deeply | Discovery issues | Flat structure preferred |
| Duplicate functionality | Maintenance burden | Compose existing skills |

---

## Token Budget

- Skill metadata (name + description): ~100 tokens each
- Full SKILL.md load: Target <5,000 tokens
- 15,000-character limit for entire available skills list in system prompt
- Reference files: Only loaded when Claude needs them

---

## Versioning

- Plugins use semantic versioning (MAJOR.MINOR.PATCH)
- Pin versions in marketplace.json for stability
- Breaking changes require MAJOR version bump

---

## See Also

- [Architecture Design](../prds/claude_code_special_force_design.md) - Three-tier configuration hierarchy
- [Anthropic Skills Repo](https://github.com/anthropics/skills) - Reference implementations
