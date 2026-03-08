# PRD: Lineage DAG Visualization

**Feature:** 021-lineage-dag-visualization
**Project:** P001-iflow-arch-evolution (Milestone R2-P4-Complete)
**Status:** Ready
**Created:** 2026-03-08
**Absorbed:** 022-kanban-card-click-through-navi (already implemented — cards link to detail pages)

## Problem Statement

The entity detail page displays lineage as flat bulleted lists (ancestors and children). For entities in complex hierarchies — e.g., a feature descended from a project via a brainstorm — this flat view obscures the relationship topology. Users must mentally reconstruct the graph from two disconnected lists. A visual DAG would make entity relationships immediately comprehensible.

## Goals

1. Replace the flat lineage list on entity detail pages with an interactive Mermaid.js DAG diagram
2. Make DAG nodes clickable — clicking navigates to that entity's detail page
3. Color-code nodes by entity type for quick visual parsing
4. Highlight the "current" entity node so users know their position in the graph
5. Ensure the diagram renders correctly in the existing dark theme

## Non-Goals

- Full-screen dedicated lineage page (deferred — inline section is sufficient for now)
- Editing lineage relationships from the UI
- Pagination or lazy-loading of very large graphs (entity hierarchies are small, typically <50 nodes)
- D3.js or canvas-based rendering (Mermaid.js is sufficient and simpler)
- Server-side diagram generation via MCP mermaid tool (client-side CDN is simpler for this use case)

## Dependencies

- **018-unified-iflow-ui-server-with-s** (completed) — FastAPI + Jinja2 + HTMX stack
- **020-entity-list-and-detail-views** (completed) — entity detail page with lineage data already fetched

## Technical Context

### Current State (from codebase exploration)

**Data fetching** (`plugins/iflow/ui/routes/entities.py:159-163`):
- Ancestors: `db.get_lineage(type_id, "up", 10)` — full transitive closure to root, root-first order
- Children: `db.get_lineage(type_id, "down", 1)` — direct children only (depth=1)
- Both use recursive CTEs in SQLite; the DB method supports arbitrary `max_depth`

**Entity dict fields** returned by `get_lineage()`:
`uuid, type_id, entity_type, entity_id, name, status, parent_type_id, parent_uuid, artifact_path, created_at, updated_at, metadata`

**Key field for edges:** `parent_type_id` — each entity points to its parent's `type_id`, giving us directed edges for the DAG.

### Mermaid.js Integration (from research)

**CDN:** `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs` (~760KB) — must lazy-load only on entity detail page to avoid bloating board/list pages.

**Critical gotchas:**
1. `securityLevel: 'loose'` required for click *callbacks* — we avoid this by using URL link syntax instead (see Click navigation syntax below) [Source: mermaid.js docs]
2. HTMX re-init: listen for `htmx:afterSwap` → `mermaid.run()` [Source: mostlylucid.net/blog/mermaidandhtmx]. Note: entity detail is a full-page load, so `startOnLoad: true` is sufficient. If HTMX partial navigation is added later, `htmx:afterSwap` re-init will be needed.
3. Dark theme: `theme: 'dark'` built-in; for custom colors use `theme: 'base'` with `themeVariables` + `darkMode: true` (only hex colors, no CSS vars) [Source: mermaid theming docs]
4. `mermaid.render()` returns `{ svg, bindFunctions }` — MUST call `bindFunctions(element)` after DOM injection or click handlers are silently dead [Source: mermaid.js docs]

**Click navigation syntax:**
```
click nodeId "https://..." "Tooltip" _self
```
This avoids needing `securityLevel: 'loose'` (URL links work at default security). Simpler than callback functions.

**Node styling:**
```
classDef feature fill:#1d4ed8,stroke:#3b82f6,color:#fff;
classDef project fill:#059669,stroke:#10b981,color:#fff;
class nodeId feature;
```

## Functional Requirements

### FR-1: Mermaid DAG in Entity Detail Lineage Section
Replace the current flat ancestor/children lists in `entity_detail.html` with a Mermaid.js flowchart rendering the entity's lineage as a top-down DAG.

**Acceptance Criteria:**
- AC-1: The Lineage card shows a rendered Mermaid `flowchart TD` diagram ABOVE the existing flat bullet lists. The flat lists are collapsed by default inside a `<details>` element (serves as CDN-failure fallback and accessible text alternative)
- AC-2: Each entity in the lineage appears as a labeled node showing `name or type_id`
- AC-3: Directed edges flow from parent → child (arrow points down, matching `flowchart TD`)
- AC-4: The current entity node is visually distinct (thicker border or different background)

### FR-2: Clickable Node Navigation
Clicking any node in the DAG navigates to that entity's detail page.

**Acceptance Criteria:**
- AC-5: Clicking a node navigates to `/entities/<type_id>` for that entity
- AC-6: The current entity's node is NOT clickable (or clicking it is a no-op) since you're already there
- AC-7: Hover cursor shows pointer on clickable nodes

### FR-3: Entity Type Color Coding
Nodes are color-coded by `entity_type` for quick visual parsing.

**Acceptance Criteria:**
- AC-8: `feature` nodes use one color (e.g., primary/blue)
- AC-9: `project` nodes use another color (e.g., success/green)
- AC-10: `brainstorm` nodes use another color (e.g., info/cyan)
- AC-11: `backlog` nodes use another color (e.g., ghost/gray)
- AC-12: Colors are legible against the dark theme background

### FR-4: Deeper Children Traversal
Increase children fetch depth from 1 to 10 to show the full descendant subtree in the DAG.

**Acceptance Criteria:**
- AC-13: `db.get_lineage(type_id, "down", 10)` is used instead of depth=1
- AC-14: The flat children list (if kept alongside the DAG) still shows the same data
- AC-15: Entities with many descendants render without error (the DAG may be large but functional)

### FR-5: Lazy-Load Mermaid.js
Only load the Mermaid.js library on the entity detail page, not on board or list pages.

**Acceptance Criteria:**
- AC-16: Mermaid.js `<script>` tag appears only in entity_detail.html (not in base.html)
- AC-17: Board page (`/`) does not download mermaid.js (verifiable via network tab)
- AC-18: Entity list page (`/entities`) does not download mermaid.js

### FR-6: Mermaid Diagram Generation in Python
Generate the Mermaid flowchart definition string server-side in Python and pass it to the template.

**Acceptance Criteria:**
- AC-19: A function `build_mermaid_dag(entity, ancestors, children)` returns a valid Mermaid flowchart string
- AC-20: Node IDs are sanitized via `_sanitize_id()` (replace non-alphanumeric chars with `_`, prefix with `n` if starts with digit, append short hash suffix to prevent collisions) and labels via `_sanitize_label()` (escaping `"`, `[`, `]` and other Mermaid-breaking characters)
- AC-21: The function is unit-testable independent of the web framework
- AC-22: Empty lineage (no ancestors, no children) renders a single-node diagram

## Technical Design (High-Level)

### Python: Mermaid DAG Builder

New module or function in `plugins/iflow/ui/` that takes entity + ancestors + children and produces a Mermaid flowchart string:

```python
def build_mermaid_dag(entity: dict, ancestors: list[dict], children: list[dict]) -> str:
    """Build Mermaid flowchart TD definition from lineage data.

    Required dict keys: type_id, name (optional), entity_type, parent_type_id.
    ancestors and children should NOT include the entity itself (already stripped by route).
    Data model is single-parent (tree), not general DAG — but visualization uses DAG terminology.
    """
    lines = ["flowchart TD"]

    all_entities = {e["type_id"]: e for e in ancestors + [entity] + children}

    # Node definitions with labels
    for tid, e in all_entities.items():
        safe_id = _sanitize_id(tid)
        label = _sanitize_label(e.get("name") or tid)
        lines.append(f'    {safe_id}["{label}"]')

    # Edges from parent_type_id → type_id
    for tid, e in all_entities.items():
        if e.get("parent_type_id") and e["parent_type_id"] in all_entities:
            lines.append(f'    {_sanitize_id(e["parent_type_id"])} --> {_sanitize_id(tid)}')

    # Click handlers (URL links, not callbacks — avoids securityLevel issue)
    for tid in all_entities:
        if tid != entity["type_id"]:  # Don't link current entity
            lines.append(f'    click {_sanitize_id(tid)} "/entities/{tid}"')

    # Styling by entity_type
    lines.append('    classDef feature fill:#1d4ed8,stroke:#3b82f6,color:#fff')
    lines.append('    classDef project fill:#059669,stroke:#10b981,color:#fff')
    lines.append('    classDef brainstorm fill:#0891b2,stroke:#22d3ee,color:#fff')
    lines.append('    classDef backlog fill:#4b5563,stroke:#6b7280,color:#fff')
    lines.append(f'    classDef current fill:#7c3aed,stroke:#a78bfa,color:#fff,stroke-width:3px')

    for tid, e in all_entities.items():
        cls = "current" if tid == entity["type_id"] else e.get("entity_type", "feature")
        lines.append(f'    class {_sanitize_id(tid)} {cls}')

    return "\n".join(lines)
```

### Template: Mermaid Rendering

In `entity_detail.html`, the Lineage card gets a `<pre class="mermaid">` block with the server-generated definition:

```html
<pre class="mermaid">{{ mermaid_dag }}</pre>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'dark' });
</script>
```

### Route Change

In `entities.py`, add `mermaid_dag` to the template context:

```python
from ui.mermaid import build_mermaid_dag
# ... after fetching ancestors/children ...
mermaid_dag = build_mermaid_dag(entity, ancestors, children)
```

Also change children depth from 1 to 10:
```python
child_lineage = db.get_lineage(type_id, "down", 10)  # was 1
```

## Files Modified (estimated 5 files)

| File | Changes |
|------|---------|
| `plugins/iflow/ui/mermaid.py` | **NEW** — `build_mermaid_dag()` + `_sanitize_id()` |
| `plugins/iflow/ui/routes/entities.py` | Import mermaid builder, increase children depth, add `mermaid_dag` to context |
| `plugins/iflow/ui/templates/entity_detail.html` | Replace/augment lineage section with Mermaid `<pre>` + lazy-loaded script |
| `plugins/iflow/ui/tests/test_mermaid.py` | **NEW** — unit tests for `build_mermaid_dag` |
| `plugins/iflow/ui/tests/test_entities.py` | Update integration tests for deeper children + mermaid context |

## Verification

1. Unit tests for `build_mermaid_dag()`:
   - Single entity (no lineage) → single node diagram
   - Linear chain (grandparent → parent → entity → child) → 4 nodes, 3 edges
   - Entity with multiple children → fan-out edges
   - Special characters in type_id sanitized (both ID and label)
   - Label with double quotes, brackets sanitized
   - Current entity gets `current` class, not a click handler
   - Empty name falls back to type_id

2. Integration tests:
   - Entity detail page response contains `<pre class="mermaid">`
   - Mermaid script tag present in entity detail, absent in board/list pages

3. Manual browser verification (Playwright MCP available in session):
   - Navigate to entity detail → DAG renders as SVG
   - Click a non-current node → navigates to that entity's detail
   - Verify nodes are color-coded by entity type
   - Verify current entity node is visually distinct
   - Verify hover cursor shows pointer on clickable nodes
   - Check no console errors

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Mermaid CDN unavailable | Low | Medium | Fallback: keep flat list visible below DAG; if Mermaid fails to load, list is still usable |
| Large entity graphs render slowly | Low | Low | Entity hierarchies are typically <50 nodes; Mermaid handles this easily |
| Click navigation broken by security settings | Medium | High | Use URL links (`click nodeId "url"`) instead of callbacks — works at default security level |
| Special characters in type_id break Mermaid | Medium | Medium | Sanitize IDs (replace `:`, `-` with `_`) and use quoted labels |

## Absorbed Feature: 022-kanban-card-click-through-navi

This feature was absorbed into 021. The click-through navigation from kanban cards to entity detail pages is **already implemented** — `_card.html` wraps each card in `<a href="/entities/{{ item.type_id }}">`. No additional work needed. The absorption is acknowledged and closed.
