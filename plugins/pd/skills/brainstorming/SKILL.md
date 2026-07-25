---
name: brainstorming
description: Ideation contract turning a raw idea into an evidence-backed PRD. Use when the user says 'brainstorm this', 'explore options for', 'start ideation', or 'create a PRD'.
---

# Brainstorming

## Config Variables
From session context: `{pd_artifacts_root}` (artifact root, default `docs`), `max_concurrent_agents` (dispatch batch size, default 5).

**Output:** one PRD at `{pd_artifacts_root}/brainstorms/{YYYYMMDD-HHMMSS}-{slug}.prd.md`, after `mkdir -p {pd_artifacts_root}/brainstorms/`. Slug: topic lowercased, non-alphanumerics collapsed to single hyphens, trimmed to 30 characters.

## 1. Clarify
Settle five things before any research: the problem, who it affects, what success looks like in measurable terms ("works better" is not a criterion), known constraints, and approaches already tried. One question at a time. Apply YAGNI to every "nice to have".

## 2. Research
Dispatch in batches of `max_concurrent_agents`. Each agent carries one narrow question and returns findings with sources, never file dumps:

- `pd:codebase-explorer` — what already exists here, and where.
- `pd:internet-researcher` — external prior art and standard approaches.
- `pd:skill-searcher` — capabilities already installed.
- `pd:advisor` — one dispatch per lens, each carrying the verbatim text of `references/advisors/{name}.advisor.md` plus the clarify answers. Default pair: `pre-mortem` and `opportunity-cost`. Swap in `feasibility` for build risk, `working-backwards` for a fuzzy deliverable, `first-principles` for open exploration. A missing template is skipped with a warning.

A failed agent is a warning, not a stop.

## 3. Converge
Fold the findings into one document. Every claim carries `— Evidence: {URL | file:line | User input}` or `— Assumption: needs verification`. Contradictions between sources are stated, not averaged away.

## 4. Write the PRD
Sections in order: Status · Problem Statement · Goals · Success Criteria · User Stories · Use Cases · Edge Cases & Error Handling · Constraints (behavioral, then technical) · Requirements (FR and NFR) · Non-Goals · Research Summary · Strategic Analysis (one subsection per advisor, closing with its evidence quality) · Open Questions · Next Steps.

## 5. Review, then decide
Dispatch `pd:prd-reviewer` in fresh context; its return shape lives in the agent file. One pass → at most one fix round → remaining blockers go to the user alongside the decision.

Then ask what happens next: `/pd:create-feature --prd={path}`, or `/pd:create-project --prd={path}` when the PRD spans three or more entity types, functional areas, or user-facing surfaces — otherwise refine further, or save and stop.

**Constraints:** this skill writes the PRD and nothing else — no feature directories, no code, no phase commands.
