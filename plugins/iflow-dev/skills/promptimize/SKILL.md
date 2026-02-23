---
name: promptimize
description: Reviews plugin prompts against best practices guidelines and returns scored assessment with improved version. Use when user says 'review this prompt', 'improve this skill', 'optimize this agent', 'promptimize', or 'check prompt quality'.
---

# Promptimize

Review and improve plugin component prompts using structured scoring and best practices.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active in the execution context:

- **Step 8:** Auto-select "Accept all" (skip AskUserQuestion)

## Process

### Step 1: Detect component type

Identify the component type from the input path using **suffix-based matching** (the path CONTAINS the pattern, not an exact glob match -- this handles both absolute dev-workspace paths and cache paths):

| Path suffix pattern | Component type |
|---------------------|----------------|
| `skills/<name>/SKILL.md` | skill |
| `agents/<name>.md` | agent |
| `commands/<name>.md` | command |

Match rules:
1. Check if path contains `skills/` followed by a directory name and `/SKILL.md` --> type = **skill**
2. Check if path contains `agents/` followed by a filename ending in `.md` --> type = **agent**
3. Check if path contains `commands/` followed by a filename ending in `.md` --> type = **command**
4. No match --> display error: "Path must match: skills/*/SKILL.md, agents/*.md, or commands/*.md" --> **STOP**

### Step 2: Load references

Load three files using two-location Glob (try primary cache path first, fall back to dev workspace).

**2a. Scoring rubric**

- Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/promptimize/references/scoring-rubric.md`
- Fallback (dev workspace): `plugins/*/skills/promptimize/references/scoring-rubric.md`

**2b. Prompt guidelines**

- Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/promptimize/references/prompt-guidelines.md`
- Fallback (dev workspace): `plugins/*/skills/promptimize/references/prompt-guidelines.md`

**2c. Target file**

Read the file at the input path directly (absolute path provided by caller).

**Error handling:** If any reference file is not found after both Glob locations --> display error: "Required reference file not found: {filename}. Verify plugin installation." --> **STOP**

### Step 3: Check staleness

1. Parse the `## Last Updated: YYYY-MM-DD` heading from the prompt guidelines file
2. Compare the parsed date against today's date
3. If the date is **more than 30 days old**, set `staleness_warning = true`
4. This flag is used in Step 7 to append a staleness warning to the report

### Step 4: Evaluate 9 dimensions

For each dimension, apply the behavioral anchors from `references/scoring-rubric.md` (loaded in Step 2) to the target file. Produce a **pass (3) / partial (2) / fail (1)** score per dimension.

**Auto-pass exceptions** (score = 3, skip evaluation):

| Component Type | Auto-pass dimensions |
|----------------|----------------------|
| Command | persuasion_strength, prohibition_clarity, example_quality |
| Agent | progressive_disclosure |
| Skill | _(none -- all 9 evaluated)_ |

All dimension/type combinations NOT listed above are **Evaluated** using the scoring rubric's behavioral anchors.

**Dimensions** (evaluate in this order):

1. **Structure compliance** -- matches macro-structure for component type
2. **Token economy** -- under budget with no redundant content
3. **Description quality** -- trigger phrases, activation conditions, specificity
4. **Persuasion strength** -- uses persuasion principles effectively
5. **Technique currency** -- current best practices, no outdated patterns
6. **Prohibition clarity** -- specific, unambiguous constraints
7. **Example quality** -- concrete, minimal, representative examples
8. **Progressive disclosure** -- overview in main file, details in references
9. **Context engineering** -- appropriate tool restrictions, clean boundaries

For each dimension, record: **dimension name**, **score** (pass/partial/fail), and a **one-line finding** explaining the assessment.

### Step 5: Calculate score

Overall score = **(sum of all 9 dimension scores) / 27 x 100**, rounded to nearest integer.

Step 4 output (per-dimension scores and findings) feeds both this calculation and Step 6, which uses partial/fail dimensions to generate improvements.

### Step 6: Generate improved version

Rewrite the full target file incorporating improvements for every dimension scoring **partial or fail**. The output is a complete copy of the target file with changes applied inline.

**CHANGE/END CHANGE delimiters:** Wrap each modified region with paired HTML comment markers:

```markdown
<!-- CHANGE: {dimension} - {rationale} -->
{modified content}
<!-- END CHANGE -->
```

**Marker rules:**

- **Only wrap partial/fail dimensions.** Pass dimensions have NO markers -- their content remains unchanged from the original.
- **Multi-region changes** for one dimension: each region gets its own CHANGE/END CHANGE pair. They are grouped as a single selectable unit in Accept-some (keyed by dimension name).
- **Overlapping dimensions** (two dimensions modify the same text): merge into one block with both dimension names in the CHANGE comment (`<!-- CHANGE: dim_a, dim_b - rationale -->`), presented as a single inseparable selection.

**Example** (two change blocks with an unchanged pass-dimension region between):

```markdown
<!-- CHANGE: token_economy - Remove redundant preamble -->
You are a code reviewer focused on quality.
<!-- END CHANGE -->

## Process

<!-- CHANGE: structure_compliance - Add numbered steps with bold semantic labels -->
1. **Read** -- Load the target file
2. **Analyze** -- Check against criteria
<!-- END CHANGE -->
```

**Malformed marker fallback:** If CHANGE/END CHANGE parsing fails during Accept-some (markers missing, mismatched, or unparseable overlap), degrade to Accept all / Reject only with warning: "Selective acceptance unavailable -- markers could not be parsed. Use Accept all or Reject."

**Token budget check:** After generating the improved version, strip all `<!-- CHANGE: ... -->` and `<!-- END CHANGE -->` comments and count lines/tokens. If the stripped result exceeds 500 lines or 5,000 tokens, append a warning to the report: "Improved version exceeds token budget -- consider moving content to references/."

### Step 7: Generate report

Output the report using this template:

```markdown
## Promptimize Report: {filename}

**Component type:** {Skill | Agent | Command}
**Overall score:** {score}/100
**Guidelines version:** {date from prompt-guidelines.md}
{if staleness_warning: "Warning: Guidelines last updated {date} -- consider running /refresh-prompt-guidelines"}

### Strengths
- {dimension}: {what's done well}

### Issues Found

| # | Severity | Dimension | Finding | Suggestion |
|---|----------|-----------|---------|------------|
| 1 | blocker  | {dim}     | {finding} | {suggestion} |

### Improved Version

{Full rewritten prompt with CHANGE/END CHANGE block delimiters from Step 6}
```

**Strengths section:** List all dimensions scoring **pass** with a brief note on what was done well. This affirms good patterns before listing issues.

**Issues Found table:** Only partial/fail dimensions appear. Severity mapping: **fail = blocker**, **partial = warning**. Order blockers first, then warnings.

**Staleness warning:** Only shown when `staleness_warning` flag was set in Step 3.

### Step 8: User approval

Present the report from Step 7, then prompt for approval:

```
AskUserQuestion:
  questions: [{
    "question": "How would you like to proceed with the improvements?",
    "header": "Approval",
    "options": [
      {"label": "Accept all", "description": "Apply all improvements and write to file"},
      {"label": "Accept some", "description": "Choose which dimensions to apply"},
      {"label": "Reject", "description": "Discard improvements, no file changes"}
    ],
    "multiSelect": false
  }]
```

**Accept all:**
1. Take the improved version from Step 6
2. Strip all `<!-- CHANGE: ... -->` and `<!-- END CHANGE -->` comments
3. Write the result to the original file path (overwrite)
4. Display: "Improvements applied to {filename}. Run `./validate.sh` to verify structural compliance."

**Accept some:**
1. Collect the list of dimensions that have CHANGE markers in the improved version
2. Present each dimension as a multiSelect option:
   ```
   AskUserQuestion:
     questions: [{
       "question": "Select dimensions to apply:",
       "header": "Dimensions",
       "options": [
         {"label": "{dimension_name}", "description": "{one-line summary of changes for this dimension}"}
       ],
       "multiSelect": true
     }]
   ```
3. **Merge algorithm:**
   a. Start with the full improved version from Step 6
   b. For each **unselected** dimension, locate its CHANGE/END CHANGE block(s)
   c. Replace each unselected block's content with the corresponding region from the **original file** (preserved in memory from Step 2)
   d. Strip all remaining `<!-- CHANGE: ... -->` and `<!-- END CHANGE -->` markers
4. **Merge invariant:** The resulting file must be valid markdown with no orphaned CHANGE/END CHANGE markers
5. **Inseparable blocks:** If two dimensions' CHANGE blocks were merged (overlapping line ranges, as noted in Step 6), they appear as a single option with both dimension names. Selecting or deselecting applies to both dimensions together.
6. **Malformed marker fallback:** If markers cannot be cleanly parsed for selective application, degrade to Accept all / Reject with warning: "Selective acceptance unavailable -- markers could not be parsed. Use Accept all or Reject."
7. Write the merged result to the original file path (overwrite)
8. Display: "Selected improvements applied to {filename}. Run `./validate.sh` to verify structural compliance."

**Reject:**
Display: "No changes applied." --> **STOP**

**YOLO mode:** When `[YOLO_MODE]` is active, auto-select "Accept all" (skip AskUserQuestion), as specified in the YOLO Mode Overrides section above.
