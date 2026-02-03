---
name: retrospecting
description: Automatically captures learnings from completed features into knowledge bank using subagents. Use when reflecting on completed work.
---

# Retrospective

Automatic learning capture using investigation-agent.

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context

## Process

### Step 1: Gather Context via Subagent

Dispatch investigation-agent to gather retrospective data:

```
Task tool call:
  description: "Gather feature learnings"
  subagent_type: iflow-dev:investigation-agent
  prompt: |
    Gather retrospective data for feature {id}-{slug}.

    Read:
    - Feature folder contents (docs/features/{id}-{slug}/)
    - Git log for this branch
    - .review-history.md if exists
    - Any blockers/issues encountered

    Identify:
    - What went well
    - What could improve
    - Patterns worth documenting
    - Anti-patterns to avoid

    Return structured findings as JSON:
    {
      "what_went_well": [...],
      "what_could_improve": [...],
      "patterns": [...],
      "anti_patterns": [...],
      "heuristics": [...]
    }
```

### Step 2: Process Findings

Based on investigation-agent output, categorize learnings:

| Category | Description | Target File |
|----------|-------------|-------------|
| Patterns | Approaches that worked well | docs/knowledge-bank/patterns.md |
| Anti-Patterns | Approaches to avoid | docs/knowledge-bank/anti-patterns.md |
| Heuristics | Decision guides discovered | docs/knowledge-bank/heuristics.md |
| Principles | Core principles reinforced | docs/knowledge-bank/principles.md |

### Step 3: Write Retrospective

Write `docs/features/{id}-{slug}/retro.md`:

```markdown
# Retrospective: {Feature Name}

## What Went Well
- {From investigation findings}

## What Could Improve
- {From investigation findings}

## Learnings Captured
- {Patterns/anti-patterns identified}

## Knowledge Bank Updates
- {If any patterns added to knowledge-bank/}
```

### Step 4: Update Knowledge Bank

For significant learnings (patterns, anti-patterns, heuristics):

1. Read current knowledge bank file
2. Add new entry with reference to feature
3. Save file

Example entry:
```markdown
### Pattern: {Name}
{Description}
- Observed in: Feature {id}-{slug}
- Benefit: {Why it worked}
```

### Step 5: Commit

```bash
git add docs/features/{id}-{slug}/retro.md docs/features/{id}-{slug}/.meta.json docs/knowledge-bank/
git commit -m "docs: add retrospective for feature {id}-{slug}"
git push
```

## Output

```
Retrospective complete.
Updated: {list of knowledge-bank files updated}
Saved to retro.md.
```

## Automatic Execution

This skill runs automatically during `/iflow-dev:finish`:
- No permission prompt required
- Findings drive knowledge bank updates
- User sees summary of learnings captured
