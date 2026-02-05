---
name: designing
description: Creates design.md with architecture and contracts. Use when the user says 'design the architecture', 'create technical design', 'define interfaces', or 'plan the structure'.
---

# Design Phase

Design the technical architecture.

## Prerequisites

- If `spec.md` exists: Read for requirements
- If not: "No spec found. Run /iflow:specify first, or describe requirements now."

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Stage Parameter

The design command may invoke this skill with a `stage` parameter to produce specific sections:

| Stage | Sections Produced | Use Case |
|-------|-------------------|----------|
| `architecture` | Architecture Overview, Components, Technical Decisions, Risks | First pass - structure and decisions |
| `interface` | Interfaces (detailed contracts) | Second pass - precise contracts |
| (none/default) | All sections | Backward compatibility |

When `stage=architecture`:
- Focus on high-level structure and component boundaries
- Define what each component does, not the precise API
- Identify technical decisions and risks early

When `stage=interface`:
- Read existing design.md for component definitions
- Add detailed interface contracts with exact formats
- Define error cases and edge cases precisely

When no stage specified:
- Produce complete design in one pass (existing behavior)

## Process

### 1. Architecture Overview

High-level design:
- Components involved
- How they interact
- Data flow

Keep it simple (KISS). One diagram if helpful.

### 2. Interface Definitions

For each component boundary:
- Input format
- Output format
- Error cases

Define contracts before implementation.

### 3. Technical Decisions

For significant choices:
- Decision
- Options considered
- Rationale

### 4. Risk Assessment

- What could go wrong?
- How do we mitigate?

## Output: design.md

Write to `docs/features/{id}-{slug}/design.md`:

```markdown
# Design: {Feature Name}

## Architecture Overview

{High-level description}

```
[Simple diagram if helpful]
```

## Components

### {Component 1}
- Purpose: {what it does}
- Inputs: {what it receives}
- Outputs: {what it produces}

### {Component 2}
...

## Interfaces

### {Interface 1}
```
Input:  {format}
Output: {format}
Errors: {error cases}
```

### {Interface 2}
...

## Technical Decisions

### {Decision 1}
- **Choice:** {what we decided}
- **Alternatives:** {what we considered}
- **Rationale:** {why this choice}

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| {Risk 1} | {Impact} | {Mitigation} |

## Dependencies

- {Technical dependency}
```

## Self-Check

- [ ] KISS: Is this the simplest design that works?
- [ ] Interfaces defined before implementation?
- [ ] No over-engineering?

## Completion

"Design complete. Saved to design.md."
"Run /iflow:verify to check, or /iflow:create-plan to continue."
