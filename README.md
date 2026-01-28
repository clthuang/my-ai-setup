# my_ai_setup

Centralized repository for developing and distributing Claude Code skills, subagents, plugins, commands, and hooks.

## Quick Start

### For Users

Add this marketplace to Claude Code:
```bash
/plugin marketplace add your-org/agent-teams
```

Install plugins:
```bash
/plugin install authoring-toolkit@agent-teams
```

### For Developers

Clone and start developing:
```bash
git clone https://github.com/your-org/agent-teams.git
cd agent-teams
chmod +x scripts/*.sh
```

## Repository Structure

```
agent-teams/
├── .claude-plugin/
│   └── marketplace.json      # Plugin marketplace catalog
├── plugins/                   # Distributable plugin bundles
├── skills/                    # Standalone skills
├── agents/                    # Standalone subagents
├── commands/                  # Standalone slash commands
├── hooks/                     # Reusable hook scripts
├── scripts/                   # Development utilities
├── docs/                      # Documentation
└── CLAUDE.md                  # AI development guide
```

## Available Components

### Skills

| Skill | Description |
|-------|-------------|
| `skill-authoring` | Create high-quality Claude Code skills |
| `agent-authoring` | Design and configure subagents |
| `plugin-authoring` | Package and distribute plugins |
| `hook-authoring` | Implement automation hooks |

### Plugins

| Plugin | Description |
|--------|-------------|
| `authoring-toolkit` | Complete meta-toolkit for creating Claude Code components |

## Development Workflow

### Creating a New Skill

1. Create the skill directory:
   ```bash
   mkdir -p skills/my-skill
   ```

2. Create `SKILL.md` with proper frontmatter:
   ```markdown
   ---
   name: my-skill
   description: What it does. Use when [triggers].
   ---
   
   # My Skill
   
   [Instructions]
   ```

3. Validate:
   ```bash
   ./scripts/validate.sh
   ```

4. Test activation:
   ```bash
   claude "Test prompt that should trigger my-skill"
   ```

### Creating a New Plugin

1. Create plugin structure:
   ```bash
   mkdir -p plugins/my-plugin/.claude-plugin
   mkdir -p plugins/my-plugin/skills/my-skill
   ```

2. Create `plugin.json`:
   ```json
   {
     "name": "my-plugin",
     "version": "1.0.0",
     "description": "What this plugin provides"
   }
   ```

3. Add to `marketplace.json`

4. Validate and test

## Quality Standards

### Skill Requirements

- [ ] Name uses gerund form (`creating-*`, `reviewing-*`)
- [ ] Description includes what AND when
- [ ] SKILL.md under 500 lines
- [ ] Valid YAML frontmatter
- [ ] No hardcoded paths

### Plugin Requirements

- [ ] Valid `plugin.json` with name, version, description
- [ ] README.md documentation
- [ ] All contained skills validated
- [ ] Tested installation from scratch

## Commands

```bash
# Validate all components
./scripts/validate.sh

# Validate specific plugin
claude /plugin validate ./plugins/my-plugin

# Test skill activation
claude /test-skill skill-name
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run validation: `./scripts/validate.sh`
5. Submit a pull request

### Commit Convention

```
feat(skills): add code-reviewing skill
fix(plugins): correct path in authoring-toolkit
docs: update skill authoring guide
```

## Resources

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Plugin Marketplaces Guide](https://code.claude.com/docs/en/plugin-marketplaces)
- [Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
