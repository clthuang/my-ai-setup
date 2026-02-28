# Design: Comprehensive Prompt Refactoring

## Prior Art Research

### Codebase Findings
- **Prompt caching structure**: Static/dynamic separation is implicit across files — no `cache_control` markers are used. Commands like `specify.md`, `design.md`, and `secretary.md` interleave static routing tables with dynamic feature context throughout
- **Reviewer dispatch pattern**: Consistent across 12+ command files — all use `Task()` with `subagent_type`, `model`, `description`, `prompt`. JSON return schemas vary: some specify typed fields, review-ds-code and review-ds-analysis use prose-only ("Return your findings as JSON with: approved, strengths, issues...")
- **Promptimize scoring**: Currently 9 dimensions, denominator 27, formula `round((sum/27)*100)`. Auto-pass rules differ by component type (commands get 4 auto-passes, agents get 1, skills get 0)
- **Terminology mixing**: Commands use "Step" consistently; skills mix "Stage" and "Step" (brainstorming uses both correctly per convention, but implementing uses "Step" for top-level divisions)
- **God Prompt candidates**: `review-ds-code.md` dispatches single agent covering 5 concern areas; `review-ds-analysis.md` dispatches single agent covering 4+ concern areas
- **validate.sh**: 14 structural checks (frontmatter, hooks schema, path portability, ERR traps, mkdir guards) — zero semantic/content-level checks
- **component-authoring.md**: Quality checklist exists but no mention of promptimize as a quality gate

### External Findings
- **Prompt caching**: Anthropic's caching requires 1024 token minimum for first cache breakpoint; static system prompt content must precede dynamic content; cache hits reduce cost ~90% on repeated prefixes
- **Best practices**: XML tags are primary structuring mechanism for Claude 4.x; long data at TOP of context; explicit output schema reduces format errors; positive framing preferred over negation
- **God Prompt decomposition**: ACL 2024 findings show chaining outperforms monolithic prompts; sub-prompts with focused scope produce higher-quality outputs
- **LLM-as-Judge**: Structured rubrics with objective criteria outperform open-ended quality assessment; Anthropic recommends explicit behavioral anchors per score level
- **Tool use prompting**: Anthropic docs recommend structured tool parameter descriptions, explicit sequencing instructions for multi-tool workflows
- **Negative framing**: Claude 4.x models respond better to "Do X" than "Don't do Y" for instruction compliance

---

## Architecture Overview

### Execution Order

The refactoring executes in 5 phases, ordered by dependency:

```
Phase 1: FOUNDATION (reference file updates)
    scoring-rubric.md (add cache-friendliness dimension)
    prompt-guidelines.md (fill 3 gaps)
    component-authoring.md (add promptimize gate + terminology convention)
    ↓
Phase 2: TOOLING (promptimize updates + batch script)
    promptimize SKILL.md (10 dimensions)
    promptimize.md command (denominator 30, validation for 10 dims)
    batch-promptimize.sh (new script, iterates 85 files)
    ↓
Phase 3: STRUCTURAL CHANGES (God Prompt splits + math fix + caching)
    review-ds-code.md (3-chain dispatch)
    review-ds-analysis.md (3-chain dispatch)
    promptimize SKILL.md (extract score computation to command)
    secretary.md (document trivial-math exception)
    9 files for cache restructure (6 commands + 3 skills)
    ↓
Phase 4: CONTENT SWEEP (adjective removal + terminology + passive voice)
    ~73 raw adjective instances across 38 files (per spec AC-8; exact in-scope count after domain-specific exclusion filtering TBD by batch audit in Phase 4 execution)
    ~12 passive voice instances
    Terminology normalization across 85+ files
    ↓
Phase 5: ENFORCEMENT + VERIFICATION
    validate.sh (add subjective adjective grep)
    hookify rule (.claude/hookify.promptimize-reminder.local.md)
    5-file pilot with behavioral equivalence verification
    Full batch-promptimize run for SC-1 verification
```

### Dependency Graph

```
AC-1 (scoring rubric) ──→ AC-3 (batch script) ──→ AC-13 (pilot verification)
AC-2 (guidelines)     ──→ AC-10 (passive voice via technique_currency)
                           AC-3 (batch script) ──→ SC-1 (all files ≥80)
AC-6 (math fix)       ──→ AC-13 (pilot: promptimize + secretary)
AC-7 (God splits)     ──→ AC-5 (JSON schemas) ──→ AC-13 (pilot: ds-code, ds-analysis)
AC-4 (cache restructure) ──→ AC-13 (pilot: brainstorming, secretary, design-reviewer)
AC-8 (adjectives)     ──→ SC-2 (zero adjectives)
AC-9 (terminology)    ──→ SC-3 (one convention)
AC-11 (enforcement)   ─── independent
AC-12 (validate.sh)   ─── independent (but verifies AC-8 output)
```

### Phase 1: Foundation — Components

#### C1.1: scoring-rubric.md Update
- **File**: `plugins/iflow/skills/promptimize/references/scoring-rubric.md`
- **Change**: Add 10th row to Behavioral Anchors table:
  - Dimension: `Cache-friendliness`
  - Pass (3): All static content precedes all dynamic content with zero interleaving
  - Partial (2): Mostly separated but 1-2 static blocks appear after dynamic injection points
  - Fail (1): Static and dynamic content freely interleaved or no clear separation
- **Change**: Add 10th row to Component Type Applicability table:
  - Cache-friendliness: Evaluated for skills, Evaluated for agents, Evaluated for commands
- **Risk**: None — additive change to reference file

#### C1.2: prompt-guidelines.md Update
- **File**: `plugins/iflow/skills/promptimize/references/prompt-guidelines.md`
- **Change**: Add 3 new sections after the existing "Plugin-Specific Patterns" section:
  1. **Tool Use Prompting** — structured tool parameter descriptions, sequencing instructions for multi-tool workflows [Anthropic docs]
  2. **System vs Human Turn Placement** — static instructions in system turn, dynamic context in human turn; agentic reminders at bottom [Anthropic Claude 4.x]
  3. **Negative Framing Guidance** — prefer "Do X" over "Don't do Y"; exceptions for hard safety constraints in PROHIBITED sections [Anthropic Claude 4.x]
- **Change**: Update `## Last Updated` date to current date
- **Change**: Add entries to Update Log table

#### C1.3: component-authoring.md Update
- **File**: `docs/dev_guides/component-authoring.md`
- **Change**: Add to Quality Standards / Validation Checklist:
  - `[ ] Run promptimize on new/modified component files`
- **Change**: Add new section "Terminology Convention":
  - "Stage" for top-level divisions in skills
  - "Step" for sequential sections in commands and sub-items within stages
  - "Phase" exclusively for workflow-state phase names (brainstorm, specify, design, plan, tasks, implement, finish)

### Phase 2: Tooling — Components

#### C2.1: promptimize SKILL.md Update
- **File**: `plugins/iflow/skills/promptimize/SKILL.md`
- **Changes**:
  - Add `cache_friendliness` as 10th dimension in Phase 1 evaluation list (after context_engineering)
  - Add to canonical dimension name mapping table: `Cache-friendliness` → `cache_friendliness`
  - Update "exactly 9 entries" constraint to "exactly 10 entries"
  - Phase 1 output JSON: no structural change (dimensions array simply has 10 items now)

#### C2.2: promptimize.md Command Update
- **File**: `plugins/iflow/commands/promptimize.md`
- **Changes**:
  - Step 4c validation: change "exactly 9 entries" to "exactly 10 entries"
  - Step 4c canonical names list: add `cache_friendliness`
  - Step 5: replace the LLM-computed formula `round((sum / 27) * 100)` with an instruction for the LLM to output raw scores only as JSON `{"scores": [3, 2, 3, ...]}`. The final percentage computation moves to the calling context (batch-promptimize.sh computes in bash; interactive use computes via the command's post-processing logic). This satisfies AC-6: sum/divide/round operations execute in orchestrating code, not LLM generation.
  - Step 5 example: update to show 10 raw scores with explicit note that percentage is computed externally

#### C2.3: batch-promptimize.sh Script (New File)
- **File**: `plugins/iflow/scripts/batch-promptimize.sh`
- **Purpose**: Iterate all 85 component files with aggregate reporting
- **Design**:
  - Discovery: find all `SKILL.md`, `agents/*.md`, `commands/*.md` under `plugins/iflow/`
  - Execution mechanism: invoke Claude CLI per file using `claude -p "Run /iflow:promptimize on {filepath}. Return ONLY the final score line in format: SCORE:{N}" --allowedTools 'Read,Grep,Glob' --model sonnet`. The `-p` flag (print mode) sends a single prompt and returns output to stdout without interactive session. Plugin slash commands are available because `claude -p` loads the plugin context from `.claude/plugins.json`. Each invocation runs in the project root so plugin resolution works normally.
  - Score extraction: parse stdout for line matching regex `SCORE:(\d+)`. If no match found, mark file as `[ERROR]` with score -1 and continue. The `SCORE:{N}` return format is a deterministic single-line output that avoids parsing complex markdown.
  - Concurrency: max 5 parallel background processes (`&` + `wait`); configurable via `--max-parallel`
  - Output: per-file score line, aggregate summary (count, mean, min, files below 80)
  - Exit code: 0 if all files ≥80, 1 if any file <80
  - Timeout: 120 seconds per file invocation (via `timeout 120 claude -p ...`); files exceeding timeout marked as `[TIMEOUT]`

### Phase 3: Structural Changes — Components

#### C3.1: review-ds-code.md God Prompt Split
- **File**: `plugins/iflow/commands/review-ds-code.md`
- **Current**: Single `Task()` dispatch to `iflow:ds-code-reviewer` covering 5 concern areas
- **New Structure**:
  ```
  Chain 1: Task(ds-code-reviewer) — axes: [anti-patterns, pipeline quality, code standards]
           Scope override: "Evaluate ONLY the following axes. Ignore all other review sections."
           Return: JSON {axis_results: [{axis, approved, issues}]}

  Chain 2: Task(ds-code-reviewer) — axes: [notebook quality, API correctness]
           Scope override: same instruction
           Return: JSON {axis_results: [{axis, approved, issues}]}

  Chain 3: Task(ds-code-reviewer) — synthesis
           Data flow: Chain 3's dispatch prompt includes the JSON outputs from Chains 1+2
             inline in its prompt text (not via separate tool calls or files). The command
             file orchestrates this: after Chain 1 Task() returns, capture its JSON text;
             after Chain 2 Task() returns, capture its JSON text; then construct Chain 3's
             prompt with both JSON blocks embedded in a `## Prior Chain Results` section.
           Instruction: "Synthesize into single consolidated review. Do not re-read original files."
           Return: JSON {approved, strengths, issues, verification, summary}
  ```
- **Agent file**: `agents/ds-code-reviewer.md` — unchanged. Each chain invokes same agent with narrower scope
- **JSON schema**: Add typed schema block to each chain's dispatch prompt (see Interface Design)
- **Chain error handling**: If Chain 1 or Chain 2 fails (Task() returns error or invalid JSON), do NOT proceed to Chain 3. Instead, return an error response: `{approved: false, issues: [{severity: "blocker", description: "Chain {N} failed: {error}"}], summary: "Review incomplete due to chain failure"}`. If Chain 3 fails, return the raw Chain 1+2 results concatenated as a degraded response with a warning header.

#### C3.2: review-ds-analysis.md God Prompt Split
- **File**: `plugins/iflow/commands/review-ds-analysis.md`
- **Current**: Single `Task()` dispatch to `iflow:ds-analysis-reviewer` covering 4+ concern areas
- **New Structure**:
  ```
  Chain 1: Task(ds-analysis-reviewer) — axes: [methodology, statistical validity, data quality]
           Scope override: "Evaluate ONLY the following axes. Ignore all other review sections."
           Return: JSON {axis_results: [{axis, approved, issues}]}

  Chain 2: Task(ds-analysis-reviewer) — axes: [conclusion validity, reproducibility]
           Scope override: same instruction
           Return: JSON {axis_results: [{axis, approved, issues}]}

  Chain 3: Task(ds-analysis-reviewer) — synthesis
           Data flow: Same mechanism as C3.1 — Chain 3's dispatch prompt includes Chain 1+2
             JSON outputs inline in a `## Prior Chain Results` section. The command file
             orchestrates sequential Task() calls, capturing each return value as text.
           Instruction: "Synthesize into single consolidated review. Do not re-read original files."
           Return: JSON {approved, pitfalls_detected, code_issues, methodology_concerns,
                         verification, recommendations, summary}
  ```
- **Agent file**: `agents/ds-analysis-reviewer.md` — unchanged
- **Chain error handling**: Same policy as C3.1 — Chain 1/2 failure halts before Chain 3; Chain 3 failure returns degraded Chain 1+2 results

#### C3.3: Math-in-LLM Fixes
- **promptimize.md command**: Step 5 currently contains the formula `round((sum/27)*100)` as markdown text that the LLM interprets during command execution. This IS LLM-performed math (division + rounding), violating AC-6. The fix: rewrite Step 5 to instruct the LLM to output raw dimension scores only (as a JSON array of 10 integers), then add a post-processing step where the command's orchestrating logic (the skill runner / command dispatcher) computes the final percentage. Implementation: the promptimize command's Step 5 becomes "Output the 10 raw scores as JSON: `{\"scores\": [3, 2, 3, ...]}`. The final percentage is computed by the calling script." The batch-promptimize.sh script and any direct command invocation will extract the scores array and compute `round((sum/30)*100)` in bash arithmetic (`$(( (sum * 100 + 15) / 30 ))` for rounding).
- **promptimize SKILL.md**: The skill's Phase 1 outputs raw dimension scores — no math here. No change needed.
- **secretary.md**: The complexity scoring (5-signal additive counting) remains inline as LLM computation. Add a code comment documenting the trivial-math exception: `<!-- Trivial-math exception: 5-signal additive integer counting (SC-5). Addition only, no division/rounding. -->`

#### C3.4: Prompt Caching Restructure (9 Files)
- **Principle**: Move all static content (reviewer templates, routing tables, schemas, rules, PROHIBITED sections) above all dynamic content (user input, feature context, iteration state, $ARGUMENTS handling)
- **Files and strategy**:

  | File | Static Content (move to top) | Dynamic Content (keep at bottom) |
  |------|------------------------------|----------------------------------|
  | `commands/specify.md` | Workflow rules, reviewer dispatch templates, YOLO overrides | Feature path, iteration context |
  | `commands/design.md` | 5-stage workflow definition, reviewer templates, YOLO overrides | Feature path, stage state |
  | `commands/create-plan.md` | Plan structure template, rules | Feature path, spec/design content |
  | `commands/create-tasks.md` | Task breakdown rules, format template | Feature path, plan content |
  | `commands/implement.md` | Implementation rules, reviewer dispatch, circuit breaker | Feature path, task list, iteration |
  | `commands/secretary.md` | Help text, mode logic, specialist fast-path tables, workflow pattern tables, confidence thresholds, error handling templates, rules section | User request, feature state, discovery results, triage output. Note: secretary.md has deep interleaving — routing tables reference dynamic discovery output mid-flow. Restructure approach: extract all static tables (fast-path, workflow patterns, maturity signals, complexity signals) into a dedicated `## Static Reference Tables` section at the top; convert inline table references to named anchors (e.g., "See Fast-Path Table above"); keep all step-by-step logic (which references both static and dynamic) in the procedural section below. This is a larger restructure than the other 8 files. |
  | `skills/brainstorming/SKILL.md` | 6-stage process definition, PRD template reference, YOLO overrides, PROHIBITED | User topic, research results, iteration |
  | `skills/implementing/SKILL.md` | Task dispatch pattern, review loop, TDD reference | Feature context, task list, progress |
  | `skills/retrospecting/SKILL.md` | AORTA framework, KB update rules, recovery logic | Feature context, retro data |

- **Verification**: Per AC-4, for 5 pilot files use full AC-13 behavioral equivalence; for remaining 4 files use automated diff check (no lines deleted/added, only moved; dynamic markers after all static content; named static sections before first dynamic marker)

### Phase 4: Content Sweep — Components

#### C4.1: Subjective Adjective Removal
- **Target pattern**: `appropriate|sufficient|robust|thorough|proper|adequate|reasonable`
- **Scope**: Instruction text in all 85 prompt files
- **Exclusions**: Reference files, domain-specific statistical terms (e.g., "sufficient sample size" in ds-analysis), description frontmatter trigger phrases, code examples
- **Method**:
  1. Grep all 85 files for the pattern
  2. Manual filter using AC-8 exclusion boundary (domain-specific terms in ds review checklists)
  3. For each match, replace adjective with measurable criterion
  4. Verify replacements in agent files preserve static-content-first ordering (SC-10)
- **Examples**:
  - "appropriate tools" → "tools listed in the frontmatter `tools:` field"
  - "sufficient detail" → "detail covering all acceptance criteria"
  - "robust error handling" → "error handling with try/catch at I/O boundaries"

#### C4.2: Passive Voice Fix
- **Target**: ~12 instances of passive voice constructions
- **Method**: After batch-promptimize grades all files, review `technique_currency` dimension findings for passive voice flags
- **Fix**: Convert to imperative mood ("Return JSON" not "JSON should be returned")

#### C4.3: Terminology Normalization
- **Convention**:
  - "Stage" → top-level divisions in skills (e.g., "Stage 1: CLARIFY")
  - "Step" → sequential sections in commands and sub-items within stages
  - "Phase" → exclusively for workflow-state phase names
- **Method**: Grep all 85 files + READMEs for misuses; fix each instance
- **Verification**: Post-fix grep confirms zero violations; hook scripts using phase name strings are verified unbroken

### Phase 5: Enforcement + Verification — Components

#### C5.1: validate.sh Extension
- **File**: `validate.sh`
- **Change**: Add content-level check section after existing structural checks:
  ```bash
  # Content-level checks
  echo "Checking Content Quality..."
  adjective_pattern='appropriate|sufficient|robust|thorough|proper|adequate|reasonable'
  adjective_violations=0
  while IFS= read -r md_file; do
      # Skip reference files (contain rubric examples and domain definitions)
      case "$md_file" in */references/*) continue ;; esac
      # Use grep -n to get line-level matches, then filter out known exclusion patterns:
      # - Lines inside code blocks (``` fenced blocks)
      # - Lines in YAML frontmatter (between --- markers)
      # - Known domain-specific compounds: "sufficient sample size", "appropriate statistical test",
      #   "appropriate test", "sufficient data", "robust standard error"
      # Implementation: pipe grep output through awk that tracks code-block state and
      # filters domain-specific compounds via negative lookahead-equivalent patterns
      matches=$(grep -cEi "$adjective_pattern" "$md_file" 2>/dev/null || true)
      # Subtract domain-specific matches
      domain_matches=$(grep -cEi '(sufficient sample|appropriate (statistical |stat )?test|sufficient data|robust standard error)' "$md_file" 2>/dev/null || true)
      net_matches=$((matches - domain_matches))
      if [ "$net_matches" -gt 0 ]; then
          log_error "$md_file: $net_matches subjective adjective instance(s) (after excluding $domain_matches domain-specific terms)"
          ((adjective_violations+=net_matches)) || true
      fi
  done < <(find ./plugins/iflow/agents ./plugins/iflow/skills ./plugins/iflow/commands -name "*.md" -type f 2>/dev/null)
  ```
- **Behavior**: Fails with descriptive output if violations found
- **False positive mitigation**: Domain-specific compound terms (statistical terminology used in ds-review checklists) are subtracted from raw match count per AC-8 exclusion boundary

#### C5.2: Hookify Rule
- **File**: `.claude/hookify.promptimize-reminder.local.md`
- **Purpose**: Advisory reminder when component files are edited
- **Method**: Create via `/iflow:hookify` command targeting PostToolUse Write/Edit events on `plugins/iflow/{agents,skills,commands}/**/*.md`
- **Note**: `.local.md` naming = local-only, not committed to version control

#### C5.3: Pilot Verification (AC-13)
- **5 pilot files**: `design-reviewer.md`, `secretary.md`, `brainstorming/SKILL.md`, `review-ds-code.md`, `review-ds-analysis.md`
- **Process**:
  1. Record pre-refactor promptimize scores for all 5 files
  2. Apply all Phase 1-4 changes to pilot files first
  3. Record post-refactor promptimize scores
  4. For each pilot file, identify 2-3 representative inputs
  5. Run pre and post versions, compare: same approval decision, issue count within +/-1, no new issue categories, severity distribution shift ≤1 level
  6. **JSON structure comparison note**: For `review-ds-code.md` and `review-ds-analysis.md`, the God Prompt split (C3.1/C3.2) changes the intermediate chain schemas but Chain 3's synthesis output preserves the same top-level schema as the pre-split single dispatch (same field names, same types). The AC-13 "same JSON structure" check applies to the Chain 3 synthesis output, not the intermediate chain outputs.
  7. If any pilot fails → halt and investigate before proceeding to remaining files
- **Secretary routing verification**: 5+ representative prompts confirming same agent selection
- **Pilot sequencing**: Pilot files are verified AFTER all Phase 1-4 changes are applied to them (not incrementally per phase). This ensures the behavioral equivalence check captures the combined effect of all changes.

---

## Technical Decisions

| # | Decision | Rationale | Alternative Considered |
|---|----------|-----------|----------------------|
| TD-1 | Same agent files called multiple times with narrower scope (no new agent files) | Avoids agent duplication; the existing agent system prompts define the review knowledge, and each chain only needs a scope subset | Creating separate focused agents per chain — rejected because it duplicates review criteria across files |
| TD-2 | Batch-promptimize as shell script with `claude -p` (print mode) | Native parallelism via `&` + `wait`; `-p` flag sends single prompt to stdout with plugin context loaded; avoids recursive command-scoring-command issue; score extracted via deterministic `SCORE:{N}` line format | Python script — rejected because shell is simpler and matches existing validate.sh pattern |
| TD-3 | Cache restructure uses block movement, not content rewriting | Minimizes risk of behavioral changes; only repositioning existing text blocks | Rewriting files from scratch — rejected because behavioral equivalence verification would be impractical |
| TD-4 | Secretary trivial-math stays inline with documented exception | 5-signal additive counting is deterministic for LLMs; extracting to code adds complexity without reliability gain | Moving to code — rejected per SC-5 trivial-math exception |
| TD-5 | Adjective removal uses grep + manual filter, not automated rewrite | Each adjective needs a context-specific measurable replacement; automated rewrite cannot determine the right criterion | Full automated replacement — rejected because replacements require semantic understanding of context |
| TD-6 | Chain 3 (synthesis) does not re-read original files | Chains 1+2 already extracted all findings; re-reading would waste tokens and risk inconsistency | Having Chain 3 re-read for validation — rejected to avoid token waste and redundant work |

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R-1 | God Prompt split changes dispatch contract, breaking agent expectations | Medium | High | AC-7 subset scope override instruction prevents agent from evaluating out-of-scope axes; AC-13 pilot verification catches behavioral differences |
| R-2 | Secretary routing silently breaks from description text changes during adjective removal | Medium | High | AC-13 pilot includes secretary with 5+ routing prompts; changes to description frontmatter are excluded from AC-8 scope |
| R-3 | Cache restructure introduces subtle behavioral changes from content reordering | Low | High | AC-4 automated diff verification (no lines deleted/added, only moved); AC-13 pilot for 5 high-risk files |
| R-4 | batch-promptimize.sh timeout from API latency on 85 files | Medium | Low | Non-functional target (not acceptance-gating); max 5 concurrent processes; timeout handling per invocation |
| R-5 | Adjective domain-specific exclusion boundary is ambiguous | Low | Medium | AC-8 defines explicit boundary: statistical terminology in ds review checklists where adjective describes a domain concept, not a vague instruction |
| R-6 | Terminology normalization breaks hook scripts that match phase name strings | Low | High | AC-9 requires verification that hook scripts are unbroken; only "Phase" naming for workflow states, which is already the convention in hooks |
| R-7 | God Prompt chain scope override ignored by LLM — agent evaluates all axes despite restriction | Medium | Medium | Two-layer mitigation: (1) scope instruction at top of prompt for maximum attention, (2) deterministic code-level stripping of out-of-scope axis_results entries before passing to Chain 3 (see I-7) |
| R-8 | Chain 1 or Chain 2 failure leaves review incomplete | Low | High | Error handling in C3.1/C3.2: chain failure halts before synthesis; returns structured error response; no silent partial reviews |

---

## Interface Design

### I-1: Chain Dispatch JSON Schema (review-ds-code)

Each chain's dispatch prompt includes this typed schema block:

**Chain 1 & 2 Return Schema:**
```json
{
  "axis_results": [
    {
      "axis": "string — name of the review axis evaluated",
      "approved": "boolean — true if no blockers found for this axis",
      "issues": [
        {
          "severity": "string — one of: blocker, warning, suggestion",
          "description": "string — what the issue is",
          "location": "string — file:line or section reference",
          "suggestion": "string — how to fix it"
        }
      ]
    }
  ]
}
```

**Chain 3 (Synthesis) Return Schema:**
```json
{
  "approved": "boolean — true if no blockers across all axes",
  "strengths": [
    "string — positive observation"
  ],
  "issues": [
    {
      "severity": "string — one of: blocker, warning, suggestion",
      "axis": "string — which review axis flagged this",
      "description": "string — what the issue is",
      "location": "string — file:line or section reference",
      "suggestion": "string — how to fix it"
    }
  ],
  "verification": {
    "api_checked": "boolean — whether at least 1 API usage was verified",
    "api_details": "string — what was checked and result"
  },
  "summary": "string — 2-3 sentence overall assessment"
}
```

### I-2: Chain Dispatch JSON Schema (review-ds-analysis)

**Chain 1 & 2 Return Schema:** Same as I-1 Chain 1 & 2.

**Chain 3 (Synthesis) Return Schema:**
```json
{
  "approved": "boolean — true if no blockers across all axes",
  "pitfalls_detected": [
    {
      "name": "string — pitfall category name",
      "severity": "string — one of: blocker, warning, suggestion",
      "description": "string — what the pitfall is",
      "evidence": "string — how it was detected"
    }
  ],
  "code_issues": [
    {
      "severity": "string — one of: blocker, warning, suggestion",
      "description": "string — code-level issue",
      "location": "string — file:line reference"
    }
  ],
  "methodology_concerns": [
    "string — methodology observation"
  ],
  "verification": {
    "claim_checked": "boolean — whether at least 1 statistical claim was verified",
    "claim_details": "string — what was checked and result"
  },
  "recommendations": [
    "string — actionable recommendation"
  ],
  "summary": "string — 2-3 sentence overall assessment"
}
```

### I-3: batch-promptimize.sh Interface

**Input:**
```bash
./plugins/iflow/scripts/batch-promptimize.sh [--max-parallel N] [--threshold N]
```
- `--max-parallel`: Max concurrent processes (default: 5)
- `--threshold`: Minimum passing score (default: 80)

**Invocation per file:**
```bash
timeout 120 claude -p "Run /iflow:promptimize on {filepath}. Return ONLY the final score line in format: SCORE:{N}" \
  --allowedTools 'Read,Grep,Glob' --model sonnet 2>/dev/null
```

**Score extraction:** Parse stdout for regex `SCORE:([0-9]+)`. If no match: mark `[ERROR]`. If timeout: mark `[TIMEOUT]`.

**Score computation:** The promptimize command outputs raw dimension scores. The batch script extracts these and computes `$(( (sum * 100 + 15) / 30 ))` (integer rounding of `sum/30*100`) in bash arithmetic — no LLM math.

**Output Format:**
```
[PASS] plugins/iflow/agents/code-reviewer.md: 89/100
[FAIL] plugins/iflow/commands/secretary.md: 72/100
[ERROR] plugins/iflow/agents/broken.md: parse error
[TIMEOUT] plugins/iflow/skills/slow/SKILL.md: exceeded 120s
...
============================================
Batch Promptimize Summary
============================================
Total files: 85
Passed (≥80): 78
Failed (<80): 5
Errors: 1
Timeouts: 1
Mean score: 84 (excludes errors/timeouts)
Min score: 62
============================================
```

**Exit Code:** 0 if all files pass threshold, 1 if any fail/error/timeout.

### I-4: Scoring Rubric Extension

The `cache_friendliness` dimension is added as the 10th dimension. The canonical JSON name mapping:

| Rubric Name | JSON `name` Value |
|---|---|
| Cache-friendliness | `cache_friendliness` |

Component Type Applicability: Evaluated for all types (skill, agent, command).

### I-5: validate.sh Content Check Interface

The new content-level check section:
- **Input**: Scans `plugins/iflow/{agents,skills,commands}/**/*.md`
- **Exclusions**: `*/references/*` directories
- **Pattern**: Case-insensitive grep for `appropriate|sufficient|robust|thorough|proper|adequate|reasonable`
- **Output**: Per-file error with count; contributes to global `ERRORS` counter
- **Behavior**: Fails the validation script if any matches found (same as existing structural checks)

### I-6: Hookify Rule Specification

**File**: `.claude/hookify.promptimize-reminder.local.md`
**Event**: PostToolUse (Write or Edit)
**Matcher**: File path contains any of: `plugins/iflow/agents/`, `plugins/iflow/skills/`, `plugins/iflow/commands/` AND file extension is `.md`. The hookify rule uses the hookify plugin's standard matcher syntax (substring match on file path), not shell brace expansion. Three separate path patterns are specified, one per component directory.
**Action**: Advisory message: "Component file modified. Consider running /iflow:promptimize to verify prompt quality."
**Blocking**: No — advisory only

### I-7: Subset Scope Override Instruction

Standard instruction prepended to each chain dispatch (except synthesis chain):

```
SCOPE RESTRICTION: Evaluate ONLY the following axes: [{comma-separated axis names}].
Ignore all other review sections in your system prompt.
Do not evaluate, comment on, or report findings for axes outside this list.
Your response JSON must contain axis_results entries ONLY for the listed axes.
Any axis_results entry for an unlisted axis will be discarded by the caller.
```

**Scope leakage mitigation**: LLMs may not reliably ignore system prompt sections. Two safeguards:
1. The scope override instruction is placed at the TOP of the dispatch prompt (highest attention position), not buried mid-prompt
2. The command file's post-processing validates Chain 1+2 JSON responses: if `axis_results` contains entries for axes not in the chain's assigned list, those entries are stripped before passing to Chain 3. This is a deterministic code-level check, not LLM-dependent.

### I-8: Terminology Convention Contract

The convention documented in component-authoring.md and enforced via AC-9:

| Term | Usage | Examples |
|------|-------|---------|
| Stage | Top-level divisions in skills | Stage 1: CLARIFY, Stage 2: RESEARCH |
| Step | Sequential sections in commands; sub-items within skill stages | Step 1: Check arguments, Step 2a: Load file |
| Phase | Exclusively for workflow-state phase names | brainstorm, specify, design, plan, tasks, implement, finish |

Verification: `grep -rn 'Stage\|Step\|Phase' plugins/iflow/ | wc -l` with per-file review against convention.
