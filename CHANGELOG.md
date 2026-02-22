# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- MCP memory server configuration now portable across projects via `plugin.json` `mcpServers` with `${CLAUDE_PLUGIN_ROOT}` variable substitution (replaces project-level `.mcp.json`)

### Added
- `run-memory-server.sh` bootstrap wrapper for MCP memory server with venv Python → system Python fallback and automatic dependency bootstrapping
- `validate.sh` checks for stale `.mcp.json` files and validates `mcpServers` script paths

## [3.0.15] - 2026-02-22

### Added
- `test-deepener` agent — spec-driven adversarial testing across 6 dimensions; Phase A generates a test outline, Phase B writes executable tests; dispatched by `/implement` as the new Test Deepening Phase
- Test Deepening Phase (Step 6) in `/implement` workflow — runs after code simplification, before review; reports spec divergences with fix/accept/manual-review control flow
- Secretary fast-path: 'deepen tests', 'add edge case tests', and 'test deepening' patterns route directly to `test-deepener` at 95% confidence

## [3.0.14] - 2026-02-22

### Added
- Working Standards section in CLAUDE.md: stop-and-replan rule, verification for all work, autonomous bug fixing posture, learning capture on correction, simplicity check

## [3.0.13] - 2026-02-21

### Fixed
- Plan mode hooks (plan review, post-approval workflow) no longer incorrectly skipped when an iflow feature is active

## [3.0.12] - 2026-02-21

### Added
- Secretary fast-path routing: known specialist patterns skip discovery, semantic matching, and reviewer gate
- Secretary Workflow Guardian: feature requests auto-route to correct workflow phase based on active feature state
- Secretary plan-mode routing: unmatched simple tasks route to Claude Code plan mode instead of dead-ending
- Secretary web/library research tools (WebSearch, WebFetch, Context7) for scoping unfamiliar domains

### Changed
- Secretary conditional reviewer gate: reviewer skipped for high-confidence matches (>85%)
- Secretary-reviewer model changed from opus to haiku
- Data science components renamed with `ds-` prefix (`analysis-reviewer`, `review-analysis`, `choosing-modeling-approach`, `spotting-analysis-pitfalls`)

## [3.0.11] - 2026-02-21

### Added
- `/wrap-up` command for finishing work done outside iflow feature workflow (plan mode, ad-hoc tasks)
- PostToolUse hooks for plan mode integration: plan review before approval (EnterPlanMode), task breakdown and implementation workflow after approval (ExitPlanMode)
- `plan_mode_review` configuration option to enable/disable plan mode review hooks

### Changed
- Renamed `/finish` to `/finish-feature` to distinguish from the new `/wrap-up` command

## [3.0.10] - 2026-02-21

### Added
- Automatic learning capture in all 5 core phase commands (specify, design, create-plan, create-tasks, implement) — recurring review issues persisted to long-term memory
- Learning capture in `/root-cause-analysis` command — root causes and recommendations persisted to memory

### Fixed
- Retro fallback path now persists learnings to knowledge bank and semantic memory (Steps 4, 4a, 4c) instead of silently dropping them

## [3.0.9] - 2026-02-21

### Fixed
- CHANGELOG backfill for missing version entries

## [3.0.8] - 2026-02-21

### Added
- `/remember` command for manually capturing learnings to long-term memory
- `capturing-learnings` skill for model-initiated learning capture with configurable modes (ask-first, silent, off)
- `memory_model_capture_mode` and `memory_silent_capture_budget` configuration keys
- Optional `confidence` parameter (high/medium/low, defaults to medium) for `store_memory` MCP tool
- Memory capture hints in session-start context for model-initiated learning capture

## [3.0.7] - 2026-02-21

### Changed
- Secretary delegation hardened with workflow prerequisite validation

## [3.0.6] - 2026-02-21

### Added
- Source-hash deduplication for knowledge bank backfill

## [3.0.5] - 2026-02-20

### Fixed
- Venv Python used consistently in session-start hook

## [3.0.4] - 2026-02-20

### Fixed
- Memory injection failure from module naming conflict (`types.py` renamed to `retrieval_types.py`)

## [3.0.3] - 2026-02-20

### Changed
- Plugin configuration consolidated into single file

## [3.0.2] - 2026-02-20

### Added
- `search_memory` MCP tool for on-demand memory retrieval
- Enhanced retrieval context signals (active feature, current phase, git branch)

### Fixed
- Secretary routing hardened to prevent dispatch bypass

## [3.0.1] - 2026-02-20

### Added
- `setup-memory` script for initial memory database population
- Knowledge bank backfill from existing pattern/anti-pattern/heuristic files

### Fixed
- README documentation drift synced with ground truth detection

## [3.0.0] - 2026-02-20

### Added
- Semantic memory system with embedding-based retrieval using cosine similarity and hybrid ranking
- `store_memory` and `search_memory` MCP tools for mid-session memory capture and on-demand search
- Enhanced retrieval context signals: active feature, current phase, git branch, recently changed files
- Memory toggle configuration: `memory_semantic_enabled`, `memory_embedding_provider`, `memory_embedding_model`
- SQLite-backed memory database (`memory.db`) with legacy fallback support
- Setup-memory script and knowledge bank backfill with source-hash deduplication

### Fixed
- Secretary routing hardened to prevent dispatch bypass
- Plugin config consolidated into single file
- Venv Python used consistently in session-start hook

## [2.11.0] - 2026-02-17

### Added
- Cross-project persistent memory system with global memory store (`~/.claude/iflow/memory/`)
- Memory injection in session-start hook for cross-project context

## [2.10.2] - 2026-02-17

### Added
- Working-backwards advisor with deliverable clarity gate for high-uncertainty brainstorms

## [2.10.1] - 2026-02-17

### Added
- Secretary-driven advisory teams for generalized brainstorming

## [2.10.0] - 2026-02-14

### Added
- Data science domain skills for brainstorming enrichment
- Secretary-driven advisory teams for generalized brainstorming
- Working-backwards advisor with deliverable clarity gate for high-uncertainty brainstorms

### Changed
- Release script blanket iflow-dev to iflow conversion improved

## [2.9.0] - 2026-02-13

### Changed
- Implementing skill rewritten with per-task dispatch loop
- Knowledge bank validation step added to retrospecting skill
- Implementation-log reading added to retrospecting skill

## [2.8.6] - 2026-02-13

### Fixed
- YOLO-guard hook hardened with wildcard matcher and fast-path optimization

## [2.8.5] - 2026-02-11

### Added
- AORTA retrospective framework with retro-facilitator agent

## [2.8.4] - 2026-02-11

### Added
- YOLO mode for fully autonomous workflow

## [2.8.3] - 2026-02-11

### Changed
- All agents set to model: opus for maximum capability

## [2.8.2] - 2026-02-10

### Changed
- `/finish` improved with CLAUDE.md updates and better defaults

## [2.8.1] - 2026-02-10

### Changed
- Reviewer cycles strengthened across all workflow phases

## [2.8.0] - 2026-02-10

### Added
- `/iflow:create-project` command for AI-driven PRD decomposition into ordered features
- Scale detection in brainstorming Stage 7 with "Promote to Project" option
- `decomposing` skill orchestrating project decomposition pipeline
- `project-decomposer` and `project-decomposition-reviewer` agents
- Feature `.meta.json` extended with `project_id`, `module`, `depends_on_features`
- "planned" feature status for decomposition-created features
- `show-status` displays Project Features section with milestone progress
- YOLO mode for fully autonomous workflow
- AORTA retrospective framework with retro-facilitator agent

### Changed
- `/finish` improved with CLAUDE.md updates and better defaults
- Reviewer cycles strengthened across all workflow phases
- All agents set to model: opus for maximum capability

## [2.7.2] - 2026-02-10

### Changed
- No-time-estimates policy enforced across plan and task components

## [2.7.1] - 2026-02-10

### Fixed
- Plugin best practices audit fixes

## [2.7.0] - 2026-02-09

### Added
- Crypto-analysis domain skill with 7 reference files (protocol-comparison, defi-taxonomy, tokenomics-models, trading-strategies, mev-classification, market-structure, risk-assessment)
- Crypto/Web3 option in brainstorming Step 9 domain selection
- Crypto-analysis criteria table in brainstorm-reviewer for domain-specific quality checks

## [2.6.0] - 2026-02-07

### Added
- Game-design domain skill with 7 reference files (design-frameworks, engagement-retention, aesthetic-direction, monetization-models, market-analysis, tech-evaluation-criteria, review-criteria)
- Domain selection (Steps 9-10) in brainstorming Stage 1 for opt-in domain enrichment

### Changed
- Brainstorming refactored to generic domain-dispatch pattern
- PRD output format gains conditional domain analysis section

## [2.5.0] - 2026-02-07

### Added
- Structured problem-solving skill with SCQA framing and 5 problem type frameworks (product/feature, technical/architecture, financial/business, research/scientific, creative/design)
- Problem type classification step in brainstorming Stage 1 (Steps 6-8) with Skip option
- Type-specific review criteria in brainstorm-reviewer for domain-adaptive quality checks
- Mermaid mind map visualization in PRD Structured Analysis section
- 4 reference files: problem-types.md, scqa-framing.md, decomposition-methods.md, review-criteria-by-type.md

### Changed
- Brainstorming Stage 1 CLARIFY expanded with Steps 6-8 (problem type classification, optional framework loading, metadata storage)
- PRD format gains Problem Type metadata and Structured Analysis section (SCQA framing, decomposition tree, mind map)
- Brainstorm-reviewer applies universal criteria plus type-specific criteria when problem type is provided

## [2.4.0] - 2026-02-05

### Added
- Feasibility Assessment section in spec.md with 5-level confidence scale (None to Proven) and evidence requirements
- Prior Art Research stage (Stage 0) in design phase preceding architecture design
- Evidence-grounded Technical Decisions documenting alternatives, trade-offs, and principles in design
- Reasoning fields in plan.md items (Why this item, Why this order) replacing LOC estimates
- Task traceability with Why field in tasks.md linking back to plan items
- Auto-commit and auto-push after phase approval (specify, design, create-plan, create-tasks)
- Independent verification in spec-reviewer and design-reviewer agents using Context7 and WebSearch tools

### Changed
- Design phase workflow expanded to 5 stages: Prior Art Research, Architecture, Interface, Design Review, Handoff
- Plan phase removes line-of-code estimates, focuses on reasoning and traceability
- Phase approval now triggers automatic VCS commits and pushes for better workflow continuity

### Fixed
- Component formats standardized; 103 validate.sh warnings eliminated
- Spec-skeptic agent renamed to spec-reviewer
- Show-status rewritten as workspace dashboard

## [2.4.5] - 2026-02-07

### Fixed
- Release script uses `--ci` flag in agent workflows

## [2.4.4] - 2026-02-07

### Fixed
- Component formats standardized across all plugin files
- 103 validate.sh warnings eliminated

## [2.4.3] - 2026-02-07

### Changed
- Documentation and MCP config relocated

## [2.4.2] - 2026-02-07

### Added
- Pre-merge validation step in `/finish` Phase 5
- Discovery-based scanning in documentation agents

### Changed
- `show-status` rewritten as workspace dashboard
- READMEs updated with complete commands, skills, and agents inventory

### Fixed
- validate.sh `set -e` crash fixed with Anthropic best-practice checks

## [2.4.1] - 2026-02-05

### Changed
- Spec-skeptic agent renamed to spec-reviewer

## [2.3.1] - 2026-02-05

### Added
- Workflow overview diagram in plugin README

## [2.3.0] - 2026-02-05

### Changed
- Review system redesigned with two-tier pattern
- Workflow state transitions hardened
- Description patterns standardized to 'Use when' format

## [2.2.0] - 2026-02-05

### Added
- Root cause analysis command `/iflow:root-cause-analysis` for systematic bug investigation
- `rca-investigator` agent with 6-phase methodology (symptom, reproduce, hypothesize, trace, validate, document)
- `root-cause-analysis` skill with reference materials for investigation techniques

## [2.1.0] - 2026-02-04

### Added
- `write-control` PreToolUse hook for Write/Edit path restrictions on agent subprocesses (replaced by centralized guidelines in v2.1.1)
- `agent_sandbox/` directory for agent scratch work and investigation output
- `write-policies.json` configuration for protected/warned/safe path policies

## [2.1.1] - 2026-02-04

### Changed
- Write-control hook removed, guidelines centralized into agent instructions

## [2.0.0] - 2026-02-04

### Added
- Secretary agent for intelligent task routing with 5 modules (Discovery, Interpreter, Matcher, Recommender, Delegator)
- `/iflow:secretary` command for manual invocation
- `inject-secretary-context.sh` hook for aware mode activation
- Activation modes: manual (explicit command) and aware (automatic via `.claude/iflow-dev.local.md`)

## [1.7.0] - 2026-02-04

### Added
- GitHub Actions workflow for manual releases

### Changed
- `/finish` streamlined with 6-phase automatic process
- `/implement` restructured with multi-phase review and automated review iterations
- `/create-tasks` gains two-stage review with task-breakdown-reviewer agent
- Plugin quality patterns applied across skills and agents

## [1.7.1] - 2026-02-04

### Changed
- `/implement` gains automated review agent iterations
- Plugin quality patterns applied across skills and agents

## [1.6.1] - 2026-02-03

### Added
- `/create-plan` gains two-stage review with plan-reviewer agent
- Code change percentage-based version bumping in release script

### Fixed
- Dev version simplified to mirror release version
- Subshell variable passing fixed for change stats

## [1.6.0] - 2026-02-03

### Added
- `/create-plan` gains two-stage review with plan-reviewer agent
- Code change percentage-based version bumping in release script

### Fixed
- `get_last_tag` uses git tag sorting instead of `git describe`
- Dev version simplified to mirror release version
- Subshell variable passing fixed for change stats

## [1.5.0] - 2026-02-03

### Added
- 4-stage design workflow with design-reviewer agent

## [1.4.0] - 2026-02-03

### Changed
- PRD file naming standardized to `YYYYMMDD-HHMMSS-{slug}.prd.md` format

## [1.3.0] - 2026-02-03

### Added
- Enhanced brainstorm-to-PRD workflow with 6-stage process (clarify, research, draft, review, correct, decide)
- 4 new research/review agents: `internet-researcher`, `codebase-explorer`, `skill-searcher`, `prd-reviewer`
- PRD output format with evidence citations and quality criteria checklist
- Parallel subagent invocation for research stage
- Auto-correction of PRD issues from critical review

### Changed
- `/iflow:brainstorm` now produces `.prd.md` files instead of `.md` files
- Brainstorming skill rewritten for structured PRD generation with research support

## [1.2.0] - 2026-02-02

### Added
- Two-plugin coexistence model: `iflow` (production) and `iflow-dev` (development)
- Pre-commit hook protection for `plugins/iflow/` directory
- `IFLOW_RELEASE=1` environment variable bypass for release script
- Version format validation in `validate.sh` (iflow: X.Y.Z, iflow-dev: X.Y.Z-dev)
- Sync-cache hook now syncs both plugins to Claude cache

### Changed
- Release script rewritten for copy-based workflow (copies iflow-dev to iflow on release)
- Plugin directory structure: development work in `plugins/iflow-dev/`, releases in `plugins/iflow/`
- README.md updated with dual installation instructions
- README_FOR_DEV.md updated with two-plugin model documentation

### Removed
- Branch-based marketplace name switching
- Marketplace format conversion during release

## [1.1.0] - 2026-02-01

### Added
- Plugin distribution and versioning infrastructure
- Release script with conventional commit version calculation
- Marketplace configuration for local plugin development

### Changed
- Reorganized plugin structure for distribution

## [1.0.0] - 2026-01-31

### Added
- Initial iflow workflow plugin
- Core commands: brainstorm, specify, design, create-plan, create-tasks, implement, finish, verify
- Skills for each workflow phase
- Agents for code review and implementation
- Session-start and pre-commit-guard hooks
- Knowledge bank for capturing learnings
