---
description: Scaffold or update the three-tier project documentation
---

# /pd:generate-docs

Entry to the updating-docs skill for project-facing docs. Doc tiers live at the project root — `docs/user-guide/`, `docs/dev-guide/`, `docs/technical/` — NOT under `{pd_artifacts_root}`, which scopes pd's own workflow artifacts.

**Steps:**
1. Read `pd_doc_tiers` from session context; keep only `user-guide`, `dev-guide`, `technical`. Nothing recognized → say so and stop.
2. Mode: any enabled tier directory missing → `scaffold`; all present → `incremental`.
3. Scaffold writes new directories, so confirm once:

```
AskUserQuestion:
  questions: [{
    "question": "Scaffold {N} starter files across {missing tiers}?",
    "header": "Scaffold",
    "options": [
      {"label": "Scaffold", "description": "Create the missing tier directories and starter content"},
      {"label": "Skip", "description": "Exit without writing"}
    ],
    "multiSelect": false
  }]
```

4. Hand off to the updating-docs skill with the mode, the enabled tiers, and each tier's last source-path commit timestamp (`"no-source-commits"` when it has none). It owns the researcher and writer dispatches.
5. Report mode and tiers written.

**Constraints:** that skill's component-sync checklist applies whenever this run touches a README, CHANGELOG, or count claim.
