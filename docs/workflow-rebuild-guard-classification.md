# Workflow-Rebuild Guard Classification

Pre-work artifact for `docs/brainstorms/20260710-153500-workflow-rebuild.prd.md` (rev 2):
FR-9 (delete inventory), FR-10 (guards kept), and the Success Criterion "every retained
guard carries an expiry/re-test condition" ("build for deletion"). Census metrics refer to
`scripts/verbosity-census.sh`; the baseline run is recorded at the bottom.

## KEEP — model-independent guards

A guard stays only while its row names a live re-test condition. A kept guard whose
condition can no longer be stated is a deletion candidate by default (PRD SC).

| Guard | Lives in | Why model-independent | Expiry / re-test condition |
|---|---|---|---|
| Prompt-injection hardening in dispatch prompts | command dispatch blocks → one shared preamble after FR-3 | inputs are adversarial regardless of model capability; #065 documented live injected directives | Never expires while agents read untrusted files; re-test whenever the dispatch template changes (plant one directive in a fixture file, confirm it is ignored) |
| `data-file-guard` single-writer for `.meta.json` | PreToolUse hook dispatcher | enforces DB-as-truth write topology, not model skill | Re-scope (not delete) after FR-12 + #085 cutover verify projections-only writes: tighten to deny ALL agent `.meta.json` writes; re-test each time projection paths change |
| MCP degradation ladder (non-state ops proceed/reconcile; state mutations fail loud) | workflow-transitions | infrastructure failure handling | Infrastructure — no expiry; re-test whenever MCP transport or server topology changes |
| Prerequisite fail-fast (one line) | phase commands | phase ordering is a state-machine fact | Expires INTO the engine: once FR-12 lands, `validate_prerequisites` (MCP) is the check and the prose line goes; re-test = engine rejects an out-of-order transition |
| ONE bounded circuit breaker, final validation exempt | implement | halting guarantee for autonomous runs (anti-patterns.md:645 fixed by the exemption) | Re-test: zero happy-path trips across the first 3 P005 features (PRD SC); if 0 trips across 10 consecutive features, revisit the bound |
| YOLO safety hard-stops (merge conflict, review failure, missing prerequisites) | one global rule in workflow-transitions after FR-8 | irreversibility boundary, not capability | Never expires; re-test in each YOLO pilot run |

## DELETE — weak-model-era scaffolding

| Scaffolding | Census metric (baseline 2026-07-25) | Deletion rationale |
|---|---|---|
| `resume_state` machinery | `resume_state` = 239 | PRD Evidence: complexity managing the loop design's own token cost; harness handles continuity natively now |
| Delta-size guards | `delta_size_guards` = 48 | same class — guards for the machinery, not for any model failure |
| Context-compaction detection | `compaction_detection` = 37 | harness compacts + resumes natively (this session's own compactions prove the workflow survives without prose detection) |
| `Files read:` confirmation ritual | `files_read_ritual` = 40 | confirmation theater; execution-based QA (FR-5) verifies outcomes instead |
| LAZY-LOAD warnings | `lazy_load_warnings` = 14 | context-anxiety scaffolding; obsolete failure mode |
| Reviewer schema restatements in commands | `schema_restatements_commands` = 41 → **target 0** (PRD SC) | FR-6 single-source in agent files (`schema_restatements_skills` = 5 reviewed case-by-case: agent-file definitions are the ONE allowed home) |
| Per-command YOLO blocks | `yolo_block_headers` = 13, `yolo_mentions` = 95 | FR-8: one global rule |
| Mandatory post-pass re-validation | in `dispatch_sites_commands` = 40 (`implement.md:250,910`) | audit-findings.md:13-39 Critical #1; FR-5 deletes it |
| JSON parse/retry ladders | (no discrete token; falls with word count) | 2024-era transport defenses; MCP degradation ladder (kept) covers real transport failure |

## Baseline run — 2026-07-25 (`scripts/verbosity-census.sh`)

```
scope_words_commands	44435
scope_words_skills	66790
scope_words_total	111225
resume_state	239
delta_size_guards	48
compaction_detection	37
files_read_ritual	40
lazy_load_warnings	14
schema_restatements_commands	41
schema_restatements_skills	5
yolo_block_headers	13
yolo_mentions	95
dispatch_sites_commands	40
dispatch_sites_reviewer_commands	13
```

Note: `scope_words_total` (111,225) exceeds the PRD's ~74,000 approximation because the
pinned scope includes every `.md` under `plugins/pd/skills/` (references included) — the
prose an orchestrating session can actually load. Per the PRD (FR-9), these pinned numbers
supersede the 2026-07-10 approximations; the ≤5,000-word target applies to this scope.
