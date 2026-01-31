# Brainstorm: Plugin Distribution & Versioning

**Backlog Item:** 00005
**Topic:** Separate stable production branch and dev branch, plugin distribution format, and version control

## Problem Statement

The iflow plugin currently:
1. Has no stable/dev branch separation - all development happens on main
2. Uses a local file-based marketplace with hardcoded version 1.0.0
3. Has no public distribution mechanism for others to use
4. Relies on sync-cache hook to copy source to cache on each session

This creates risk for personal use (breaking changes affect daily work) and makes sharing with the public difficult.

## Goals

1. **Stability for personal use** - Have a known-good version to fall back to
2. **Safe development** - Experiment without breaking daily workflow
3. **Public distribution** - Allow others to install and use the plugin
4. **Version control** - Track changes with semantic versioning

## Current Setup

```
~/.claude/plugins/
├── installed_plugins.json  (tracks: iflow@my-local-plugins v1.0.0)
├── known_marketplaces.json (points to local marketplace.json)
└── cache/my-local-plugins/iflow/1.0.0/  (synced from source)

/Users/terry/projects/my-ai-setup/
├── .claude-plugin/marketplace.json  (local marketplace definition)
└── plugins/iflow/  (plugin source)
```

## Approaches Considered

### 1. Branching Strategy

**Approach A: main + dev branch**
- `main` = stable, production-ready
- `dev` = active development
- Pros: Simple, familiar pattern
- Cons: Only two states (stable/unstable)

**Approach B: main + develop + feature branches** ✓ CHOSEN
- `main` = stable releases only (tagged)
- `develop` = integration branch (default working branch)
- `feature/*` = individual features (existing iflow pattern)
- Pros: Aligns with iflow workflow, clear release process
- Cons: Slightly more overhead

**Approach C: Trunk-based with release tags**
- Single `main` branch with version tags
- Pros: Simplest
- Cons: No development mode separation

**Decision:** Approach B - Feature branches merge to `develop`, release to `main` via explicit release command/script.

### 2. Distribution Format

**Approach A: GitHub-hosted marketplace** ✓ CHOSEN
- Host `marketplace.json` in repo on `main` branch
- Users add marketplace URL to Claude config
- Claude Code fetches from GitHub on install
- Pros: Standard Claude Code pattern, version selection built-in
- Cons: Requires understanding Claude's plugin system

**Approach B: Git clone + local install**
- Users clone repo, run install from local path
- Pros: Simple, no hosting needed
- Cons: Manual updates, no version management

**Approach C: npm-style package**
- Publish to npm registry
- Pros: Familiar to JS developers
- Cons: Claude Code doesn't natively support npm plugins

**Approach D: GitHub Releases**
- Downloadable zip/tarball per version
- Pros: Version history clear
- Cons: Manual process for users

**Decision:** Approach A - GitHub marketplace with marketplace.json on main branch.

### 3. Version Control

**Approach A: Manual version bumps**
- Edit version manually before release
- Pros: Simple
- Cons: Error-prone, easy to forget

**Approach B: Release script with prompts**
- Script asks major/minor/patch
- Updates versions, creates tag, merges to main
- Pros: Consistent process
- Cons: Requires remembering to run it

**Approach C: Conventional commits + auto-versioning** ✓ CHOSEN
- Use commit prefixes: feat:, fix:, BREAKING CHANGE:
- Auto-determine version bump from commits since last release
- Pros: No manual decision, encourages good commit messages
- Cons: Requires discipline

**Decision:** Approach C - Conventional commits with release script that auto-calculates version.

### 4. Local Development vs Stable Use

**Approach A: Always use source (current behavior)**
- sync-cache copies source → cache every session
- Issue: Breaking changes affect daily work

**Approach B: Switch between modes**
- Flag or environment variable toggles source vs installed
- Pros: Clear separation
- Cons: More complex setup

**Approach C: Dual installation** ✓ CHOSEN
- `iflow` = stable version from GitHub marketplace
- `iflow-dev` = local source (for development)
- Pros: Both always available, clear naming
- Cons: Need to maintain two plugin names

**Decision:** Approach C - Publish as `iflow` for public, develop locally as `iflow-dev`.

## Chosen Direction

**Branching:** main + develop + feature branches
- `develop` becomes default branch for iflow workflow
- Features merge to `develop` via /iflow:finish
- Releases merge `develop` → `main` with version tag

**Distribution:** GitHub-hosted marketplace
- `marketplace.json` on `main` branch points to stable releases
- Users install via Claude Code's plugin system
- Repo must be public on GitHub

**Versioning:** Conventional commits with auto-versioning
- Commit prefixes determine version bump
- Release script calculates next version from commits
- Updates plugin.json, marketplace.json, creates git tag

**Local development:** Dual installation
- Rename local dev plugin to `iflow-dev` in local marketplace
- Install public `iflow` from GitHub for stable daily use
- Both available simultaneously, no confusion

## YAGNI Check

Reviewing for unnecessary complexity:
- ❌ CI/CD pipeline for releases - manual release script is sufficient for now
- ❌ Changelog generation - can add later if needed
- ❌ Multiple marketplace support - one GitHub marketplace is enough
- ✓ All four decisions are necessary for the stated goals

## Open Questions

1. Should the repo be renamed from `my-ai-setup` to something more descriptive like `claude-iflow-plugin`?
2. What's the minimum viable release script? (version bump + tag + merge)
3. How to handle the existing local marketplace setup during transition?

## Next Steps

Ready for /iflow:specify to define requirements for:
1. Branch restructure (create develop, update iflow to target develop)
2. Release script (conventional commits → version calculation)
3. Dual plugin setup (rename local to iflow-dev)
4. Public marketplace setup (marketplace.json for GitHub)
