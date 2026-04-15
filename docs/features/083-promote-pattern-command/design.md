---
last-updated: 2026-04-16
feature: 083-promote-pattern-command
project: P002-memory-flywheel
---

# Design: /pd:promote-pattern

## Prior Art (Step 0 — abbreviated, YOLO)

Skipped formal research dispatch — the codebase was mapped during prior P002 investigations:
- **KB markdown parsers exist** in `plugins/pd/hooks/lib/semantic_memory/importer.py` (parses anti-patterns/heuristics/patterns) — reusable rather than rewriting parsing.
- **Hook registration pattern** is in `plugins/pd/hooks/hooks.json` + `.sh` files following established conventions (validated by feature 078's checks).
- **Slash-command pattern** is markdown files under `plugins/pd/commands/{name}.md`, similar in shape to `/pd:remember`, `/pd:add-to-backlog`.
- **AskUserQuestion gating** is the canonical user-interaction pattern across all commands (per CLAUDE.md User Input Standards).
- **Existing skills count:** 30+ under `plugins/pd/skills/` — confirms FR-3-skill needs Top-3 LLM filter (full list is unwieldy).

## Architecture Overview

A **slash command** (`/pd:promote-pattern`) backed by an **optional supporting skill** (`pd:promoting-patterns`) that holds the deeper procedural logic. Command file is the entrypoint per pd convention; skill carries reusable steps.

```
User → /pd:promote-pattern [name?]
         ↓
       commands/promote-pattern.md  (entrypoint, ~150 lines)
         ↓ (Skill dispatch)
       skills/promoting-patterns/SKILL.md  (logic core, ~250 lines)
         ↓
       ┌─ Step 1: Enumerate KB (parser + filter)
       ├─ Step 2: Classify target (regex score → LLM fallback → user)
       ├─ Step 3: Generate diff (per-target generator)
       ├─ Step 4: Approval gate (AskUserQuestion + edit-content path)
       └─ Step 5: Apply (5-stage atomic write)
```

## Components

### C-1: Command entrypoint — `plugins/pd/commands/promote-pattern.md`
Markdown command file following the convention of `remember.md` / `add-to-backlog.md`. Receives optional `<entry-name>` argument. Dispatches the `pd:promoting-patterns` skill with parsed args. Handles top-level arg parsing, --help, validation of args.

### C-2: Logic skill — `plugins/pd/skills/promoting-patterns/SKILL.md`
Procedural skill containing the FR-1..FR-6 step-by-step. Markdown-driven (no Python module needed for the skill itself — the orchestrating LLM follows the steps). References the helper modules below for deterministic operations.

### C-3: KB parser helper — extends `plugins/pd/hooks/lib/semantic_memory/importer.py`
Add a function `enumerate_qualifying_entries(kb_dir, min_observations) -> list[KBEntry]`:
- Reuses existing markdown parsing in `importer.py` (don't rewrite).
- Adds the `effective_observation_count` normalization from FR-1 (Observation count field OR distinct Feature # count).
- Filters by `confidence='high'` for files that have it; by observation count threshold for all.
- Excludes entries containing `- Promoted: ` line.

`KBEntry` dataclass fields: `name`, `description`, `confidence`, `effective_observation_count`, `category` (anti-pattern/heuristic/pattern), `file_path`, `line_range`.

### C-4: Classifier helper — new `plugins/pd/hooks/lib/promote_pattern/classifier.py`
Pure-Python module:
- `classify_keywords(entry: KBEntry) -> dict[str, int]` — returns `{hook: int, skill: int, agent: int, command: int}` score map per FR-2a regex table (Python `re` flavor, IGNORECASE).
- Constants for the 4 keyword tables (single source of truth for FR-2a rows).
- `decide_target(scores: dict) -> Literal['hook', 'skill', 'agent', 'command'] | None` — returns winner if strictly highest; None if tied or all-zero (caller invokes LLM fallback).

The skill (C-2) calls these via `plugins/pd/.venv/bin/python -m promote_pattern.classifier ...` (subprocess — same pattern as semantic_memory tooling).

### C-5: Per-target diff generators — new `plugins/pd/hooks/lib/promote_pattern/generators/`
Four generator modules:
- `hook.py` — generates the `.sh` skeleton + `hooks.json` patch + test stub from feasibility-gate output. Validates JSON post-patch. Closed-enum tools array enforced.
- `skill.py` — applies append-to-section patch to a target SKILL.md. Section-locator helper.
- `agent.py` — same shape as skill but for `plugins/pd/agents/{name}.md`.
- `command.py` — same shape but for `plugins/pd/commands/{name}.md`, with step-id targeting.

Each generator exposes a single function: `generate(entry: KBEntry, target_meta: dict) -> DiffPlan` where `DiffPlan` is a list of `FileEdit` records: `{path, action, before, after}`.

### C-6: 5-stage apply orchestrator — new `plugins/pd/hooks/lib/promote_pattern/apply.py`
Implements FR-5 staging:
- `pre_flight(diff_plan) -> bool` — Stage 1 validation
- `snapshot(diff_plan) -> dict[path, content]` — Stage 2
- `write(diff_plan) -> None` — Stage 3 (with rollback closure capturing snapshot)
- `validate_baseline_delta(snapshot) -> bool` — Stage 4 (runs validate.sh before+after)
- `mark_kb(entry, target_path, target_type) -> None` — Stage 5

Wraps in a single `apply(entry, diff_plan, target_type) -> Result` function. On any stage failure, restores from snapshot and returns `Result(success=False, reason=...)`.

### C-7: Config field — `.claude/pd.local.md` template
Add `memory_promote_min_observations: 3` to the `# Memory` block. Read by C-3 enumerator. Documented in the template comment.

## Technical Decisions

### TD-1: Skill-as-logic, command-as-entry
Following `/pd:retrospect` / `pd:retrospecting` pattern: command is thin (arg parsing + dispatch); skill carries the workflow. Keeps the command markdown small (~150 lines) and the skill testable independently.

### TD-2: Reuse semantic_memory.importer for KB parsing
**Why:** Existing parser handles markdown structure correctly; rewriting risks divergence. **Risk:** importer is currently used only for `import` flow — extending it must not break that flow. Mitigation: add the new function alongside existing ones; existing callers untouched; tests for both new and old paths.

### TD-3: Subprocess Python calls from skill markdown
The orchestrating LLM in the skill markdown invokes Python helpers via `plugins/pd/.venv/bin/python -m promote_pattern.classifier` etc. **Why:** keeps deterministic logic in pure Python (testable, fast, no LLM cost), while skill markdown handles user interaction + orchestration. **Alternative considered:** putting all logic in Python and command markdown just calls one entrypoint. Rejected because user interaction (AskUserQuestion) is markdown-driven.

### TD-4: LLM fallback uses inline orchestrator call (no MCP)
For FR-2c classification + FR-3-{hook,skill,agent,command} LLM steps, the skill markdown asks the orchestrating Claude directly (inline reasoning), not via MCP or subagent. **Why:** ≤2000 token budget per attempt is tight; Task subagent dispatch has substantial overhead. Inline reasoning is fast and stays within the orchestrator's existing context. **Risk:** orchestrator's classification could drift over sessions. Mitigation: validation of LLM output against closed enum (FR-2c).

### TD-5: Baseline-delta validation via validate.sh
FR-5 Stage 4 captures `validate.sh` output before and after writes. **Why:** project already has validate.sh; reuse rather than build new validator. **Risk:** validate.sh is slower than a targeted check (~2-5s on this repo). Mitigation: NFR-4 budget allows up to 30s — well within current.

### TD-6: KB marker is line-level, not structured
Marker is a `- Promoted: {target_type}:{repo-relative path}` markdown bullet. **Why:** matches existing `- Confidence:`, `- Used in:` line conventions; survives markdown re-parsing trivially. **Alternative:** YAML frontmatter per entry. Rejected because anti-patterns.md / heuristics.md / patterns.md don't use frontmatter per-entry.

### TD-7: Hook feasibility gate restricted to mechanical checks
FR-3-hook step 1 explicitly returns `infeasible` for rules that cannot be expressed as regex/JSON-field checks on tool input. **Why:** PreToolUse can't observe arbitrary semantic conditions (e.g., "test code respects encapsulation" requires AST analysis). Forcing such patterns to fall through to skill/agent target prevents shipping hooks that silently never fire.

### TD-8: No transaction wrapper
FR-5 5-stage apply uses in-memory snapshot + manual rollback rather than git stash/restore or transactional FS. **Why:** simpler, no external dependency; all writes are within `plugins/pd/`, not destructive at scale. **Risk:** if process is killed mid-Stage-3, partial state remains. Mitigation: documented in error table; user re-runs command (idempotency from FR-5 marker).

## Risks

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| KB parser drift between import flow and promote-pattern flow | Medium | Medium | Tests for both; shared parser code |
| LLM classification drift over time | Medium | Low | Closed-enum validation; user override always available |
| `hooks.json` schema evolves (new fields) | Low | Medium | Parse + emit using existing JSON tooling; validate post-patch |
| Mid-flight process termination | Low | Low | Re-run is safe (FR-5 marker idempotency) |
| `validate.sh` baseline-delta has false positives (e.g., timing-sensitive checks) | Low | Medium | Compare error count + categories; document in error table; allow manual override on next iteration |
| Skill discovery list (C-2 input to LLM Top-3) becomes noisy as skills grow | Medium | Low | Cap at 30 in initial prompt; if exceeded, pre-filter by keyword overlap |
| User edit-content corrupts markdown structure | Medium | Low | Stage 4 validate.sh catches structural errors; rollback restores |

## Interfaces

### I-1: `enumerate_qualifying_entries(kb_dir: Path, min_observations: int) -> list[KBEntry]`
**Module:** `plugins/pd/hooks/lib/semantic_memory/importer.py` (extension)
**Signature:**
```python
def enumerate_qualifying_entries(
    kb_dir: Path,
    min_observations: int = 3,
) -> list[KBEntry]:
    """Return KB entries meeting promotion criteria.

    Filters: confidence='high' (where field exists), observation count >= threshold,
    no existing 'Promoted:' marker. Excludes constitution.md.
    """
```

### I-2: `classify_keywords(entry: KBEntry) -> dict[str, int]`
**Module:** `plugins/pd/hooks/lib/promote_pattern/classifier.py`
```python
def classify_keywords(entry: KBEntry) -> dict[Literal['hook','skill','agent','command'], int]:
    """Return regex-match score per target. Uses Python re with IGNORECASE."""
```

### I-3: `decide_target(scores: dict) -> Optional[str]`
```python
def decide_target(scores: dict) -> Optional[Literal['hook','skill','agent','command']]:
    """Return winner if strictly highest score; None if tied or all-zero."""
```

### I-4: `generate_hook(entry: KBEntry, feasibility: dict) -> DiffPlan`
**Module:** `plugins/pd/hooks/lib/promote_pattern/generators/hook.py`
```python
def generate_hook(entry: KBEntry, feasibility: dict) -> DiffPlan:
    """Produce DiffPlan with .sh + hooks.json patch + test file.

    feasibility schema: {event, tools[], check_kind, check_expression}
    """
```

Same shape for `generate_skill`, `generate_agent`, `generate_command` with target-specific second argument (e.g., `target_meta` carrying section heading + insertion mode).

### I-5: `apply(entry, diff_plan, target_type) -> Result`
**Module:** `plugins/pd/hooks/lib/promote_pattern/apply.py`
```python
@dataclass
class Result:
    success: bool
    target_path: Optional[Path]  # repo-relative
    reason: Optional[str]        # on failure
    rolled_back: bool

def apply(entry: KBEntry, diff_plan: DiffPlan, target_type: str) -> Result:
    """Run 5-stage apply: pre-flight → snapshot → write → validate → mark KB."""
```

### I-6: `DiffPlan` and `FileEdit` dataclasses
```python
@dataclass
class FileEdit:
    path: Path                   # absolute
    action: Literal['create', 'modify']
    before: Optional[str]        # None for create
    after: str

@dataclass
class DiffPlan:
    edits: list[FileEdit]
    target_type: Literal['hook', 'skill', 'agent', 'command']
    target_path: Path            # primary target file (for KB marker)
```

### I-7: Config field
**File:** `.claude/pd.local.md` template
**Field:** `memory_promote_min_observations: 3` under `# Memory` block. Read by `enumerate_qualifying_entries`.

### I-8: Command argument shape
**Command:** `/pd:promote-pattern [<entry-name-substring>]`
- No arg: enumerate + AskUserQuestion select
- One arg: substring match against entry headings; multiple matches → disambiguate; zero matches → error
- `--help`: show usage

## Out of Scope (Design)

- **Backporting promotion for existing constitution.md entries** — constitution is hard rule already, no promotion target exists.
- **Cross-project promotion** — only operates on current project's `docs/knowledge-bank/`.
- **Reverse promotion (un-promote)** — manual KB edit suffices; no command surface.
- **Auto-promotion daemon** — explicitly out of scope per spec.

## Component Dependencies

```
promote-pattern.md (command)
  └── promoting-patterns/SKILL.md (skill)
        ├── importer.py::enumerate_qualifying_entries (extended)
        ├── promote_pattern/classifier.py
        ├── promote_pattern/generators/{hook,skill,agent,command}.py
        └── promote_pattern/apply.py
              └── invokes ./validate.sh (subprocess)
```

## Testing Strategy (preview for create-plan phase)

- **Unit:** `classifier.py` (regex scoring), `enumerate_qualifying_entries` (filter logic), each generator (deterministic templates)
- **Integration:** `apply.py` 5-stage flow with synthetic DiffPlan (snapshot, write, fake validate failure → rollback verification)
- **End-to-end (manual per Acceptance Evidence):** promote real KB pattern to each of {hook, skill, agent}; verify KB marker, target file, validate.sh pass
