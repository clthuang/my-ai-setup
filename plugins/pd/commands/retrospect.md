---
description: Run a retrospective for the current or a named feature
argument-hint: "[feature-id]"
---

# /pd:retrospect

Entry point to the retrospecting skill. Resolve the feature from the argument, else the single active feature; zero or several active without an argument → stop and ask. Then follow that skill.

**Inputs:** the feature's artifacts under `{pd_artifacts_root}/features/{id}-{slug}/`, the reviewer notes on its completed events, and engine phase state (`get_phase`).

**Constraints:** every figure the retro quotes — iteration counts, blocker counts, commit counts — is re-derived from those primary sources at write time, never copied from a briefing or a prior retro. Data is richest once implement closes; earlier runs work with less and say so.
