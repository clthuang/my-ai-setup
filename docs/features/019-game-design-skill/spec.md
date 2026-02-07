# Specification: Game Design Domain Skill for Brainstorming

## Overview

Add a game-design domain skill (thin orchestrator + 7 reference files) that enriches brainstorm PRDs with game design frameworks, engagement analysis, aesthetic direction, and feasibility guardrails. The brainstorming skill gains Steps 9-10 for domain selection/loading. The brainstorm-reviewer gains domain-aware review criteria via inline dispatch context.

## Components

### C1: New Skill — `game-design`

**Location:** `plugins/iflow-dev/skills/game-design/`

**Structure:**
```
game-design/
├── SKILL.md                              # Thin orchestrator (<120 lines)
└── references/
    ├── design-frameworks.md              # MDA, core loops, Bartle's, progression, genre mappings
    ├── engagement-retention.md           # Hook models, progression mechanics, retention frameworks
    ├── aesthetic-direction.md            # Art styles, audio design, game feel/juice, mood mappings
    ├── monetization-models.md            # F2P, premium, hybrid — advisory guardrails only
    ├── market-analysis.md               # Competitor frameworks, market sizing approach
    ├── tech-evaluation-criteria.md       # Evaluation dimensions for engines/platforms (NOT static lists)
    └── review-criteria.md               # Domain-specific checks for brainstorm-reviewer
```

**SKILL.md responsibilities:**
1. Accept game concept context from brainstorming Stage 1 (problem statement, target user, constraints)
2. Read reference files — all files are optional with graceful degradation:
   - If a reference file is missing: warn "Reference {filename} not found, skipping" and continue
   - If ALL reference files are missing: warn "No reference files found, skipping domain enrichment" and STOP
   - Produce partial Game Design Analysis from whatever files are available
3. Apply frameworks from loaded references to the game concept, producing 4 PRD subsections
4. Output `## Game Design Analysis` section with exact structure:
   ```markdown
   ## Game Design Analysis

   ### Game Design Overview
   - **Core Loop:** {describe the core gameplay loop using 3-layer model from design-frameworks.md}
   - **MDA Analysis:** Mechanics: {list} → Dynamics: {emergent behaviors} → Aesthetics: {player experiences}
   - **Player Types:** {primary Bartle type targeted} — {rationale}
   - **Genre-Mechanic Fit:** {genre} typically uses {mechanics} — concept aligns/diverges because {reason}

   ### Engagement & Retention
   - **Hook Model:** Trigger: {what} → Action: {what} → Reward: {what} → Investment: {what}
   - **Progression:** {vertical/horizontal/nested} — {specific mechanics}
   - **Social Features:** {applicable social hooks or "single-player focus"}
   - **Retention Strategy:** {D1/D7/D30 approach}

   ### Aesthetic Direction
   - **Art Style:** {chosen style from taxonomy} — {rationale tied to genre/audience}
   - **Audio Design:** {soundtrack approach, SFX style, ambient design}
   - **Game Feel/Juice:** {key juice elements: screen shake, particles, animation easing, etc.}
   - **Mood:** {emotional tone} — {how visual/audio reinforce it}

   ### Feasibility & Viability
   - **Monetization Options:** {2-3 models from monetization-models.md with risk flags}
   - **Market Context:** {competitor landscape, market sizing from market-analysis.md}
   - **Platform Considerations:** {evaluation dimensions from tech-evaluation-criteria.md — actual engine/platform data comes from Stage 2 research}
   ```
5. Output domain review criteria as markdown list for brainstorming to forward to Stage 6 dispatch:
   ```
   Domain Review Criteria:
   - Core loop defined?
   - Monetization risks stated?
   - Aesthetic direction articulated?
   - Engagement hooks identified?
   ```

**Does NOT:**
- Prescribe engines, platforms, or tech stacks (evaluation criteria only — live research fills in specifics)
- Prescribe monetization strategy (advisory guardrails only)
- Produce art assets or music (articulates direction, not production)
- Solution technical architecture (feasibility sanity check only)

### C2: Modified Skill — `brainstorming`

**Location:** `plugins/iflow-dev/skills/brainstorming/SKILL.md`

Three distinct modification points:

#### C2.1: Stage 1 CLARIFY — Steps 9-10

After existing Steps 6-8 (problem type classification, framework loading, store problem type), add:

**Step 9: Domain Selection**
- Present domain options via AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Does this problem have a specialized domain?",
      "header": "Domain",
      "options": [
        {"label": "Game Design", "description": "Load game design frameworks for PRD enrichment"},
        {"label": "None", "description": "No domain enrichment — standard brainstorm"}
      ],
      "multiSelect": false
    }]
  ```
- (Future domains can be added as additional options, up to AskUserQuestion's 4-option limit)

**Step 10: Domain Loading**
- If user selected "Game Design":
  - Derive sibling skill path: replace `skills/brainstorming` in Base directory with `skills/game-design`
  - Read `{derived path}/SKILL.md` via Read tool
  - If file not found: warn "Game design skill not found, proceeding without domain enrichment" → skip to Stage 2
  - Follow game-design SKILL.md instructions to read references and produce sections
  - Write `## Game Design Analysis` section to PRD (between Structured Analysis and Review History)
  - Store domain review criteria (markdown list from SKILL.md output) for Stage 6 dispatch
  - Store `domain: game-design` in brainstorming context for Stage 2 and Stage 6
- If user selected "None": skip Step 10 body entirely, proceed to Stage 2

**Loop-back behavior:** If `## Game Design Analysis` already exists in the PRD (from a previous Stage 7 → Stage 1 loop), delete it entirely before re-running Steps 9-10. Do NOT duplicate.

#### C2.2: Stage 2 RESEARCH — Domain-Aware Query Enhancement

When `domain` is set to `game-design` and tech-evaluation-criteria.md was loaded in Step 10:

- The internet-researcher dispatch prompt gains additional context:
  ```
  Additional game-design research context:
  - Research current game engines/platforms suitable for this concept
  - Evaluate against these dimensions: {dimensions from tech-evaluation-criteria.md}
  - Include current market data for the game's genre/platform
  ```
- Internet-researcher results are written to `Research Summary > Internet Research` as normal
- Game-design skill's `Feasibility & Viability` subsection references these Stage 2 findings

When domain is "None" or absent: Stage 2 dispatch is unchanged (backward compatible).

#### C2.3: Stage 6 READINESS CHECK — Domain Context in Dispatch

When domain context was stored in Step 10, add to the `## Context` section of the brainstorm-reviewer dispatch prompt:

```
## Context
Problem Type: {type from Step 8, or "none" if skipped/absent}
Domain: game-design
Domain Review Criteria:
- Core loop defined?
- Monetization risks stated?
- Aesthetic direction articulated?
- Engagement hooks identified?
```

When domain is "None" or absent, the Domain and Domain Review Criteria lines are omitted entirely. The dispatch looks identical to the pre-modification version:

```
## Context
Problem Type: {type from Step 8, or "none" if skipped/absent}
```

#### C2.4: PRD Output Format — Game Design Analysis Section

Add `## Game Design Analysis` section template (conditional — only when domain is active). Placed between Structured Analysis and Review History:

```markdown
## Game Design Analysis
*(Only included when game-design domain is active)*

### Game Design Overview
{MDA analysis, core loop description, genre-mechanic mapping, Bartle's player type targeting}

### Engagement & Retention
{Hook model application, progression mechanics, social features, retention strategy}

### Aesthetic Direction
{Art style choice with rationale, audio design direction, game feel/juice elements, mood-to-genre alignment}

### Feasibility & Viability
{Monetization model options with risk flags, market reality check, platform considerations from Stage 2 research}
```

When domain is "None": this section is not present in the PRD at all.

### C3: Modified Agent — `brainstorm-reviewer`

**Location:** `plugins/iflow-dev/agents/brainstorm-reviewer.md`

**Current state:** 5 universal criteria + 5-type criteria table. Parses `Problem Type:` from `## Context` section.

**New behavior:**

In addition to existing Problem Type parsing, the reviewer also parses:
- `Domain: {name}` from `## Context` section
- `Domain Review Criteria:` block with bulleted criteria items

**When domain criteria are present:**
- For each criterion in `Domain Review Criteria:` list, check PRD content for the corresponding analysis:
  - "Core loop defined?" → check `### Game Design Overview` subsection exists and mentions a core loop
  - "Monetization risks stated?" → check `### Feasibility & Viability` subsection exists and mentions monetization
  - "Aesthetic direction articulated?" → check `### Aesthetic Direction` subsection exists and contains art/audio/feel content
  - "Engagement hooks identified?" → check `### Engagement & Retention` subsection exists and mentions hooks or progression
- This is **existence-only** validation — check that the section header and relevant keywords are present, not whether the content is correct or complete
- Report missing domain criteria as warnings (not blockers)

**When domain is absent or "None":** only universal + type-specific criteria apply (backward compatible). The Domain and Domain Review Criteria lines are simply absent from the dispatch prompt — no special handling needed.

**Scope constraint preserved:** domain criteria check for EXISTENCE of game design analysis, not whether the analysis is CORRECT. Example: check "is a core loop defined?" not "is this a good core loop?"

### C4: Reference File Specifications

Each reference file provides evaluation frameworks, not static recommendations.

**C4.1: `design-frameworks.md`** (~120-150 lines)
- MDA Framework: Mechanics → Dynamics → Aesthetics with application template
- Core Loop Design: 3-layer model (Core Gameplay → Meta Game → Content Strategy)
- Bartle's Player Taxonomy: 4 primary types + extended 8-type model
- Progression Systems: vertical vs horizontal, nested loop patterns
- Genre-Mechanic Mappings: common genre archetypes with typical mechanic combinations

**C4.2: `engagement-retention.md`** (~100-130 lines)
- Hook Model: trigger → action → variable reward → investment
- Progression Mechanics: XP curves, unlock gates, mastery indicators
- Social Features: leaderboards, guilds, co-op, community integration
- Daily Engagement Patterns: daily quests, login rewards, event cycles
- Retention Frameworks: D1/D7/D30 benchmarks, churn indicators

**C4.3: `aesthetic-direction.md`** (~120-150 lines)
- Art Style Taxonomy: pixel art, low-poly, hand-drawn, realistic, abstract, mixed media
- Audio Design Dimensions: soundtrack style, SFX categories, adaptive audio, ambient design
- Game Feel/Juice: input responsiveness, particle effects, screen shake, animation easing, haptic feedback
- Mood-to-Genre Mappings: emotional tone → visual/audio treatment by genre

**C4.4: `monetization-models.md`** (~100-120 lines)
- Model Overview: premium, F2P, freemium, subscription, pay-once-expand
- Risk/Viability Indicators per model (advisory, not prescriptive)
- Solo Indie Considerations: scope vs revenue expectations, platform economics
- Anti-patterns: pay-to-win, loot box controversy, excessive advertising

**C4.5: `market-analysis.md`** (~100-120 lines)
- Competitor Analysis Framework: direct/indirect competitors, differentiation axes
- Market Sizing Approach: TAM/SAM/SOM for indie context
- Platform Selection Criteria: audience demographics, revenue share, discoverability
- Community Strategy: Discord/Reddit/TikTok as retention and marketing channels

**C4.6: `tech-evaluation-criteria.md`** (~100-120 lines)
- Evaluation Dimensions: technology-agnostic criteria such as: 2D/3D rendering capability, cross-platform support, built-in physics, asset pipeline maturity, community ecosystem size, licensing model, real-time multiplayer support
  - Dimensions are phrased as questions: "Does engine support X?" not "Engine Y has X"
- Solo Developer Constraints: learning curve, asset pipeline complexity, deployment difficulty, one-person workflow feasibility
- Performance Considerations: target hardware tiers, network requirements, storage footprint
- NOTE: MUST NOT contain specific engine recommendations — dimensions are for internet-researcher to use at Stage 2 via C2.2 query enhancement

**C4.7: `review-criteria.md`** (~60-80 lines)
- Domain review criteria list for brainstorm-reviewer dispatch
- Per-criterion explanation of what "exists" means
- Severity guidance: missing core loop = warning, missing aesthetic direction = warning

## Requirements Traceability

| Requirement | Component | Acceptance Criteria |
|---|---|---|
| FR-1 | C1 | Given game-design skill is created, when `plugins/iflow-dev/skills/game-design/SKILL.md` is checked, then it exists with <120 lines AND `references/` contains 7 files |
| FR-2 | C4.1 | Given `design-frameworks.md` is read, then it contains MDA framework, core loop model, Bartle's taxonomy, progression systems, and genre-mechanic mappings |
| FR-3 | C4.4 | Given `monetization-models.md` is read, then it presents models with risk/viability indicators AND does NOT prescribe a specific pricing strategy |
| FR-4 | C4.6 | Given `tech-evaluation-criteria.md` is read, then it provides evaluation dimensions AND contains NO specific engine/platform recommendations |
| FR-5 | C4.2 | Given `engagement-retention.md` is read, then it contains hook models, progression mechanics, social features, and retention frameworks |
| FR-6 | C4.5 | Given `market-analysis.md` is read, then it provides competitor analysis framework and market sizing approach |
| FR-7 | C4.3 | Given `aesthetic-direction.md` is read, then it contains art style taxonomy, audio design dimensions, game feel/juice, and mood-to-genre mappings |
| FR-8 | C4.7 | Given `review-criteria.md` is read, then it lists domain-specific checks with per-criterion existence definitions |
| FR-9 | C2 | Given Steps 6-8 complete, when Step 9 runs, then AskUserQuestion presents domain options including "Game Design" and "None" |
| FR-10 | C3 | Given brainstorm-reviewer receives `Domain: game-design` and criteria in `## Context`, then it checks each domain criterion against PRD content |
| FR-11 | C4.6 + Stage 2 | Given tech-evaluation-criteria.md provides dimensions, when internet-researcher runs at Stage 2, then it uses those dimensions to research current engines/platforms for this specific game concept |
| FR-12 | C2 PRD Format | Given game-design domain is active, when PRD is written, then it contains `## Game Design Analysis` with 4 subsections between Structured Analysis and Review History |
| NFR-1 | C1 | game-design SKILL.md <120 lines |
| NFR-2 | C4 | Each reference file <160 lines |
| NFR-3 | C2 | Brainstorming SKILL.md stays under 500 lines after Steps 9-10 addition |
| NFR-4 | All | No new agents required — existing agents handle game domain research |
| NFR-5 | C2, C3 | No domain selected = existing behavior unchanged: (1) brainstorming with domain="none" produces identical PRD format to pre-modification (no Game Design Analysis section), (2) brainstorm-reviewer with no Domain context applies universal + type-specific criteria only, (3) existing PRDs without domain sections are valid inputs to downstream phases |

## Behavioral Specifications

### BS-1: Domain selection is opt-in
- Step 9 includes "None" option — selecting it skips domain enrichment entirely
- No domain-related content appears in PRD when "None" is selected
- Steps 9-10 add no overhead when domain is skipped (single AskUserQuestion + skip)

### BS-2: Backward compatibility
- Brainstorming skill works identically when no domain is selected
- Brainstorm-reviewer applies only universal + type-specific criteria when no domain context is provided
- Existing PRDs without domain context are reviewed with existing criteria only

### BS-3: Graceful degradation
- If game-design SKILL.md not found: warn "Game design skill not found, proceeding without domain enrichment", skip Steps 9-10 body
- If some reference files missing: load available files, warn about missing ones, produce partial Game Design Analysis
- If all reference files missing: warn, skip domain enrichment entirely

### BS-4: Domain and method dimensions are orthogonal
- User can select BOTH a problem type (Steps 6-8) AND a domain (Steps 9-10)
- Execution order: Steps 6-8 run first (method/SCQA), then Steps 9-10 run (domain/game design)
- Method produces `## Structured Analysis` (SCQA + decomposition)
- Domain produces `## Game Design Analysis` (game frameworks)
- Both sections appear in PRD when both are active — no conflict, no replacement
- PRD section order: Research Summary → Structured Analysis → Game Design Analysis → Review History

### BS-5: Monetization is advisory only
- Reference file presents models with risk flags, not recommendations
- Game Design Analysis > Feasibility & Viability flags assumptions and risks
- MUST NOT dictate pricing strategy or recommend a specific monetization approach
- Language uses "consider", "options include", "risks to evaluate" — not "you should" or "use this"

### BS-6: Platform/engine data is research-driven
- tech-evaluation-criteria.md provides evaluation DIMENSIONS (criteria, tradeoffs, constraints)
- Actual engine/platform recommendations come from internet-researcher at Stage 2
- Reference file MUST NOT contain statements like "use Godot" or "Unity is best for..."
- Stage 2 research prompt includes tech evaluation dimensions to guide the researcher

### BS-7: Domain review criteria delivery
- Stage 6 dispatch adds `Domain: game-design` and inline criteria to `## Context`
- Format: `Domain Review Criteria:\n- Core loop defined?\n- Monetization risks stated?\n- Aesthetic direction articulated?\n- Engagement hooks identified?`
- Reviewer checks each criterion for existence (not correctness)
- Missing criteria reported as warnings (not blockers)

## Scope Boundaries

### In Scope
- New `game-design` skill with SKILL.md + 7 reference files
- Stage 1 CLARIFY additions (Steps 9-10) in brainstorming skill
- Stage 6 dispatch enhancement (domain context + review criteria)
- Brainstorm-reviewer domain criteria parsing and checking
- PRD format: Game Design Analysis section template

### Out of Scope
- Changes to Stages 3-5, 7 of brainstorming (Stage 2 gains domain-aware query enhancement via C2.2, but Stages 3-5 and 7 are unchanged)
- Changes to prd-reviewer
- New agents
- Additional domain skills (future work)
- Multi-domain composition (future work)
- Changes to validate.sh (feature adds markdown skills and agent edits; existing validation covers agent frontmatter)
- GDD generation (downstream artifact, not brainstorming concern)

## Open Questions (Resolved)

| Question | Resolution |
|---|---|
| Line budget for Steps 9-10? | ~15-18 lines. Feasible within 18-line headroom (482/500). Fallback: trim whitespace in Steps 6-8, or extract domain loading to separate skill. |
| How does domain skill load? | Cross-skill Read: replace `skills/brainstorming` with `skills/game-design` in Base directory. Same mechanism as structured-problem-solving (Feature #018). |
| How do domain criteria reach reviewer? | Inline in Stage 6 dispatch `## Context` section, same pattern as `Problem Type: {type}`. |
| Where do game sections go in PRD? | `## Game Design Analysis` placed between Structured Analysis and Review History. Additional section, not a replacement. |
| Can domain + problem type both be active? | Yes — orthogonal dimensions. Method produces Structured Analysis, domain produces Game Design Analysis. |
| What about partial skill (some refs missing)? | Load what's available, warn about missing files, produce partial analysis. Same graceful degradation as structured-problem-solving. |
