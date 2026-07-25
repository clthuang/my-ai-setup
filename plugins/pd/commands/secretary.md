---
description: Single entry point — triage a request into deep, express, or specialist
argument-hint: "<request> [--deep|--express]"
---

# /pd:secretary

Triage that selects a mode — not a pipeline. Assess the request, state mode + rationale in one short block, route, hand off. Triage never mutates state; the routed command owns entity work.

**Mode signals** (any present → deep is mandatory): security surface, schema or data migration, multi-file blast radius, novel domain, success criteria you cannot state mechanically. Express fits: small diff, known pattern, outcome verifiable by a command. Uncertain → deep.

**Routing:**
- **Deep** → `/pd:brainstorm` when the idea needs shaping, else `/pd:create-feature` → six-phase pipeline (sequence: workflow-state skill).
- **Express** → `/pd:create-feature --express` (inline mini-spec recorded as `mini_spec` event) → `/pd:implement` → `/pd:finish-feature`.
- **Existing feature named** → ask the engine (`get_phase`) and invoke the next phase command.
- **Specialist fast-path** (direct, no feature entity):

| Request pattern | Route |
|---|---|
| security / vulnerability review | `pd:security-reviewer` agent |
| code-quality review | `pd:code-quality-reviewer` agent |
| design/architecture review | `pd:design-reviewer` agent |
| DS analysis / DS code review | `/pd:review-ds-analysis` / `/pd:review-ds-code` |
| debug / root cause | `pd:systematic-debugging` skill / `/pd:root-cause-analysis` |
| explore codebase | `pd:codebase-explorer` agent |
| deepen tests | `pd:test-deepener` agent |
| docs / backlog / doctor / status | `/pd:generate-docs` `/pd:add-to-backlog` `/pd:doctor` `/pd:show-status` |

**Overrides:** `--deep` / `--express` force the mode both directions. Mid-express escalation: stop implement, `record_backward_event(feature_type_id, source_phase="implement", target_phase="specify", reason=<why>)`, then run `/pd:specify` — it reads the `mini_spec` event as its input; no restart penalty.

**Output shape:** `Mode: {deep|express|specialist} — {one-line rationale}. Routing to {command}.` Then invoke it, propagating `[YOLO_MODE]` per the global rule (workflow-transitions).

**Component discovery:** installed plugin first — `~/.claude/plugins/cache/*/pd*/*/` glob; fallback `plugins/pd/` (dev workspace).
