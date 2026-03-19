# Spec: Rename to pedantic-drip

## Problem Statement

The repository is named `my-ai-setup` (a generic working title) and the plugin is named `iflow`. For the public open-source release, both need distinctive, memorable names that reflect the tool's adversarial review philosophy. The new names are `pedantic-drip` (repository) and `pd` (plugin prefix — abbreviation of pedantic-drip).

## Scope

### In Scope

**R1: Plugin directory rename**
- `plugins/iflow/` → `plugins/pd/`
- All internal paths within the plugin that reference `iflow` as directory name
- Delete and recreate `.venv` after rename (venvs contain hardcoded absolute paths in pyvenv.cfg)

**R2: Plugin identity rename**
- `plugin.json` name: `"iflow"` → `"pd"`
- `marketplace.json` name: `"iflow"` → `"pd"`
- Plugin cache path pattern references: `*/iflow*/` → `*/pd*/`

**R3: Command/skill/agent prefix rename**
- All `iflow:` prefixes in command names → `pd:` (29 commands)
- All `iflow:` prefixes in skill names → `pd:` (29 skills in frontmatter `name:` fields)
- All `iflow:` prefixes in agent `subagent_type:` references → `pd:` (28 agents)
- All `iflow:` references within command/skill/agent body text

**R4: Config file and template variable rename**
- `.claude/iflow.local.md` → `.claude/pd.local.md`
- Session-start hook reads config from `pd.local.md`
- Template variables throughout commands/skills:
  - `{iflow_artifacts_root}` → `{pd_artifacts_root}`
  - `{iflow_base_branch}` → `{pd_base_branch}`
  - `{iflow_release_script}` → `{pd_release_script}`
  - `{iflow_doc_tiers}` → `{pd_doc_tiers}`
  - `iflow_plugin_root` → `pd_plugin_root`
  - `max_concurrent_agents` stays (not iflow-prefixed)

**R5: Hook script updates**
- All 13 hook `.sh` scripts under `plugins/pd/hooks/` referencing `iflow` paths or config keys
- Note: `hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` for paths and event names for matchers — no `iflow` string present, no changes needed to hooks.json

**R6: Python source files**
- MCP servers: `entity_server.py`, `memory_server.py`, `workflow_state_server.py` — path references
- MCP bootstrap scripts: `run-entity-server.sh`, `run-memory-server.sh`, `run-workflow-server.sh`
- Hooks lib Python: `config.py`, `memory.py`, `backfill.py` — any `iflow` path references
- UI Python files under `plugins/pd/ui/`
- `.mcp.json` server entry paths update from `plugins/iflow/` to `plugins/pd/`

**R7: Scripts directory**
- `scripts/release.sh` — plugin path references
- `scripts/migrate_db.py`, `scripts/migrate.sh` — path references
- `scripts/setup-memory.sh` — path references
- `scripts/fix_kanban_columns.py` — path references
- `scripts/test_migrate_e2e.py`, `scripts/test_migrate_bash.sh` — test path references

**R8: Validation script**
- `validate.sh` path references: `plugins/iflow/` → `plugins/pd/`
- Template variable enforcement patterns: `iflow_artifacts_root` → `pd_artifacts_root`, `iflow_base_branch` → `pd_base_branch`
- Allowlist entries that hardcode `plugins/iflow/` paths

**R9: Documentation updates**
- `README.md` (root) — all `iflow` references
- `README_FOR_DEV.md` — all `iflow` references
- `plugins/pd/README.md` (after directory rename)
- `CLAUDE.md` (project) — all `iflow` references (31 occurrences)
- All docs/ references to `iflow` (excluding historical feature artifacts)

**R10: Hookify rules and .claude config files**
- `.claude/hookify.docs-sync.local.md` — `iflow` references
- `.claude/hookify.promptimize-reminder.local.md` — `iflow` references

**R11: Test files**
- All test files under `plugins/pd/` referencing `iflow` in paths or assertions
- Test files under `scripts/` referencing `iflow` paths

**R12: GitHub repository rename**
- Rename repo from `my-ai-setup` to `pedantic-drip` via `gh repo rename`
- Update git remote URL
- Note: GitHub provides automatic redirects from old URL

### Out of Scope
- Renaming the GitHub organization/username (`clthuang` stays)
- Renaming entity types in the database (feature, backlog, etc. stay)
- Migrating existing entity registry or memory DB data
- Renaming historical feature artifact directories (e.g., `docs/features/014-hook-migration-*`)
- Knowledge bank entries referencing `iflow` (archival data)
- Backward compatibility shims (per CLAUDE.md: "No backward compatibility")
- CI/CD pipeline updates beyond what's in the repo (external services)

## Execution Strategy

**Bulk replacement approach** — scoped to avoid over-replacement:

**Include in bulk replace:**
- `plugins/pd/**/*.md`, `plugins/pd/**/*.py`, `plugins/pd/**/*.sh`, `plugins/pd/**/*.json`
- `scripts/*.sh`, `scripts/*.py`
- `validate.sh`
- `README.md`, `README_FOR_DEV.md`, `CLAUDE.md`
- `.claude/*.local.md`
- `.mcp.json`
- `.claude-plugin/marketplace.json`

**Exclude from bulk replace:**
- `docs/features/*/` (historical artifacts — spec.md, design.md, retro.md, etc.)
- `docs/knowledge-bank/` (archival entries)
- `.git/` (immutable history)
- `__pycache__/` (regenerated)
- `.venv/` (deleted and recreated)
- `node_modules/` if present

**Replacement rules (ordered, most specific first):**
1. `iflow_artifacts_root` → `pd_artifacts_root` (template vars)
2. `iflow_base_branch` → `pd_base_branch`
3. `iflow_release_script` → `pd_release_script`
4. `iflow_doc_tiers` → `pd_doc_tiers`
5. `iflow_plugin_root` → `pd_plugin_root`
6. `plugins/iflow` → `plugins/pd` (paths)
7. `iflow:` → `pd:` (command/skill/agent prefixes)
8. `"iflow"` → `"pd"` (JSON name fields — targeted in plugin.json/marketplace.json only)

## Acceptance Criteria

- **AC-1**: `./validate.sh` passes with 0 errors
- **AC-2**: All test suites pass: entity_registry, semantic_memory, MCP servers, hook integration
- **AC-3**: `plugin.json` and `marketplace.json` show name `"pd"`
- **AC-4**: `grep -ri 'iflow' plugins/pd/` returns zero results (excluding `__pycache__/`)
- **AC-5**: `/pd:show-status` works (commands use `pd:` prefix)
- **AC-6**: MCP servers start successfully from new paths
- **AC-7**: `.claude/pd.local.md` is read by session-start hook
- **AC-8**: `gh repo view` shows repository name `pedantic-drip`
- **AC-9**: `grep -c 'iflow' CLAUDE.md` returns 0
- **AC-10**: Git remote URL points to `pedantic-drip` repository
- **AC-11**: All JSON files (plugin.json, marketplace.json, hooks.json, .mcp.json) parse without errors
- **AC-12**: `grep -ri 'iflow' scripts/` returns zero results (excluding `__pycache__/`)

## Risk

| Risk | Mitigation |
|------|------------|
| Regex over-replacement (hitting historical docs, knowledge bank) | Explicit include/exclude patterns; exclude docs/features/ and knowledge-bank/ |
| Plugin cache invalidation | Run sync-cache after rename |
| Venv path corruption | Delete and recreate .venv |
| MCP server restart needed | Restart after path changes |
| GitHub redirect from old URL | GitHub provides automatic redirects; existing clones need `git remote set-url` |
| JSON corruption from sed | AC-11 validates all JSON parses correctly; use targeted replacements not global |
