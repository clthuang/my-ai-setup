---
description: Explore an idea into an evidence-backed PRD
argument-hint: [topic or idea to explore]
---

# /pd:brainstorm

Contract command. No engine entry — no feature entity exists yet.

**Purpose:** turn a raw idea into a PRD a later phase can consume.

**Inputs:** the topic argument, or the topic asked of the user when the argument is empty.

**Output:** `{pd_artifacts_root}/brainstorms/{YYYYMMDD-HHMMSS}-{slug}.prd.md` — problem, cited evidence, requirements, risks, open questions.

**Steps:**
1. Invoke the `brainstorming` skill with the topic. The skill owns its stages and their outputs.
2. Report the PRD path, then offer promotion via `/pd:create-feature --prd=<path>`.

**Constraints:** no feature directory, branch, or entity is created here — promotion is `/pd:create-feature`'s job.
