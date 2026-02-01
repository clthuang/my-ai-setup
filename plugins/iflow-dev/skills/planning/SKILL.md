---
name: planning
description: Creates implementation plans with dependencies and sequencing. Use when ready to plan build order. Produces plan.md with ordered steps.
---

# Planning Phase

Create an ordered implementation plan.

## Prerequisites

- If `design.md` exists: Read for architecture
- If not: "No design found. Run /iflow:design first, or describe architecture now."

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### 1. Identify Work Items

From design, list everything that needs building:
- Components
- Interfaces
- Tests
- Documentation

### 2. Map Dependencies

For each item:
- What must exist before this can start?
- What depends on this?

### 3. Determine Order

Build dependency graph, then sequence:
1. Independent items (can start immediately)
2. Items with resolved dependencies
3. Items waiting on others

### 4. Estimate Complexity

Not time estimates. Complexity indicators:
- Simple: Straightforward implementation
- Medium: Some decisions needed
- Complex: Significant work or risk

## Output: plan.md

Write to `docs/features/{id}-{slug}/plan.md`:

```markdown
# Plan: {Feature Name}

## Implementation Order

### Phase 1: Foundation
Items with no dependencies.

1. **{Item}** — {brief description}
   - Complexity: Simple/Medium/Complex
   - Files: {files to create/modify}

2. **{Item}** — {brief description}
   ...

### Phase 2: Core Implementation
Items depending on Phase 1.

1. **{Item}** — {brief description}
   - Depends on: {Phase 1 items}
   - Complexity: ...
   - Files: ...

### Phase 3: Integration
Items depending on Phase 2.

...

## Dependency Graph

```
{Item A} ──→ {Item B} ──→ {Item D}
                    ↘
{Item C} ──────────→ {Item E}
```

## Risk Areas

- {Complex item}: {why it's risky}

## Testing Strategy

- Unit tests for: {components}
- Integration tests for: {interactions}

## Definition of Done

- [ ] All items implemented
- [ ] Tests passing
- [ ] Code reviewed
```

## Completion

"Plan complete. Saved to plan.md."
"Run /iflow:verify to check, or /iflow:create-tasks to break into actionable items."
