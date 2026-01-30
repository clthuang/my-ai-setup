---
name: designing
description: Creates architecture and interface definitions. Use when designing technical approach. Produces design.md with architecture, interfaces, and contracts.
---

# Design Phase

Design the technical architecture.

## Prerequisites

- If `spec.md` exists: Read for requirements
- If not: "No spec found. Run /specify first, or describe requirements now."

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification

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
"Run /verify to check, or /create-plan to continue."
