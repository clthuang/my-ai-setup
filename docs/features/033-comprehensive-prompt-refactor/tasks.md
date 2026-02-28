# Tasks: Comprehensive Prompt Refactoring

## Legend
- **Status**: `[ ]` pending, `[x]` done, `[~]` in-progress
- **Deps**: Task IDs that must complete first
- **Group**: Tasks with same group letter can run in parallel
- **Why**: Plan step and success criteria this task implements

---

## Phase 0: Baseline Capture

### T01: Run promptimize baseline on 5 pilot files [Group: A]
- **Deps**: none
- **Why**: Plan Step 0.1 / SC-1 — establish pre-refactor quality scores for comparison
- **Files**: `plugins/iflow/agents/design-reviewer.md`, `plugins/iflow/commands/secretary.md`, `plugins/iflow/skills/brainstorming/SKILL.md`, `plugins/iflow/commands/review-ds-code.md`, `plugins/iflow/commands/review-ds-analysis.md`
- **Action**: Run `/iflow:promptimize` on each of the 5 pilot files. Record scores in `docs/features/033-comprehensive-prompt-refactor/baseline-scores.md`.
- **Done**: `baseline-scores.md` exists with 5 numeric scores (one per pilot file).
- [ ] Status

### T02: Capture representative test outputs for pilot files
- **Deps**: T01
- **Why**: Plan Step 0.1 / AC-13 — capture pre-refactor behavioral outputs for equivalence comparison
- **Files**: Same 5 pilot files as T01
- **Action**: For each pilot file, run with representative inputs and capture outputs. Inputs must be concrete and reproducible:
  - `design-reviewer.md`: Provide a 200-word feature design document with 3 components, 2 interfaces, and 1 missing dependency → capture JSON output (approval decision + issues array)
  - `secretary.md`: Run 5 routing prompts: (1) "review auth for security issues" (direct agent), (2) "help" (help subcommand), (3) "make the app better" (ambiguous), (4) "orchestrate build login" (orchestrate), (5) "translate to French" (no-match) → capture agent selection per prompt
  - `brainstorming/SKILL.md`: Provide topic "Add rate limiting to API endpoints" → capture stage progression through Stage 1-3
  - `review-ds-code.md`: Provide a notebook description with 3 anti-patterns (global imports, no docstrings, hardcoded paths) and 2 correct patterns → capture JSON output
  - `review-ds-analysis.md`: Provide an analysis description with 1 p-hacking instance, 1 missing confidence interval, and 1 correct methodology → capture JSON output
- **Done**: All 5 baseline outputs recorded in `baseline-outputs.md` (separate from scores).
- [ ] Status

### T03: Store reproducible test inputs [Group: B]
- **Deps**: T02
- **Why**: Plan Step 0.1 / AC-13 — preserve inputs as artifacts for post-refactor behavioral comparison
- **Files**: `docs/features/033-comprehensive-prompt-refactor/test-inputs/` (new directory)
- **Action**: Store all test inputs from T02 as reproducible artifacts. File naming convention:
  - `design-reviewer-input.md` — the 200-word design document
  - `secretary-routing-prompts.md` — 5 prompts numbered 1-5 with expected agent selections
  - `brainstorming-topic.md` — the rate limiting topic description
  - `ds-code-notebook-input.md` — the notebook description with anti-patterns
  - `ds-analysis-input.md` — the analysis description with statistical pitfalls
- **Done**: `test-inputs/` directory exists with 5 files matching the naming convention above. Each file is self-contained plain text that can be pasted directly into the pilot file invocation.
- [ ] Status

**Commit after T01-T03**: `iflow: capture baseline scores for 033 pilot files`

---

## Phase 1: Foundation (Reference File Updates)

### T04: Add cache-friendliness dimension to scoring-rubric.md [Group: C]
- **Deps**: none (parallel with T01-T03)
- **Why**: Plan Step 1.1 / SC-10, AC-1 — rubric must include cache-friendliness before SKILL.md can reference it
- **File**: `plugins/iflow/skills/promptimize/references/scoring-rubric.md`
- **Action**: Add `Cache-friendliness` as 10th row to Behavioral Anchors table with anchors: Pass (3) = all static before dynamic, Partial (2) = 1-2 static blocks after dynamic, Fail (1) = freely interleaved. Add to Component Type Applicability table (evaluated for all types).
- **Done**: File has 10 rows in anchors table. `cache_friendliness` appears. Applicability row exists.
- [ ] Status

### T05: Add 3 sections to prompt-guidelines.md [Group: C]
- **Deps**: none
- **Why**: Plan Step 1.2 / SC-7, AC-2 — guidelines must document Anthropic best practices before content sweep
- **File**: `plugins/iflow/skills/promptimize/references/prompt-guidelines.md`
- **Action**: Add after "Plugin-Specific Patterns": (1) Tool Use Prompting with Anthropic citation, (2) System vs Human Turn Placement with Claude 4.x citation, (3) Negative Framing Guidance with Claude 4.x citation. Update `## Last Updated` date and Update Log.
- **Done**: 3 new sections exist with Anthropic citations.
- [ ] Status

### T06: Add promptimize gate and terminology convention to component-authoring.md [Group: C]
- **Deps**: none
- **Why**: Plan Step 1.3 / SC-4, AC-11 — authoring guide must define terminology convention before content sweep
- **File**: `docs/dev_guides/component-authoring.md`
- **Action**: Add `[ ] Run promptimize on new/modified component files` to Quality Standards / Validation Checklist. Add "Terminology Convention" section defining: Stage = top-level skill divisions, Step = command sections and skill sub-items, Phase = workflow-state phase names only.
- **Done**: Promptimize checklist item present. Terminology section with all 3 terms defined.
- [ ] Status

**Commit after T04-T06**: `iflow: update foundation reference files (rubric, guidelines, authoring)`

---

## Phase 2: Tooling (Promptimize Updates + Batch Script)

### T07: Update test-promptimize-content.sh — 9 to 10 dimensions (TDD Red) [Group: D]
- **Deps**: none (Red step — tests expected to fail)
- **Why**: Plan Step 2.1a / SC-10, AC-1 — TDD Red: tests must assert 10 dimensions before source changes
- **File**: `plugins/iflow/hooks/tests/test-promptimize-content.sh`
- **Action**: Rename and update 7 test functions by name (use function names as anchors, not line numbers):
  - `test_rubric_has_exactly_9_dimensions` → `test_rubric_has_exactly_10_dimensions` (add `|Cache` to grep pattern, assert 10)
  - `test_scoring_formula_max_denominator_is_27` → `test_scoring_formula_max_denominator_is_30` (add `|Cache`, assert 10, denominator 30)
  - `test_cmd_validates_exactly_9_dimensions_in_phase1` → `test_cmd_validates_exactly_10_dimensions_in_phase1`
  - `test_cmd_lists_all_9_canonical_dimension_names` → `test_cmd_lists_all_10_canonical_dimension_names` (add `cache_friendliness`)
  - `test_skill_lists_all_9_dimension_names` → `test_skill_lists_all_10_dimension_names` (add `cache_friendliness`)
  - `test_skill_canonical_name_mapping_table_has_9_entries` → `test_skill_canonical_name_mapping_table_has_10_entries` (add `cache_friendliness`)
  - `test_cmd_score_formula_contains_27_and_100` → `test_cmd_score_formula_contains_30_and_100` (grep `'30'` instead of `'27'`)
  - Update ALL runner invocations to new function names (grep for old names to find all references)
- **Done**: `bash plugins/iflow/hooks/tests/test-promptimize-content.sh` runs and tests FAIL (Red — source files still say 9).
- [ ] Status

### T08: Update promptimize SKILL.md — 10 dimensions (TDD Green) [Group: E]
- **Deps**: T04 (rubric), T07 (tests)
- **Why**: Plan Step 2.1b / SC-10, AC-1 — TDD Green: SKILL.md must reference 10 dimensions to pass Red tests
- **File**: `plugins/iflow/skills/promptimize/SKILL.md`
- **Action**: Add `cache_friendliness` as 10th dimension in Phase 1 evaluation list (after `context_engineering`). Add to canonical dimension name mapping table. Use text-match search for updates:
  - "Evaluate all 9 dimensions" → "Evaluate all 10 dimensions"
  - "exactly 9 entries" → "exactly 10 entries"
- **Done**: Grep for "all 10 dimensions" returns >=1 match. Grep for "exactly 10 entries" returns >=1 match. Grep for "cache_friendliness" returns >=2 matches (dimension list + mapping table).
- [ ] Status

### T09: Update promptimize.md command — denominator 30 (TDD Green) [Group: F]
- **Deps**: T08 (SKILL.md must reference 10 before command validates)
- **Why**: Plan Step 2.2 / SC-5, SC-10 — command formula must use denominator 30 for 10 dimensions, with trivial-math exception
- **File**: `plugins/iflow/commands/promptimize.md`
- **Action**:
  - Step 4c validation: "exactly 9" → "exactly 10", add `cache_friendliness` to canonical names
  - Step 5 preamble: "Sum all 9 dimension scores" → "Sum all 10 dimension scores" (~line 145)
  - Step 5 formula: `round((sum/27)*100)` → `round((sum/30)*100)`, update denominator 27→30
  - Add trivial-math exception comment: `<!-- Trivial-math exception: sum of 10 integers [1-3] + divide by 30 + round. Deterministic, no ambiguity. See SC-5 refinement. -->`
  - Update Step 5 example to show 10 scores: `[3, 2, 1, 3, 2, 3, 3, 3, 2, 2]` → sum = 24, score = 80
- **Done**: (1) `bash plugins/iflow/hooks/tests/test-promptimize-content.sh` — all dimension tests PASS (Green). (2) Grep confirms "30" in formula, "exactly 10". (3) Grep for "Trivial-math exception" in promptimize.md returns 1 match.
- [ ] Status

### T10: Create batch-promptimize.sh script [Group: E]
- **Deps**: T04 (rubric must have 10 dimensions)
- **Why**: Plan Step 2.3 / SC-1, SC-5 — batch script needed for full-fleet scoring; must use bash arithmetic not LLM math
- **File**: `plugins/iflow/scripts/batch-promptimize.sh` (new)
- **Action**: Create shell script per design C2.3 and I-3:
  - Discovery: find all `SKILL.md`, `agents/*.md`, `commands/*.md` under `plugins/iflow/`
  - Execution: `claude -p` with inline scoring prompt
  - Score extraction: Python JSON parsing
  - Score computation: bash arithmetic `$(( (sum * 100 + 15) / 30 ))` — no LLM math
  - Concurrency: max 5 parallel processes, configurable via `--max-parallel`
  - Per-file timeout: 120s via `timeout 120 claude -p ...`
  - Working directory guard: verify `plugins/iflow/skills/promptimize/references/scoring-rubric.md` exists
  - CLI args: `--max-parallel N`, `--threshold N` (default 80), `--help`
  - `chmod +x` the script
- **Done**: (1) Script is executable. (2) `--help` runs without error. (3) Rubric guard fails gracefully outside project root. (4) Grep for `$(( ` returns >=1 match. (5) No `claude -p` call performs score computation.
- [ ] Status

### T11: Smoke test batch-promptimize.sh [Group: G]
- **Deps**: T10
- **Why**: Plan Step 2.3 / SC-1 — verify batch script produces parseable numeric output before full run
- **Action**: Run batch-promptimize.sh on 1-2 known files (one agent, one skill). Verify parseable scores are extracted.
- **Done**: At least 1 file produces a valid numeric score.
- [ ] Status

**Commit after T07-T11**: `iflow: update promptimize tooling to 10 dimensions + batch script`

---

## Phase 3: Structural Changes

### T12: Split review-ds-code.md — God Prompt 3-chain dispatch [Group: H]
- **Deps**: none (independent of Phase 1-2)
- **Why**: Plan Step 3.1 / SC-6, AC-7 — decompose 5-axis monolithic prompt into 3 chained dispatches with <=3 axes each
- **File**: `plugins/iflow/commands/review-ds-code.md`
- **Action**: Replace single `Task()` dispatch with 3-chain sequential dispatch:
  - Chain 1: [anti-patterns, pipeline quality, code standards]
  - Chain 2: [notebook quality, API correctness]
  - Chain 3: synthesis of Chain 1+2 outputs
  - Add SCOPE RESTRICTION instruction at TOP of Chains 1+2
  - Add typed JSON schemas to all 3 chains
  - Add chain error handling (Chain 1/2 failure halts; Chain 3 returns degraded)
  - Add scope leakage filtering between Chain 2 and Chain 3
  - Add output size warning (>5KB)
  - Add chain output handling: extract JSON from response, treat invalid JSON as chain failure
- **Done**: File has 3 separate `Task()` dispatch blocks. Grep for "SCOPE RESTRICTION" returns 2 matches. Typed schema blocks present. Chain error handling present.
- [ ] Status

**Commit after T12**: `iflow: split review-ds-code.md into 3-chain dispatch`

### T13: Split review-ds-analysis.md — God Prompt 3-chain dispatch [Group: H]
- **Deps**: none (parallel with T12)
- **Why**: Plan Step 3.2 / SC-6, AC-7 — same God Prompt decomposition for analysis review
- **File**: `plugins/iflow/commands/review-ds-analysis.md`
- **Action**: Same 3-chain pattern as T12:
  - Chain 1: [methodology, statistical validity, data quality]
  - Chain 2: [conclusion validity, reproducibility]
  - Chain 3: synthesis
  - Same scope override, JSON schemas, error handling, chain output handling patterns
- **Done**: Same verification as T12 adapted for analysis review axes.
- [ ] Status

**Commit after T13**: `iflow: split review-ds-analysis.md into 3-chain dispatch`

### T14: Add trivial-math exception comment to secretary.md [Group: I]
- **Deps**: T15 (secretary.md cache restructure must complete first — micro-dependency from plan Step 3.3)
- **Why**: Plan Step 3.3 / SC-5 — document the trivial-math exception for secretary complexity scoring
- **File**: `plugins/iflow/commands/secretary.md`
- **Action**: Add `<!-- Trivial-math exception: 5-signal additive integer counting (SC-5). Addition only, no division/rounding. -->` near complexity scoring section.
- **Done**: Grep for "Trivial-math exception" in secretary.md returns 1 match.
- [ ] Status

### T15: Restructure secretary.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static content must precede dynamic content for prompt caching
- **File**: `plugins/iflow/commands/secretary.md`
- **Action**: Extract static content (Specialist Fast-Path table, routing tables, rules, PROHIBITED section, YOLO overrides) into `## Static Reference Tables` section at top. Convert inline table references to named anchors. Move all dynamic content (`$ARGUMENTS`, feature context) to bottom. This is the TD-3 exception file — requires limited content rewriting beyond block movement.
- **Done**: All static tables precede all dynamic injection markers. Run 3 routing prompts (direct agent match, help subcommand, ambiguous request) to verify no silent breakage.
- [ ] Status

### T16: Restructure brainstorming/SKILL.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static-before-dynamic ordering for prompt caching
- **File**: `plugins/iflow/skills/brainstorming/SKILL.md`
- **Action**: Move static content (stage definitions, rules, PROHIBITED section, error handling, PRD output format) above dynamic content (ARGUMENTS, iteration state). Block-movement only per TD-3.
- **Done**: All static sections precede dynamic injection points.
- [ ] Status

### T17: Restructure specify.md and design.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static-before-dynamic for 2 command files
- **Files**: `plugins/iflow/commands/specify.md`, `plugins/iflow/commands/design.md`
- **Action**: For each file, move static content (reviewer templates, schemas, YOLO overrides, rules) above dynamic content (ARGUMENTS, feature_path, iteration state). Block-movement only.
- **Done**: For each file, run: `git diff HEAD -- {filepath}` — added line count equals removed line count (confirming move-only changes, no net content added/deleted). All dynamic markers (`ARGUMENTS`, `{feature_path}`) appear after all static sections.
- [ ] Status

### T18: Restructure create-plan.md and create-tasks.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static-before-dynamic for 2 command files
- **Files**: `plugins/iflow/commands/create-plan.md`, `plugins/iflow/commands/create-tasks.md`
- **Action**: Same block-movement pattern as T17.
- **Done**: Same git diff verification as T17 for both files.
- [ ] Status

### T19: Restructure implement.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static-before-dynamic for implement command
- **File**: `plugins/iflow/commands/implement.md`
- **Action**: Same block-movement pattern as T17.
- **Done**: Same git diff verification as T17.
- [ ] Status

### T20: Restructure implementing/SKILL.md and retrospecting/SKILL.md for prompt caching [Group: H]
- **Deps**: none
- **Why**: Plan Step 3.4 / SC-3, AC-3 — static-before-dynamic for 2 skill files
- **Files**: `plugins/iflow/skills/implementing/SKILL.md`, `plugins/iflow/skills/retrospecting/SKILL.md`
- **Action**: Same block-movement pattern as T16.
- **Done**: Same git diff verification as T17 for both files.
- [ ] Status

### T21: Verify non-pilot cache restructure with automated diff [Group: J]
- **Deps**: T17, T18, T19, T20
- **Why**: Plan Step 3.4 / SC-3 — verify all 7 non-pilot restructured files are content-preserving moves only
- **Action**: For the 7 non-pilot restructured files (specify.md, design.md, create-plan.md, create-tasks.md, implement.md, implementing/SKILL.md, retrospecting/SKILL.md), run automated diff check:
  - For each file: `git diff HEAD -- {filepath} | grep -c '^+'` and `git diff HEAD -- {filepath} | grep -c '^-'` — added count must equal removed count (move-only)
  - Verify all dynamic markers (`ARGUMENTS`, `{feature_path}`, `{iteration}`) appear after all static content (headers, tables, schemas, rules)
  - Verify each file has a named static section before the first dynamic marker
- **Done**: All 7 files pass: added lines == removed lines, dynamic markers after static content.
- [ ] Status

**Commit after T12-T21**: `iflow: restructure 9 files for prompt caching (static-first ordering)`

---

## Phase 4: Content Sweep

### T22: Run pre-sweep adjective audit [Group: K]
- **Deps**: T15-T20 (cache restructure must be done before content sweep)
- **Why**: Plan Step 4.0 / SC-2, AC-8 — definitive audit before adjective removal
- **Action**: Run `grep -rlEi '\bappropriate\b|\bsufficient\b|\brobust\b|\bthorough\b|\bproper\b|\badequate\b|\breasonable\b' plugins/iflow/{agents,skills,commands} --include='*.md' | grep -v '/references/'`. For each file, count raw matches and domain-specific compound matches. Store definitive file list in `docs/features/033-comprehensive-prompt-refactor/adjective-audit.md`.
- **Done**: `adjective-audit.md` exists with exact file list and per-file net match counts (raw minus compounds).
- [ ] Status

### T23: Remove subjective adjectives from agent files [Group: L]
- **Deps**: T22
- **Why**: Plan Step 4.1 / SC-2, AC-8 — replace adjectives with measurable criteria in agent files
- **Files**: Agent files identified in T22 audit (~12 files)
- **Action**: For each in-scope agent file match: replace adjective with measurable criterion (context-specific per design C4.1 examples). Verify replacements preserve static-first ordering (SC-10).
- **Done**: Run: `grep -rEi '\bappropriate\b|\bsufficient\b|\brobust\b|\bthorough\b|\bproper\b|\badequate\b|\breasonable\b' plugins/iflow/agents --include='*.md' | grep -vEi '(sufficient sample|appropriate (statistical|stat )?test|sufficient data|robust standard error)'` — output is empty.
- [ ] Status

### T24: Remove subjective adjectives from command files [Group: L]
- **Deps**: T22
- **Why**: Plan Step 4.1 / SC-2, AC-8 — replace adjectives in command files. Note: secretary.md adjective removal only in this task; passive voice (T27) and terminology (T28) are separate passes
- **Files**: Command files identified in T22 audit (~6 files)
- **Action**: For each in-scope command file match: replace adjective with measurable criterion (context-specific per design C4.1 examples).
- **Done**: Run: `grep -rEi '\bappropriate\b|\bsufficient\b|\brobust\b|\bthorough\b|\bproper\b|\badequate\b|\breasonable\b' plugins/iflow/commands --include='*.md' | grep -vEi '(sufficient sample|appropriate (statistical|stat )?test|sufficient data|robust standard error)'` — output is empty.
- [ ] Status

### T25: Remove subjective adjectives from skill files [Group: L]
- **Deps**: T22
- **Why**: Plan Step 4.1 / SC-2, AC-8 — replace adjectives in skill files
- **Files**: Skill files identified in T22 audit (~10 files)
- **Action**: For each in-scope skill file match: replace adjective with measurable criterion (context-specific per design C4.1 examples).
- **Done**: Run: `grep -rEi '\bappropriate\b|\bsufficient\b|\brobust\b|\bthorough\b|\bproper\b|\badequate\b|\breasonable\b' plugins/iflow/skills --include='*.md' | grep -v '/references/' | grep -vEi '(sufficient sample|appropriate (statistical|stat )?test|sufficient data|robust standard error)'` — output is empty.
- [ ] Status

### T26: Verify zero adjectives across all component files [Group: M]
- **Deps**: T23, T24, T25
- **Why**: Plan Step 4.1 / SC-2 — cross-file verification that adjective removal is complete
- **Action**: Run full adjective grep: `grep -rEi '\bappropriate\b|\bsufficient\b|\brobust\b|\bthorough\b|\bproper\b|\badequate\b|\breasonable\b' plugins/iflow/{agents,skills,commands} --include='*.md' | grep -v '/references/' | grep -vEi '(sufficient sample|appropriate (statistical|stat )?test|sufficient data|robust standard error)'`
- **Done**: Command returns empty output (SC-2 verified).
- [ ] Status

### T27: Fix passive voice instances [Group: M]
- **Deps**: T23, T24, T25 (adjective removal may touch same files; do adjectives first)
- **Why**: Plan Step 4.2 / SC-7 — convert passive constructions to imperative mood
- **Files**: Affected prompt files (~12 instances)
- **Action**: Review files for passive constructions. Convert each to imperative mood (e.g., "JSON should be returned" → "Return JSON", "is returned" → "Return", "are provided" → "Provide", "will be" → direct verb, "must be" → direct verb).
- **Done**: Run: `grep -rEin '\b(should be|is returned|are provided|will be validated|is expected to|are expected to)\b' plugins/iflow/{agents,skills,commands} --include='*.md' | grep -v '/references/'` — output is empty for all modified files.
- [ ] Status

### T28: Normalize Stage/Step/Phase terminology [Group: N]
- **Deps**: T26 (normalize after adjective removal to capture any terminology introduced by replacements)
- **Why**: Plan Step 4.3 / SC-4, AC-11 — enforce consistent terminology per component-authoring.md convention
- **Files**: All 85 prompt files + 3 READMEs
- **Action**: Run: `grep -rn '\bStage\b\|\bStep\b\|\bPhase\b' plugins/iflow/{agents,skills,commands} README.md README_FOR_DEV.md plugins/iflow/README.md --include='*.md' > /tmp/terminology-audit.txt`. For each match, verify conformance: Stage = top-level skill divisions only, Step = command sections and skill sub-items, Phase = workflow-state phase names only. Violations: "Step" used as top-level division in a skill, "Stage" used in a command, "Phase" used outside workflow-state context. Fix all violations.
- **Done**: Re-run grep, manually verify all instances conform to convention. Zero violations.
- [ ] Status

### T29: Verify hook scripts after terminology changes [Group: N]
- **Deps**: T28
- **Why**: Plan Step 4.3 / SC-4 — hooks that reference phase names by string must not break
- **Action**: Run `bash plugins/iflow/hooks/tests/test-hooks.sh` to verify hooks referencing phase names by string are unbroken.
- **Done**: Hook tests pass.
- [ ] Status

### T30: Re-verify secretary.md static-first ordering [Group: N]
- **Deps**: T14, T24, T27, T28 (all editing passes on secretary.md: cache restructure + math comment + adjectives + passive voice + terminology)
- **Why**: Plan Step 3.4 + 4.1 + 4.2 + 4.3 / SC-3 — confirm static-first ordering survived all editing passes
- **File**: `plugins/iflow/commands/secretary.md`
- **Action**: After all secretary.md edits complete, re-verify that static content still precedes dynamic content. Run 3 routing prompts to confirm functional equivalence: (1) "review auth for security issues" → expect iflow:security-reviewer, (2) "help" → expect help output, (3) "make the app better" → expect clarification question.
- **Done**: Static-first ordering confirmed. 3 routing prompts return expected results.
- [ ] Status

**Commit after T22-T30**: `iflow: complete content sweep — adjectives, passive voice, terminology`

---

## Phase 5: Enforcement + Verification

### T31: Extend validate.sh with subjective adjective check [Group: O]
- **Deps**: T26 (adjectives must be removed first)
- **Why**: Plan Step 5.1 / SC-2, AC-12 — prevent adjective regression via CI-level enforcement
- **File**: `validate.sh`
- **Action**: Add content-level check section. Grep for subjective adjective pattern with `\b` word boundaries. Skip `*/references/*`. Subtract domain-specific compound matches (hardcoded: "sufficient sample", "appropriate statistical test", "sufficient data", "robust standard error"). Fail with descriptive output if violations found.
- **Done**: (1) `./validate.sh` passes. (2) Temporarily add "appropriate tools" to a component file, run validate.sh, confirm it fails with descriptive output. Remove test string.
- [ ] Status

**Commit after T31**: `iflow: add subjective adjective content check to validate.sh`

### T32: Create hookify promptimize reminder rule [Group: O]
- **Deps**: none (independent)
- **Why**: Plan Step 5.2 / AC-12 — advisory reminder to run promptimize on modified components
- **File**: `.claude/hookify.promptimize-reminder.local.md` (new, local-only)
- **Action**: Create hookify rule targeting PostToolUse Write/Edit events on `plugins/iflow/{agents,skills,commands}/**/*.md`. Advisory: "Component file modified. Consider running /iflow:promptimize to verify prompt quality."
- **Done**: (1) In a Claude Code session, use Write tool to add a space to end of line 1 in `plugins/iflow/agents/code-quality-reviewer.md`. (2) Confirm advisory message "Component file modified. Consider running /iflow:promptimize..." appears in tool response. (3) Revert the test change.
- **Note**: Not committed (`.local.md` is local-only, gitignored).
- [ ] Status

### T33: Run post-refactor promptimize on 5 pilot files [Group: P]
- **Deps**: All Phase 1-4 tasks (T04-T30)
- **Why**: Plan Step 5.3 / SC-1 — measure post-refactor quality improvement on pilot files
- **Files**: 5 pilot files
- **Action**: Run `/iflow:promptimize` on all 5 pilot files. Record post-refactor scores. Compare with pre-refactor scores from `baseline-scores.md`.
- **Done**: Post-refactor scores recorded. All 5 score >=80 (SC-1 for pilots).
- [ ] Status

### T34: Pilot behavioral verification — design-reviewer.md [Group: Q]
- **Deps**: T33, T03 (stored test inputs)
- **Why**: Plan Step 5.3 / AC-13 — verify refactored prompt produces equivalent behavioral output
- **File**: `plugins/iflow/agents/design-reviewer.md`
- **Action**: Run with 2-3 representative inputs from `test-inputs/design-reviewer-input.md` (complete design, missing interfaces, consistency issues). Compare pre/post: same JSON structure, same approval decision, issue count +/-1, no new categories, severity shift <=1 level.
- **Done**: Behavioral equivalence verified for design-reviewer.md.
- [ ] Status

### T35: Pilot behavioral verification — secretary.md [Group: Q]
- **Deps**: T33, T03
- **Why**: Plan Step 5.3 / AC-13 — verify secretary routing decisions unchanged
- **File**: `plugins/iflow/commands/secretary.md`
- **Action**: Run 5 routing prompts from `test-inputs/secretary-routing-prompts.md`. Compare pre/post: same agent selection for each prompt.
- **Done**: All 5 routing prompts return same agent selection.
- [ ] Status

### T36: Pilot behavioral verification — brainstorming/SKILL.md [Group: Q]
- **Deps**: T33, T03
- **Why**: Plan Step 5.3 / AC-13 — verify brainstorming stage progression unchanged
- **File**: `plugins/iflow/skills/brainstorming/SKILL.md`
- **Action**: Run with representative inputs from `test-inputs/brainstorming-topic.md`. Compare pre/post stage progression.
- **Done**: Behavioral equivalence verified.
- [ ] Status

### T37: Pilot behavioral verification — review-ds-code.md [Group: Q]
- **Deps**: T33, T03
- **Why**: Plan Step 5.3 / AC-13 — verify 3-chain dispatch produces equivalent output to original single dispatch
- **File**: `plugins/iflow/commands/review-ds-code.md`
- **Action**: Run with inputs from `test-inputs/ds-code-notebook-input.md`. Compare pre/post: same JSON structure (Chain 3 output), same approval decision, issue count +/-1, no new categories, severity shift <=1 level.
- **Done**: Behavioral equivalence verified via Chain 3 synthesis output.
- [ ] Status

### T38: Pilot behavioral verification — review-ds-analysis.md [Group: Q]
- **Deps**: T33, T03
- **Why**: Plan Step 5.3 / AC-13 — verify 3-chain dispatch produces equivalent output for analysis review
- **File**: `plugins/iflow/commands/review-ds-analysis.md`
- **Action**: Run with inputs from `test-inputs/ds-analysis-input.md`. Same comparison criteria as T37.
- **Done**: Behavioral equivalence verified.
- [ ] Status

### T39: Compile pilot gate report [Group: R]
- **Deps**: T34, T35, T36, T37, T38
- **Why**: Plan Step 5.3 / AC-13 — produce auditable gate artifact before proceeding to full batch
- **Action**: Create `docs/features/033-comprehensive-prompt-refactor/pilot-gate-report.md` listing:
  - Pass/fail status for each of the 5 pilots (T34-T38)
  - Pre/post promptimize score comparison (from T33)
  - Behavioral equivalence evidence summary (approval decision match, issue count delta, category preservation)
  - Gate decision: OPEN (all 5 pass) or BLOCKED (list failures with investigation notes)
- **Done**: `pilot-gate-report.md` exists with all 5 pilot entries. If all pass, report states "Gate: OPEN". If any fail, halt and investigate before proceeding to T40.
- [ ] Status

**Commit after T33-T39**: `iflow: verify pilot files pass behavioral equivalence for 033`

### T40: Full batch promptimize run — SC-1 verification [Group: S]
- **Deps**: T39 (pilot gate), T10 (batch script), T04 (rubric)
- **Why**: Plan Step 5.4 / SC-1 — final quality gate: all 85 files must score >=80
- **Action**: Run `batch-promptimize.sh` on all 85 files. For any file scoring <80: fix the identified dimension failures and re-score (max 2 fix-and-rescore iterations per file). If a file still scores <80 after 2 iterations, document it in `docs/features/033-comprehensive-prompt-refactor/below-threshold-files.md` with file path, current score, dimension failures, and deferral rationale.
- **Done**: Gate closure requires either: (a) `batch-promptimize.sh` exits code 0 with all files showing `[PASS]`, OR (b) all remaining below-threshold files documented in `below-threshold-files.md` with deferral rationale and the overall pass rate is >=95%.
- [ ] Status

**Commit after T40**: `iflow: all 85 files score >=80 on promptimize rubric`

---

## Dependency Summary

```
Phase 0 (sequential):
  T01 (baseline scores) ──→ T02 (baseline outputs) ──→ T03 (store inputs)

Phase 1 (parallel with Phase 0):
  T04 (rubric) ─┐
  T05 (guidelines) ─┤ Group C — all independent
  T06 (authoring) ──┘

Phase 2 (partially parallel):
  T07 (test Red) ─┐
  T04 ────────────┤──→ T08 (SKILL Green) ──→ T09 (cmd Green)
  T04 ────────────┴──→ T10 (batch script) ──→ T11 (smoke test)

Phase 3 (mostly parallel):
  T12 (ds-code split)     ─┐
  T13 (ds-analysis split)  ─┤
  T15 (secretary cache)    ─┤──→ T14 (secretary math comment)
  T16 (brainstorm cache)   ─┤
  T17 (specify+design cache)─┤──→ T21 (verify non-pilot)
  T18 (plan+tasks cache)   ─┤
  T19 (implement cache)    ─┤
  T20 (skills cache)       ─┘

Phase 4 (sequential within):
  T15-T20 ──→ T22 (audit) ──→ T23,T24,T25 (adjectives) ──→ T26 (verify)
                                                              ──→ T27 (passive) ──→ T28 (terminology) ──→ T29 (hooks), T30 (secretary verify)

Phase 5 (gated):
  T26 ──→ T31 (validate.sh)
  T32 (hookify) — independent
  All Phase 1-4 ──→ T33 (pilot scores) ──→ T34-T38 (pilot behavioral) ──→ T39 (gate report) ──→ T40 (full batch)
```

## Task Count Summary

| Phase | Tasks | Parallel Groups |
|-------|-------|-----------------|
| Phase 0 | T01-T03 (3) | A, B |
| Phase 1 | T04-T06 (3) | C |
| Phase 2 | T07-T11 (5) | D, E, F, G |
| Phase 3 | T12-T21 (10) | H, I, J |
| Phase 4 | T22-T30 (9) | K, L, M, N |
| Phase 5 | T31-T40 (10) | O, P, Q, R, S |
| **Total** | **40 tasks** | **16 parallel groups** |
