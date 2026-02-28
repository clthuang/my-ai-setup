---
description: Review a plugin prompt against best practices and return an improved version
argument-hint: "[file-path]"
---

# /iflow:promptimize Command

## Input Flow

### Step 1: Check for direct path argument

If `$ARGUMENTS` contains a file path, skip to Step 2.5 (Read original file).

### Step 2: Interactive component selection

If no arguments provided:

**2a. Select component type:**

```
AskUserQuestion:
  questions: [{
    "question": "What type of component would you like to review?",
    "header": "Component",
    "options": [
      {"label": "Skill", "description": "Review a skill SKILL.md file"},
      {"label": "Agent", "description": "Review an agent .md file"},
      {"label": "Command", "description": "Review a command .md file"}
    ],
    "multiSelect": false
  }]
```

**2b. Discover matching files using two-location Glob:**

Based on the selected component type, search for files:

- **Skill:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/*/SKILL.md`
  - Fallback (dev workspace): `plugins/*/skills/*/SKILL.md`

- **Agent:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/agents/*.md`
  - Fallback (dev workspace): `plugins/*/agents/*.md`

- **Command:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/commands/*.md`
  - Fallback (dev workspace): `plugins/*/commands/*.md`

Use the primary Glob first. If it returns zero results, use the fallback.

**2c. Handle empty results:**

If no files found from either location, display:

```
No {type} files found. Expected location: {glob pattern}. Verify plugin installation or check working directory.
```

Then STOP.

**2d. Present file selection:**

If `[YOLO_MODE]` is active, auto-select the first match (skip AskUserQuestion for file selection).

Otherwise, present matching files for user selection:

```
AskUserQuestion:
  questions: [{
    "question": "Which {type} would you like to review?",
    "header": "Select File",
    "options": [
      {"label": "{filename-1}", "description": "{full-path-1}"},
      {"label": "{filename-2}", "description": "{full-path-2}"}
    ],
    "multiSelect": false
  }]
```

List each discovered file as an option, using the filename as the label and the full path as the description.

### Step 2.5: Read original file

Read the target file at the resolved path from Step 1 or Step 2d. Store the full content as `original_content`.

If the file read fails, display: "Error: could not read target file at {path}." STOP.

### Step 3: Invoke skill

The skill performs full path validation in its Step 1.

```
Skill(skill: "iflow:promptimize", args: "<selected-path>")
```

Where `<selected-path>` is the file path from Step 2d (interactive) or `$ARGUMENTS` (direct).

The skill output appears in conversation context containing `<phase1_output>` and `<phase2_output>` sections. Subsequent steps parse these sections.

---

## Orchestration

### Step 4: Parse skill output

**4a. Extract Phase 1 JSON:**

Extract the content between `<phase1_output>` and `</phase1_output>` tags from the skill output. Parse the extracted text as JSON.

**4b. Extract Phase 2 content:**

Extract the content between `<phase2_output>` and `</phase2_output>` tags from the skill output. Store as Phase 2 content (the complete rewritten file with `<change>` tags).

**4c. Validate Phase 1 JSON:**

Validate the parsed JSON against the Phase 1 schema:

1. `dimensions` array must contain exactly 9 entries.
2. Each dimension `score` must be an integer: 1, 2, or 3.
3. Each dimension must have non-empty `name`, `finding`, and `score` fields.
4. Each `name` must be one of the 9 canonical dimension names:
   - `structure_compliance`
   - `token_economy`
   - `description_quality`
   - `persuasion_strength`
   - `technique_currency`
   - `prohibition_clarity`
   - `example_quality`
   - `progressive_disclosure`
   - `context_engineering`
5. Suggestion constraint: if `score < 3` then `suggestion` must be non-null (a string). If `score == 3` then `suggestion` must be null.
6. `component_type`, `guidelines_date`, and `staleness_warning` fields must be present.

If any parsing or validation fails, display:

```
Phase 1 JSON validation failed: {reason}. Raw output snippet: {first 200 chars}
```

Then STOP.

### Step 5: Compute score

Sum all 9 dimension scores from the Phase 1 JSON `dimensions` array.

Compute the overall score: `round((sum / 27) * 100)` to the nearest integer.

Store as `overall_score`.

Example: scores [3, 2, 1, 3, 2, 3, 3, 3, 2] --> sum = 22, overall_score = round((22/27) * 100) = 81.

### Step 6a: Validate change tag structure

Parse the Phase 2 content line by line. Track code fence state:

- Maintain a boolean `in_fence`, initially false.
- Toggle `in_fence` on lines starting with three or more backticks (`` ``` ``) or three or more tildes (`~~~`).
- While `in_fence` is true, ignore any `<change>` or `</change>` patterns on those lines.

Use regex patterns to find change tags (outside code fences only):

- **Open tag:** `<change\s+dimension="([^"]+)"\s+rationale="([^"]*)">`
- **Close tag:** `</change>`

Validation checks:

1. Every `<change ...>` tag has a corresponding `</change>` tag.
2. `<change>` tags are not nested (no open tag before the previous one is closed).
3. Tag pairs do not overlap with other tag pairs.
4. Each `<change>` tag has a non-empty `dimension` attribute.

If validation passes, build an array of **ChangeBlock** structures from the matched tag pairs:

```
ChangeBlock {
  dimensions: string[]        # parsed from dimension attribute (split on comma)
  rationale: string           # from rationale attribute
  content: string             # text between <change> and </change>
  before_context: string[]    # up to 3 non-tag lines before <change> tag in Phase 2 output
  after_context: string[]     # up to 3 non-tag lines after </change> tag in Phase 2 output
}
```

For `before_context`: collect up to 3 lines immediately preceding the `<change>` tag line in the Phase 2 output (fewer if near file start).

For `after_context`: collect up to 3 lines immediately following the `</change>` tag line in the Phase 2 output (fewer if near file end or if the next `<change>` tag is within 3 lines).

If validation fails (including zero matches from the open-tag regex, which occurs with reversed attribute order like `<change rationale="..." dimension="...">`): set `tag_validation_failed = true`.

---

## Sub-procedure: match_anchors_in_original

**Inputs:**
- A ChangeBlock (or array of ChangeBlocks when merge-adjacent is true) with `before_context` and `after_context`
- `original_content` lines (from Step 2.5)
- `merge_adjacent` flag (default: false)

**When merge-adjacent is true:** Before matching, scan the ChangeBlock array for adjacent blocks whose context anchor windows overlap (i.e., the after_context of block N and before_context of block N+1 share lines). Merge adjacent blocks into a single logical region: use the before_context of the first block in the group and the after_context of the last block in the group as the outer anchors.

**Matching algorithm:**

1. Search `original_content` for a contiguous sequence of lines matching the `before_context` lines. If `before_context` has 0 lines (change at file start), skip before-anchor matching and anchor at line 0.
2. Search `original_content` for a contiguous sequence of lines matching the `after_context` lines, occurring after the before-anchor position. If `after_context` has 0 lines (change at file end), skip after-anchor matching and anchor at the last line.
3. The matched region is the span of original lines between the end of the before-context match and the start of the after-context match.

**Edge cases:**
- File start: 0-2 before-context lines available. Match uses only the available lines.
- File end: 0-2 after-context lines available. Match uses only the available lines.
- Both anchors empty: match is ambiguous -- return `{ matched: false, reason: "no context anchors available" }`.

**Returns:**
- On unique match: `{ matched: true, start_line, end_line }` where start_line and end_line are 0-based line indices in `original_content` identifying the region between anchors.
- On zero matches: `{ matched: false, reason: "before/after context not found in original" }`.
- On multiple matches: `{ matched: false, reason: "context anchors matched multiple locations" }`.
- On overlapping anchor regions between blocks: `{ matched: false, reason: "overlapping anchor regions" }`.

---

### Step 6b: Drift detection

**Skip this step if `tag_validation_failed` is true** (tags cannot be reliably parsed).

For each ChangeBlock from Step 6a, call `match_anchors_in_original` with merge-adjacent=true to locate the before/after context anchors in `original_content`.

If any anchor match fails, set `drift_detected = true` (cannot verify drift without anchor positions).

If all anchors match:

1. Reconstruct the file: replace each `<change>` block in Phase 2 content with the matched original text between the anchors (the original lines from `start_line` to `end_line`).
2. Normalize both the reconstructed content and `original_content`:
   - Strip trailing whitespace from each line.
   - Ignore blank-line differences at file boundaries (leading/trailing blank-line runs).
3. Compare the normalized reconstructed content to the normalized `original_content`.
4. If they differ: set `drift_detected = true`.

### Step 6c: Token budget check

Strip all `<change ...>` opening tags and `</change>` closing tags from the Phase 2 content.

Count the number of lines and words in the stripped content.

If the stripped content exceeds 500 lines or 5,000 words: set `over_budget_warning = true`.

### Step 7: Assemble report

Build the report from structured data. Do NOT ask the LLM to generate the report narrative -- assemble it mechanically from the following template:

```markdown
## Promptimize Report

**Component type:** {component_type from Phase 1 JSON}
**Overall score:** {overall_score}/100
**Guidelines version:** {guidelines_date from Phase 1 JSON}
```

**Staleness warning** (include only if `staleness_warning` is true from Phase 1 JSON):

```markdown
> Warning: Prompt guidelines are stale (last updated {guidelines_date}). Scores may not reflect current best practices.
```

**Over-budget warning** (include only if `over_budget_warning` is true):

```markdown
> Warning: Improved version exceeds budget thresholds (500 lines or 5,000 words). Review for unnecessary additions.
```

**Strengths section:**

List dimensions that scored pass (3) AND are NOT auto-passed. If none, omit this section.

```markdown
### Strengths
- **{Dimension name}**: {finding}
```

**Issues table:**

List dimensions scoring partial (2) or fail (1). Sort blockers (fail) first, then warnings (partial).

```markdown
### Issues

| Severity | Dimension | Finding | Suggestion |
|----------|-----------|---------|------------|
| blocker  | {name}    | {finding} | {suggestion} |
| warning  | {name}    | {finding} | {suggestion} |
```

If no issues exist, omit this section.

**Improved Version section:**

```markdown
### Improved Version

{Phase 2 output verbatim}
```

Display the assembled report.

---

## Approval and Merge

### Step 8: User approval

**8a. Determine approval path:**

- If `overall_score == 100` AND zero ChangeBlocks from Step 6a: display "All dimensions passed -- no improvements needed." STOP.
- If `overall_score == 100` BUT ChangeBlocks exist: display warning "Warning: Score is 100 but change blocks were found -- this may indicate a grading error." Then proceed to the approval menu with standard option-gating below.
- If `overall_score < 100` BUT zero ChangeBlocks: display the report with note: "Note: Dimensions scored partial/fail but no changes were generated." STOP.
- If `[YOLO_MODE]` is active: auto-select "Accept all" and proceed directly to the Accept all handler. Skip AskUserQuestion.

**8b. Present approval menu (non-YOLO):**

Determine which options to present:

- **Always available:** "Accept all", "Reject"
- **Conditionally available:** "Accept some" -- only when `tag_validation_failed == false` AND `drift_detected == false`

If "Accept some" is unavailable, display the relevant warning:
- Tag validation failure: "Partial acceptance unavailable: `<change>` tag structure is malformed."
- Drift detected: "Partial acceptance unavailable: text outside change blocks differs from original."

Present using AskUserQuestion. If "Accept some" is available:

```
AskUserQuestion:
  questions: [{
    "question": "How would you like to proceed?",
    "header": "Approval",
    "options": [
      {"label": "Accept all", "description": "Apply all improvements to the file"},
      {"label": "Accept some", "description": "Choose which dimensions to apply"},
      {"label": "Reject", "description": "Discard all improvements"}
    ],
    "multiSelect": false
  }]
```

If "Accept some" is NOT available:

```
AskUserQuestion:
  questions: [{
    "question": "How would you like to proceed?",
    "header": "Approval",
    "options": [
      {"label": "Accept all", "description": "Apply all improvements to the file"},
      {"label": "Reject", "description": "Discard all improvements"}
    ],
    "multiSelect": false
  }]
```

**8c. Execute selected action:**

#### Accept all handler

Take the Phase 2 output. Strip all `<change ...>` opening tags and `</change>` closing tags via regex.

Write the stripped content to the original file path (overwrite).

Display: "Improvements applied to {filename}. Run `./validate.sh` to verify."

STOP.

#### Accept some handler

**Part 1 -- Dimension selection:**

Collect the unique set of dimension groups from the ChangeBlock array. Overlapping dimensions (comma-separated in `dimension` attribute, e.g., `token_economy,structure_compliance`) are presented as a single inseparable option.

Present dimension selection:

```
AskUserQuestion:
  questions: [{
    "question": "Which dimensions would you like to apply?",
    "header": "Select Dimensions",
    "options": [
      {"label": "{dimension_name}", "description": "{rationale}"},
      {"label": "{dim1, dim2}", "description": "{rationale}"}
    ],
    "multiSelect": true
  }]
```

**Part 2 -- Anchor matching:**

Start from `original_content` (Step 2.5).

For each ChangeBlock belonging to a selected dimension: call `match_anchors_in_original` (sub-procedure above) with merge-adjacent=true to locate the anchor region in `original_content`.

If anchor match fails for any block: display "Partial acceptance unavailable: could not uniquely match change regions to original file." Degrade to Accept all / Reject by re-presenting the two-option AskUserQuestion menu.

**Part 3 -- Replacement assembly:**

Collect `(start_line, end_line, replacement_content)` tuples for all ChangeBlocks belonging to selected dimensions. The `replacement_content` is the content between the `<change>` and `</change>` tags for that block.

Sort tuples by `start_line` ascending.

Verify no overlapping regions. Overlap check uses closed interval: blocks overlap if `tuple[i].start_line <= tuple[i-1].end_line`. If overlap detected: display warning and degrade to Accept all / Reject.

All replacements are computed against `original_content` simultaneously (not sequentially) to avoid line-offset drift.

**Part 4 -- Assembly and write:**

Build the output by interleaving original content with replacements:

1. For each gap between replacements (and before the first / after the last), include the corresponding lines from `original_content`.
2. For each selected replacement tuple, include the `replacement_content` in place of the original lines from `start_line` to `end_line`.
3. Unselected dimensions: their regions retain the original text from `original_content` (no replacement applied).

Strip any residual `<change>` tags from the assembled output (defensive final pass -- should be none after the replacement pass, but ensures no stray tags).

Write the assembled content to the original file path.

Display: "Selected improvements applied to {filename}. Run `./validate.sh` to verify."

STOP.

#### Reject handler

Display "No changes applied." STOP.

---

## PROHIBITED

- NEVER write improvements without user approval via AskUserQuestion (Step 8). Exception: YOLO mode auto-selects Accept all.
- NEVER skip the approval step in non-YOLO mode.
- NEVER present Accept some when `tag_validation_failed` or `drift_detected` is true.
