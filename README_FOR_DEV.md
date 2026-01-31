# Developer Guide

This repo uses a git-flow branching model with automated releases via conventional commits.

## Branch Structure

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only (tagged versions) |
| `develop` | Integration branch (default for development) |
| `feature/*` | Feature branches (created by iflow workflow) |

## Plugin Names

The plugin has different names depending on the context:

| Context | Plugin Name | Commands | Branch |
|---------|-------------|----------|--------|
| Development | `iflow-dev` | `/iflow-dev:*` | develop |
| Public | `iflow` | `/iflow:*` | main |

## Development Workflow

1. Create feature branch from `develop`
2. Use conventional commits (`feat:`, `fix:`, `BREAKING CHANGE:`)
3. Merge to `develop` via `/iflow:finish` or PR
4. Release when ready using the release script

## Conventional Commits

Commit prefixes determine version bumps:

| Prefix | Version Bump | Example |
|--------|--------------|---------|
| `feat:` | Minor (1.0.0 → 1.1.0) | `feat: add new command` |
| `fix:` | Patch (1.0.0 → 1.0.1) | `fix: correct typo in output` |
| `BREAKING CHANGE:` | Major (1.0.0 → 2.0.0) | `BREAKING CHANGE: rename API` |

Scope is optional: `feat(hooks):` works the same as `feat:`.

## Release Process

From the develop branch with a clean working tree:

```bash
git checkout develop
./scripts/release.sh
```

The script will:
1. Validate preconditions (on develop, clean tree, has origin)
2. Calculate version from conventional commits since last tag
3. Update version in `plugins/iflow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
4. Convert marketplace to public format (`iflow` instead of `iflow-dev`)
5. Commit, push develop, merge to main
6. Create and push git tag
7. Restore dev format on develop branch

## Local Development Setup

To use the development version of the plugin:

```
/plugin uninstall iflow@my-local-plugins
/plugin marketplace update my-local-plugins
/plugin install iflow-dev@my-local-plugins
```

After making changes to plugin files, sync the cache:

```
/iflow-dev:sync-cache
```

## For Public Users

To install the released version:

```
/plugin marketplace add clthuang/my-ai-setup
/plugin install iflow
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/release.sh` | Release automation script |
| `.claude-plugin/marketplace.json` | Marketplace configuration |
| `plugins/iflow/.claude-plugin/plugin.json` | Plugin manifest with version |
