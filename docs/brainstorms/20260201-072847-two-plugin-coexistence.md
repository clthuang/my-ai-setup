# Brainstorm: Two-Plugin Coexistence (iflow + iflow-dev)

**Created:** 2026-02-01
**Status:** exploring

## Problem Statement

The current branch-based organization with a release script feels fragile:
- develop branch has `iflow-dev` naming in marketplace.json
- main branch has `iflow` naming
- release.sh transforms files between branches
- But Claude Code reads `plugin.json` directly, not marketplace naming
- Result: Confusion about which plugin is active

## Core Idea

Have two plugins coexist simultaneously:
- **iflow/** - Production/stable plugin (released versions)
- **iflow-dev/** - Development plugin (active work)

All new work goes to `iflow-dev`. The `iflow` plugin is protected and only updated through the release script.

## Why This Is Better

1. **Simplicity** - No branch-based transformations needed
2. **Clarity** - Clear separation between dev and production
3. **Safety** - Hook protection prevents accidental changes to iflow
4. **Parallel testing** - Can test against stable version while developing

## Key Questions to Explore

1. How do users install both plugins?
2. How does the release process work?
3. What protects iflow from accidental changes?
4. How do we handle shared code/dependencies?

---

## Exploration

### Current Structure
```
plugins/
  iflow/                    # The only plugin today
    .claude-plugin/
      plugin.json           # name: "iflow"
    skills/
    commands/
    hooks/
```

### Proposed Structure
```
plugins/
  iflow/                    # Production - protected
    .claude-plugin/
      plugin.json           # name: "iflow", version: 1.1.0
    skills/
    commands/
    hooks/

  iflow-dev/                # Development - active work
    .claude-plugin/
      plugin.json           # name: "iflow-dev", version: 0.0.0-dev
    skills/
    commands/
    hooks/
```

### Marketplace Structure
```
.claude-plugin/
  marketplace.json
    plugins:
      - name: "iflow"
        source: "./plugins/iflow"
        version: "1.1.0"
      - name: "iflow-dev"
        source: "./plugins/iflow-dev"
        version: "0.0.0-dev"
```

---

## Decisions Made

### Code Sharing: Full Duplication via Release Script
- **iflow-dev/** - Primary development location, all active work
- **iflow/** - Only updated by release script (copy from iflow-dev)
- Full duplication but controlled through release process

### Availability: Both Public and Local
- Both plugins available in public marketplace (GitHub)
- Both plugins available in local marketplace
- sync-cache.sh needs updates to handle both plugins

---

## Hook Protection Concept

Add pre-commit hook that:
```bash
# Block direct changes to plugins/iflow/ unless:
# 1. Running release script (check env var)
# 2. Explicit override flag

if changes_to_iflow && not_release_script; then
  echo "Direct changes to iflow/ blocked. Use release script."
  exit 1
fi
```

---

## Open Questions

### 1. iflow-dev Versioning Strategy ✓ DECIDED

**Decision: Next version with -dev suffix**

Example flow:
```
iflow@1.1.0 (current release)
iflow-dev@1.2.0-dev (working toward 1.2.0)

After release:
iflow@1.2.0 (new release)
iflow-dev@1.3.0-dev (bump to next dev)
```

Release script:
1. Copy iflow-dev/ → iflow/
2. Strip `-dev` from iflow version: `1.2.0-dev` → `1.2.0`
3. Bump iflow-dev to next minor: `1.2.0-dev` → `1.3.0-dev`

### 2. Skill Prefix Conflicts
- iflow commands: `/iflow:brainstorm`
- iflow-dev commands: `/iflow-dev:brainstorm`
- No conflict - different prefixes based on plugin.json name

### 3. sync-cache.sh Updates Needed
- Currently syncs single plugin to cache
- Need to sync both plugins (or just iflow-dev for local dev)
- Handle marketplace.json with both plugins listed

### 4. Release Script Changes
- Copy iflow-dev/ → iflow/ (full duplication)
- Update iflow/plugin.json version (strip -dev, bump version)
- Keep iflow-dev/plugin.json as next dev version
- Update marketplace.json with both plugin versions

---

## Proposed Architecture Summary

### Directory Structure
```
plugins/
  iflow/                      # Production - protected by hook
    .claude-plugin/
      plugin.json             # name: "iflow", version: "1.1.0"
    skills/
    commands/
    hooks/

  iflow-dev/                  # Development - active work here
    .claude-plugin/
      plugin.json             # name: "iflow-dev", version: "1.2.0-dev"
    skills/
    commands/
    hooks/

.claude-plugin/
  marketplace.json            # Lists BOTH plugins
```

### marketplace.json
```json
{
  "name": "my-local-plugins",
  "plugins": [
    {
      "name": "iflow",
      "source": "./plugins/iflow",
      "version": "1.1.0"
    },
    {
      "name": "iflow-dev",
      "source": "./plugins/iflow-dev",
      "version": "1.2.0-dev"
    }
  ]
}
```

### Release Flow
1. Run release script
2. Copy `plugins/iflow-dev/*` → `plugins/iflow/`
3. Update `plugins/iflow/.claude-plugin/plugin.json`:
   - name: "iflow" (stays)
   - version: strip -dev → "1.2.0"
4. Update `plugins/iflow-dev/.claude-plugin/plugin.json`:
   - version: bump minor → "1.3.0-dev"
5. Update marketplace.json with new versions
6. Commit and tag

### Hook Protection
Pre-commit hook blocks changes to `plugins/iflow/` unless:
- Running release script (env var `IFLOW_RELEASE=1`)
- Explicit bypass flag

### sync-cache.sh Updates
- Sync `plugins/iflow-dev/` → cache (for local development)
- Sync `plugins/iflow/` → cache (optional, for testing stable)
- Update marketplace.json in cache

## Notes

- This is not a high-security project - simplicity over protection
- Current release.sh approach has proven fragile
- The two-plugin model matches mental model better
- Eliminates branch-based transformations entirely

---

## Next Steps

- [x] Decide on duplication strategy → Full duplication via release script
- [x] Decide on dev versioning → Next version with -dev suffix
- [x] Design the release workflow → See above
- [ ] Define hook protection implementation details
- [ ] Consider promotion to feature

## Relationship to Feature 011

Feature 011 (plugin-distribution-versioning) attempted to solve this with branch-based naming. This brainstorm proposes a cleaner approach. Options:

1. **Pivot 011** - Update 011's design to use two-plugin approach
2. **Abandon 011, new feature** - Close 011, create new feature from this brainstorm
3. **Complete 011, then iterate** - Finish current 011 implementation, then create follow-up feature

Recommendation: Abandon 011, create new feature - the two-plugin approach is fundamentally different.
