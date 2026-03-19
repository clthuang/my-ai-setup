# Spec: Rename to pedantic-drip

## Problem Statement

The repository is named `my-ai-setup` (a generic working title) and the plugin is named `iflow`. For the public open-source release, both need distinctive, memorable names that reflect the tool's adversarial review philosophy. The new names are `pedantic-drip` (repository) and `pd` (plugin prefix).

## Scope

### In Scope

**R1: Plugin directory rename**
- `plugins/iflow/` → `plugins/pd/`
- All internal paths within the plugin that reference `iflow` as directory name

**R2: Plugin identity rename**
- `plugin.json` name: `"iflow"` → `"pd"`
- `marketplace.json` name: `"iflow"` → `"pd"`
- Plugin cache path pattern: `*/iflow*/` → `*/pd*/`

**R3: Command/skill/agent prefix rename**
- All `iflow:` prefixes in command names → `pd:` (29 commands)
- All `iflow:` prefixes in skill names → `pd:` (29 skills in frontmatter `name:` fields)
- All `iflow:` prefixes in agent `subagent_type:` references → `pd:` (28 agents)
- All `iflow:` references within command/skill/agent body text

**R4: Config file rename**
- `.claude/iflow.local.md` → `.claude/pd.local.md`
- Session-start hook reads config from `pd.local.md`
- Session context variables: `iflow_artifacts_root` → `pd_artifacts_root`, `iflow_base_branch` → `pd_base_branch`, `iflow_release_script` → `pd_release_script`, `iflow_doc_tiers` → `pd_doc_tiers`
- All references to `{iflow_*}` template variables in commands/skills → `{pd_*}`

**R5: Hook script updates**
- All 14 hook scripts referencing `iflow` paths, config keys, or prefixes
- `hooks.json` matcher patterns referencing `iflow:`

**R6: MCP server references**
- `.mcp.json` server names: `entity-registry`, `memory-server`, `workflow-engine` (names stay, but paths update)
- MCP bootstrap scripts referencing `plugins/iflow/` paths
- Internal references to `plugin_iflow_*` tool name patterns in docs

**R7: Documentation updates**
- `README.md` (root) — all `iflow` references
- `README_FOR_DEV.md` — all `iflow` references
- `plugins/iflow/README.md` → `plugins/pd/README.md`
- `CLAUDE.md` (project) — all `iflow` references (31 occurrences)
- `~/.claude/CLAUDE.md` (global) — no `iflow` references expected
- All `docs/` references to `iflow`

**R8: Validation script**
- `validate.sh` references to `plugins/iflow/`

**R9: GitHub repository rename**
- Rename repo from `my-ai-setup` to `pedantic-drip` via `gh repo rename`
- Update git remote URL

**R10: Hookify rules**
- `.claude/hookify.*.local.md` files referencing `iflow`

**R11: Test files**
- All test files under `plugins/iflow/` that import from `iflow`-relative paths or reference `iflow` in assertions

**R12: Python package references**
- `plugins/iflow/.venv/` — recreate or leave as-is (venv is local, not committed)
- `pyproject.toml` or `setup.py` if they reference `iflow`

### Out of Scope
- Renaming the GitHub organization/username (`clthuang` stays)
- Renaming entity types in the database (feature, backlog, etc. stay as-is)
- Migrating existing entity registry or memory DB data
- Renaming the `docs/features/` directory structure
- Backward compatibility shims (per CLAUDE.md: "No backward compatibility")

## Acceptance Criteria

- **AC-1**: `./validate.sh` passes with 0 errors after rename
- **AC-2**: All test suites pass: entity_registry, semantic_memory, MCP servers, hook integration
- **AC-3**: `plugin.json` and `marketplace.json` show name `"pd"`
- **AC-4**: No remaining references to `iflow` in `plugins/pd/` directory (except historical docs/features/ paths and knowledge bank entries which are archival)
- **AC-5**: `/pd:show-status` works (commands use `pd:` prefix)
- **AC-6**: MCP servers start successfully from new paths
- **AC-7**: `.claude/pd.local.md` is read by session-start hook
- **AC-8**: `gh repo view` shows repository name `pedantic-drip`
- **AC-9**: No remaining `iflow` references in CLAUDE.md (project)
- **AC-10**: Git remote URL points to `pedantic-drip` repository

## Execution Strategy

This rename is best executed as a **scripted bulk operation**, not manual file-by-file edits:

1. **Directory rename** first (`plugins/iflow/` → `plugins/pd/`)
2. **Bulk text replacement** via `sed` or equivalent:
   - `iflow:` → `pd:` (command/skill/agent prefixes)
   - `plugins/iflow` → `plugins/pd` (path references)
   - `iflow_artifacts_root` → `pd_artifacts_root` (and other config vars)
   - `iflow` → `pd` in plugin.json/marketplace.json name fields (targeted, not global)
3. **Config file rename** (`.claude/iflow.local.md` → `.claude/pd.local.md`)
4. **Validation** — run tests and validate.sh
5. **GitHub rename** — `gh repo rename pedantic-drip`
6. **Remote update** — `git remote set-url origin ...`

## Risk

- **Regex over-replacement**: Blindly replacing `iflow` could hit unintended matches (e.g., knowledge bank entries, git history references, feature folder names like `docs/features/014-hook-migration-yolo-stopsh-and/`). Replacements must be scoped to specific file patterns and contexts.
- **Plugin cache invalidation**: After rename, the installed plugin cache at `~/.claude/plugins/cache/*/iflow*/` becomes stale. Must run sync-cache after rename.
- **MCP server restart**: After path changes, MCP servers need restart to pick up new paths.
