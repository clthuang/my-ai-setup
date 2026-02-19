# Spec: Memory Semantic Search (Relevance Filtering)

## Overview

Replace the metadata-only ranking in `memory.py` with context-aware relevance filtering using SQLite FTS5. Entries are selected based on what the current session is about (active feature description, current phase, recent file changes) rather than solely on observation count and confidence. Markdown files remain the source of truth; SQLite is a read-only index rebuilt on each injection.

This is Phase 3 of the cross-project persistent memory roadmap (see Feature #023 PRD, Phased Roadmap section). PRD Phase 3 envisioned a persistent index rebuilt on each retro write; this spec uses an ephemeral in-memory index rebuilt on each session start instead — simpler, no staleness detection needed, and at ~200 entries the <10ms build cost is negligible.

## Problem

The current `select_entries()` in `memory.py` ranks by observation count, confidence, and recency — with no awareness of what the session is working on. At 25 entries and a limit of 20, this barely matters (80% of entries are injected). At 100+ entries, irrelevant high-observation-count entries will crowd out contextually important low-count entries.

Example: "Don't use `find .` in hooks" (observation count 3) will always outrank "Read real file samples when parsing existing files" (observation count 1), even in a session where you're building a parser and will never touch a hook.

## Existing Code Structure

Feature #023 established `plugins/iflow-dev/hooks/lib/memory.py` (296 lines) with:
- `parse_entries(filepath, category)` — split-and-partition parser for knowledge bank markdown
- `content_hash(text)` — SHA-256 first 16 hex chars of normalized description
- `deduplicate(entries)` — by content hash, keep higher observation count
- `_sort_key(entry)` — tuple sort: `(-obs_count, -conf_val, -recency)`
- `select_entries(entries, limit)` — category-balanced selection with min-3 guarantee per non-empty category, then fill by category priority
- `format_output(selected)` — markdown block with category headers
- `write_tracking(entries, project_root, global_store)` — `.last-injection.json`
- `main()` — CLI entrypoint: `--project-root`, `--limit`, `--global-store`

`session-start.sh` calls `memory.py` via `build_memory_context()` (lines 222-248) with a 3-second timeout wrapper. Config fields `memory_injection_enabled` and `memory_injection_limit` are read from `iflow-dev.local.md`.

## Components

### Component 1: Context Signal Collection

**File:** `plugins/iflow-dev/hooks/lib/memory.py` (modify `main()`, add helpers)

**What changes:**
- Before selecting entries, collect context signals from the session environment:
  1. **Active feature description:** Scan `{project_root}/docs/features/` for directories containing `.meta.json` with `"status": "active"`. If found, extract `slug` field. If `slug` missing or `.meta.json` malformed, skip — log warning to stderr. Also attempt to read `spec.md` first paragraph (text before the first `##` heading) from the same feature directory; if file missing or unreadable, skip silently. All file reads wrapped in try/except — never raise.
  2. **Current phase:** Extract `lastCompletedPhase` from the same `.meta.json` (if available). If field missing or null, skip phase signal. Phase name is used as a context keyword (e.g., "design", "implement").
  3. **Recent file paths:** New helper `collect_git_signals(project_root)` runs `git -C {project_root} diff --name-only HEAD~3..HEAD 2>/dev/null`. Splits each path on `/` and `.`, extracts path segments and extensions as domain keywords. Max 20 keywords total (truncate after 20). Skip dotfiles (paths starting with `.` or containing `/.`). Example: `plugins/hooks/lib/memory.py` → `["plugins", "hooks", "lib", "memory", "py"]`. Edge cases: (a) `HEAD~3` doesn't exist (< 3 commits) → try `HEAD~1..HEAD`; if that also fails (< 2 commits), return `[]`. Do NOT attempt to diff initial commit against empty tree. (b) git not installed or not a repo → return empty list, log to stderr. (c) detached HEAD → return empty list. All failures return `[]` — never raise.
- New helper `collect_context_signals(project_root)` orchestrates all three signal sources and returns a combined `context_query` string: space-separated, deduplicated words. Note: PRD Phase 3 mentions "filter by detected project language/domain" — this is achieved implicitly via git diff file extensions (`.py`, `.sh`, `.ts`) and feature description keywords, without a dedicated language detection step.
- If multiple active features exist, use the one with the most recently modified `.meta.json` (consistent with session-start.sh behavior).
- If `context_query` is empty after collection: fall back to current metadata-only ranking (pure prominence).

### Component 2: SQLite FTS5 Index

**File:** `plugins/iflow-dev/hooks/lib/memory.py` (new function)

**What changes:**
- New function `build_fts_index(entries)`: Creates an in-memory SQLite database with FTS5 virtual table. Schema:
  ```sql
  CREATE VIRTUAL TABLE entries_fts USING fts5(
    name,
    description,
    category,
    metadata_text,
    content_hash UNINDEXED
  );
  ```
- Inserts all parsed entries (from both local and global stores, post-dedup) into the FTS5 table.
- Returns the `sqlite3.Connection` object for use by `score_relevance()`.
- The index is ephemeral — built fresh on each session start, not persisted to disk. This avoids index staleness and file management complexity.

**Why in-memory:** At ~200 entries, building an in-memory FTS5 index takes <10ms. Persisting to disk adds complexity (staleness detection, rebuild triggers, file locking) for negligible performance gain. Revisit if corpus exceeds ~2,000 entries.

**FTS5 availability check:** Wrap `CREATE VIRTUAL TABLE` in try/except. If FTS5 is not compiled into the sqlite3 module (raises `OperationalError`), log warning to stderr and return `None`. Callers treat `None` connection as "FTS5 unavailable" and fall back to prominence-only ranking.

### Component 3: Relevance-Aware Selection

**File:** `plugins/iflow-dev/hooks/lib/memory.py` (modify `select_entries()`, add `score_relevance()`)

**What changes:**

**New function `score_relevance(entries, context_query, db_connection)`:**
1. Sanitize `context_query` for FTS5 MATCH syntax: split into individual words, strip non-alphanumeric characters, filter out empty strings, rejoin with `OR` operator. Example: `"memory-semantic search/parser"` → `"memory OR semantic OR search OR parser"`. This prevents FTS5 syntax errors from special characters. If the sanitized query is empty (all words stripped), treat as `context_query=None` and fall back to prominence-only ranking.
2. Run FTS5 MATCH query with sanitized query string.
3. Retrieve BM25 relevance scores via `bm25(entries_fts)`. **Important:** SQLite FTS5 `bm25()` returns *negative* values where *more negative = more relevant*. Negate the values so higher = more relevant.
4. Return a dict mapping `content_hash → relevance_score` (0.0 for non-matching entries).

**New function `compute_prominence(entries)`:**
Replace the existing `_sort_key()` tuple-sort with a normalized scalar score:
```
prominence_score = (obs_count / max_obs_count) * 0.5 + (conf_val / 3.0) * 0.3 + (recency_rank / max(entry_count - 1, 1)) * 0.2
```
Where:
- `max_obs_count` = max observation count across all entries (min 1 to avoid division by zero)
- `conf_val` = {high: 3, medium: 2, low: 1}
- `recency_rank` = position in recency-sorted order (0 = oldest, N-1 = newest), using the same recency logic as existing `_sort_key()` (ISO date for global entries, file position for local)

**Behavioral note:** This changes the ranking semantics from lexicographic (obs_count dominates absolutely) to weighted blend (recency can compensate for lower obs_count). This is intentional — at scale, a recent low-observation entry may be more relevant than a stale high-observation one.

**Modify `select_entries()`** to accept optional `context_query`, `db_connection`, and `relevance_weight` parameters:
- New blended scoring formula:
  ```
  final_score = (relevance_weight * relevance_score) + ((1 - relevance_weight) * prominence_score)
  ```
  Where:
  - `relevance_score` = negated BM25 score normalized to [0.0, 1.0] by dividing each score by the max score in the result set. If no entries match `context_query` (all BM25 = 0), all relevance scores are 0.0 and selection degrades to pure prominence. When few entries match, normalization creates a sharp score gap between matching and non-matching entries — this is intentional (a single relevant match should score maximally relative to non-matches).
  - `prominence_score` = scalar in [0.0, 1.0] per formula above
  - `relevance_weight` = 0.6 (configurable via `memory_relevance_weight` in `iflow-dev.local.md`)
- When `context_query` is empty/None or `db_connection` is None: fall back to pure prominence ranking. This preserves backward compatibility for sessions with no active feature.
- **Category balance with blended scoring:** The min-3 guarantee per non-empty category still applies. Within each category bucket, entries are sorted by `final_score` descending (instead of the old `_sort_key` tuple). After min-3 allocation, remaining slots are filled by `final_score` descending across all remaining entries regardless of category. This replaces the old "fill by category priority" with "fill by blended score" — relevance-aware backfill.
- When `relevance_weight` is 0.0 (pure prominence), the old `_sort_key` tuple-based sorting is NOT preserved — prominence_score uses a weighted sum which produces a different ordering. This is acceptable because the weighted prominence more accurately reflects entry value than absolute lexicographic sorting.

### Component 4: Configuration Extension

**File:** `plugins/iflow-dev/templates/iflow-dev.local.md`

**What changes:**
- Add new config field to template: `memory_relevance_weight: 0.6` with comment `# 0.0 = pure prominence ranking, 1.0 = pure relevance`

**File:** `plugins/iflow-dev/hooks/session-start.sh` (modify `build_memory_context()`)

**What changes:**
- Read `memory_relevance_weight` from config via `read_local_md_field "$config_file" "memory_relevance_weight" "0.6"`
- Pass `--relevance-weight "$weight"` to the `memory.py` invocation

**File:** `plugins/iflow-dev/hooks/lib/memory.py` (modify CLI args in `main()`)

**What changes:**
- New CLI arg `--relevance-weight` (default 0.6). Validation: parse with `float()` in try/except; if non-numeric or outside [0.0, 1.0], log stderr warning `"Invalid relevance weight '{value}', using default 0.6"` and fall back to 0.6. Never fatal — always exit 0 with valid output.

### Component 5: Diagnostic Output

**File:** `plugins/iflow-dev/hooks/lib/memory.py` (modify `format_output()`)

**What changes:**
- Extend `format_output()` signature to accept `local_count`, `global_count`, `relevance_weight`, and `context_query` parameters.
- Always append a diagnostic line at the end of the injected markdown block (after the `---`), visible to model:
  - When relevance scoring active (weight > 0 and context_query non-empty): `*Memory: {N} entries ({local_count} local, {global_count} global) | relevance: active, weight={weight} | context: "{context_query_first_30_chars}..."*` (append `...` only if original exceeds 30 characters)
  - When relevance inactive (weight = 0 or context_query empty or FTS5 unavailable): `*Memory: {N} entries ({local_count} local, {global_count} global) | relevance: inactive*`
- Purpose: Model awareness of filtering mode + human debugging.

## Acceptance Criteria

1. **Relevance boost measurable:** Given a programmatic 30-entry test fixture (constructed in-test: all entries in the same category "patterns" to eliminate category-balance confounds; 10 entries with "parser" in name/description, 20 entries about unrelated topics like "hooks", "git", "deployment" — all with observation count 2, confidence medium; parser entries assigned lower file_position values so they rank in the bottom half by prominence), and context_query = "parser file reading", at least 7 of the 10 parser-related entries appear in the top 20 selected entries. Without relevance scoring (weight=0.0), fewer than 5 of those 10 appear (because prominence ranking ignores content match).
2. **Fallback consistency:** When `context_query` is None, `select_entries()` returns entries ranked purely by prominence_score (no relevance component). Test: call `select_entries(entries, limit)` with `context_query=None` and separately with `relevance_weight=0.0` — both produce identical entry names and order. Note: this ordering differs from the old `_sort_key` lexicographic sort — the weighted prominence formula is intentionally different (see Component 3 behavioral note).
3. **In-memory only:** No `.db`, `.sqlite`, or index file is created on disk. Test: `ls` the project and global store directories before and after invocation, verify no new files.
4. **Timeout safety:** (a) Normal path: `memory.py` on a 200-entry fixture completes in <500ms on developer machine (informational benchmark, not a CI gate — the 3-second timeout in `session-start.sh` is the hard safety limit). (b) If timeout fires (e.g., git hangs): `session-start.sh` continues with empty memory output, hook JSON remains valid. (c) If FTS5 is unavailable: `memory.py` falls back to prominence-only ranking with stderr warning, exits 0.
5. **Config works:** `memory_relevance_weight: 0.0` produces pure prominence ranking. `memory_relevance_weight: 1.0` produces pure relevance ranking. Both produce valid output with no errors.
6. **Limit respected:** Total injected entries never exceed `memory_injection_limit` regardless of relevance scores.
7. **Category balance preserved:** At least 3 entries per non-empty category when limit >= 9 (3 categories x 3).
8. **`./validate.sh` passes** including `python3 -m py_compile plugins/iflow-dev/hooks/lib/memory.py`.
9. **Existing hook integration tests pass** unchanged.

## Scope Boundaries

### In Scope
- FTS5-based relevance scoring using context signals from active feature + git history
- Blended ranking (relevance + prominence)
- Configuration for relevance weight
- Diagnostic comment in output
- Backward-compatible fallback when no context signals exist
- Refactoring `_sort_key()` into normalized `compute_prominence()` scalar

### Out of Scope
- Embedding-based semantic search (vector similarity) — that's Phase 4/MCP territory
- Persistent SQLite database on disk — in-memory only for this phase
- Mid-session memory queries (pull-based retrieval) — session-start injection only
- Tag/label system for entries — FTS5 full-text search makes explicit tags unnecessary
- Changes to the knowledge bank file format — markdown remains source of truth
- Changes to the retrospective workflow — entry writing/promotion stays the same
- Changes to `build_memory_context()` beyond adding the new CLI arg pass-through
- Persistent index rebuilt on retro write (PRD Phase 3 original approach) — replaced with ephemeral in-memory index per Overview rationale

## Technical Constraints

- **Python stdlib only.** `sqlite3` with FTS5 ships with Python 3.9+ on macOS and Linux. No pip dependencies.
- **3-second timeout budget.** Context signal collection + index build + FTS5 query + selection must complete within the existing `timeout 3` wrapper in `session-start.sh`. At ~200 entries, in-memory FTS5 build is <10ms and query is <1ms. Git subprocess is the largest variable — capped by the 3s timeout on the entire `memory.py` process.
- **Graceful degradation.** If SQLite import fails or FTS5 is unavailable (rare but possible on minimal Python builds): fall back to prominence-only ranking with a stderr warning, never crash. If git is unavailable: context signals are empty, falls back to pure prominence.

## Prerequisites (Verified)

- Feature #023 (cross-project persistent memory) — shipped in v2.11.0. Verified:
  - `~/.claude/iflow/memory/` global store exists with 6 entries across 3 files
  - `memory.py` parses, deduplicates, and injects entries at session start
  - `session-start.sh` calls `memory.py` with 3-second timeout wrapper
  - Retrospective Step 4c promotes universal entries to global store
- `lastCompletedPhase` field exists in all feature `.meta.json` files — populated by workflow-transitions skill's `commitAndComplete()` function since Feature #002. Value is `null` for new features, set to phase name on completion.
- Python 3.9+ with sqlite3 module. FTS5 is typically available on macOS/Linux default Python but not guaranteed on all builds — graceful fallback to prominence-only ranking if unavailable (see Component 2).
- Active feature discovery: `docs/features/{id}-{slug}/.meta.json` with `"status": "active"` — standard iflow convention used by all phase commands. Note: `memory.py` reimplements this discovery in Python (independent from `session-start.sh`'s bash+python inline version). Both use the same `.meta.json` convention. Duplication is acceptable because `memory.py` must be callable independently as a CLI tool.

## Dependencies

- Python 3.9+ with sqlite3 + FTS5 (ships with macOS/Linux default Python)
