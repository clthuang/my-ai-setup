# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project-level workflow with `/iflow:create-project` command for AI-driven PRD decomposition into ordered features
- Scale detection in brainstorming Stage 7 using 6 signals with "Promote to Project" option
- `decomposing` skill orchestrating project decomposition pipeline (decompose, review, create features)
- `project-decomposer` agent for generating feature breakdown with milestones and dependencies
- `project-decomposition-reviewer` agent for validating decomposition quality
- Feature `.meta.json` extended with optional `project_id`, `module`, and `depends_on_features` fields
- New "planned" feature status for decomposition-created features
- `show-status` displays Project Features section with milestone progress
- `list-features` shows project_id column and planned features
- `session-start` hook displays project affiliation context
- `workflow-transitions` injects project context at Step 5
- `validate.sh` validates planned features and project metadata
- `docs/projects/` directory for project decomposition artifacts
- Structured problem-solving skill with SCQA framing and 5 problem type frameworks (product/feature, technical/architecture, financial/business, research/scientific, creative/design)
- Problem type classification step in brainstorming Stage 1 (Steps 6-8) with Skip option for backward compatibility
- Type-specific review criteria in brainstorm-reviewer for domain-adaptive quality checks
- Mermaid mind map visualization in PRD Structured Analysis section
- 4 reference files: problem-types.md, scqa-framing.md, decomposition-methods.md, review-criteria-by-type.md
- Game-design domain skill with 7 reference files (design-frameworks, engagement-retention, aesthetic-direction, monetization-models, market-analysis, tech-evaluation-criteria, review-criteria)
- Domain selection (Steps 9-10) in brainstorming Stage 1 for opt-in domain enrichment
- Crypto-analysis domain skill with 7 reference files (protocol-comparison, defi-taxonomy, tokenomics-models, trading-strategies, mev-classification, market-structure, risk-assessment)
- Crypto/Web3 option in brainstorming Step 9 domain selection
- Crypto-analysis criteria table in brainstorm-reviewer for domain-specific quality checks

### Changed
- Brainstorming Stage 1 CLARIFY expanded with Steps 6-8 (problem type classification, optional framework loading, metadata storage)
- PRD format gains Problem Type metadata in Status section and Structured Analysis section (SCQA framing, decomposition tree, mind map)
- Brainstorm-reviewer applies universal criteria (5) plus type-specific criteria (3) when problem type is provided
- Stage 6 READINESS CHECK dispatch now sends inline PRD content with Problem Type context
- Brainstorming Stage 2 gains domain-aware research query enhancement
- Brainstorm-reviewer gains domain criteria parsing with warning-level checks
- PRD output format gains conditional Game Design Analysis section
- Brainstorming refactored to generic domain-dispatch pattern
- Game-design Stage 2 research context moved to game-design SKILL.md
- PRD output format gains generic domain analysis section placeholder

## [2.3.0] - 2026-02-05

### Added
- Feasibility Assessment section in spec.md with 5-level confidence scale (None → Proven) and evidence requirements
- Prior Art Research stage (Stage 0) in design phase preceding architecture design
- Evidence-grounded Technical Decisions documenting alternatives, trade-offs, and principles in design
- Reasoning fields in plan.md items (Why this item, Why this order) replacing LOC estimates
- Task traceability with Why field in tasks.md linking back to plan items
- Auto-commit and auto-push after phase approval (specify, design, create-plan, create-tasks)
- Independent verification in spec-skeptic and design-reviewer agents using Context7 and WebSearch tools

### Changed
- Design phase workflow expanded to 5 stages: Prior Art Research → Architecture → Interface → Design Review → Handoff
- Plan phase removes line-of-code estimates, focuses on reasoning and traceability
- Phase approval now triggers automatic VCS commits and pushes for better workflow continuity

## [1.5.0] - 2026-02-05

### Added
- Root cause analysis command `/iflow:root-cause-analysis` for systematic bug investigation
- `rca-investigator` agent with 6-phase methodology (symptom, reproduce, hypothesize, trace, validate, document)
- `root-cause-analysis` skill with reference materials for investigation techniques

## [1.4.0] - 2026-02-04

### Added
- Secretary agent for intelligent task routing with 5 modules (Discovery, Interpreter, Matcher, Recommender, Delegator)
- `/iflow:secretary` command for manual invocation
- `inject-secretary-context.sh` hook for aware mode activation
- Activation modes: manual (explicit command) and aware (automatic via `.claude/secretary.local.md`)
- `write-control` PreToolUse hook for Write/Edit path restrictions on agent subprocesses
- `agent_sandbox/` directory for agent scratch work and investigation output
- `write-policies.json` configuration for protected/warned/safe path policies

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

## [1.1.0] - 2026-01-31

### Added
- Plugin distribution and versioning infrastructure
- Release script with conventional commit version calculation
- Marketplace configuration for local plugin development

### Changed
- Reorganized plugin structure for distribution

## [1.0.0] - 2026-01-15

### Added
- Initial iflow workflow plugin
- Core commands: brainstorm, specify, design, create-plan, create-tasks, implement, finish, verify
- Skills for each workflow phase
- Agents for code review and implementation
- Session-start and pre-commit-guard hooks
- Knowledge bank for capturing learnings
