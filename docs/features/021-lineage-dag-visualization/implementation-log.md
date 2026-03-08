# Implementation Log: Lineage DAG Visualization

## Phase 1: Sanitization helpers and constants (Tasks 1.1-1.3)

**Files changed:**
- NEW: `plugins/iflow/ui/tests/test_mermaid.py` — 10 tests for `_sanitize_id` (5) and `_sanitize_label` (5)
- NEW: `plugins/iflow/ui/mermaid.py` — `_sanitize_id`, `_sanitize_label`, `_ENTITY_TYPE_STYLES`, `_CURRENT_STYLE`, `_KNOWN_ENTITY_TYPES`

**Decisions:** Followed spec exactly. No deviations.

**Result:** 10/10 tests pass.

---

## Phase 2: Mermaid DAG builder function (Tasks 2.1-2.2)

**Files changed:**
- EDIT: `plugins/iflow/ui/tests/test_mermaid.py` — 12 tests for `build_mermaid_dag`
- EDIT: `plugins/iflow/ui/mermaid.py` — `build_mermaid_dag` function

**Decisions:** Followed spec exactly. Dict merge `ancestors + children + [entity]`. Click uses `href` keyword.

**Result:** 22/22 tests pass.

---

## Phase 3: Route integration (Tasks 3.1-3.3)

**Files changed:**
- EDIT: `plugins/iflow/ui/tests/test_entities.py` — `_seed_entity_with_parent` helper + 3 integration tests
- EDIT: `plugins/iflow/ui/routes/entities.py` — import `build_mermaid_dag`, depth 1→10, add `mermaid_dag` to context

**Decisions:** Updated existing test `test_entity_detail_lineage_directions` to expect depth=10 instead of 1.

**Result:** All tests pass.

---

## Phase 4: Template changes (Tasks 4.1-4.3)

**Files changed:**
- EDIT: `plugins/iflow/ui/tests/test_entities.py` — 4 template integration tests
- EDIT: `plugins/iflow/ui/templates/entity_detail.html` — `<pre class="mermaid">`, `<details>` wrapper, Mermaid CDN script

**Decisions:** Followed spec exactly. `| safe` filter used. `securityLevel: 'loose'` set.

**Result:** All 159 tests pass.

---

## Summary

- **Files created:** 2 (`mermaid.py`, `test_mermaid.py`)
- **Files modified:** 3 (`entities.py` route, `test_entities.py`, `entity_detail.html`)
- **Tests added:** 29 (22 unit + 7 integration)
- **Total test suite:** 159 passing
- **Deviations from spec:** None
