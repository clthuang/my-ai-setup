# PRD: Semantic Memory System for Cross-Project Persistent Memory

## Status
- Created: 2026-02-19
- Last updated: 2026-02-20
- Status: Draft
- Problem Type: Technical/Architecture
- Archetype: exploring-an-idea

## SCQA Framing

**Situation:** Feature #023 (cross-project persistent memory, v2.11.0) established a working memory injection system: `memory.py` (296 lines) parses markdown knowledge bank entries, deduplicates, sorts by observation count/confidence/recency, and injects the top-N entries into session context at startup. The system works well today at ~54 entries (48 local + 6 global) with a 20-entry injection limit.

**Complication:** Three scaling limits are approaching:

1. **Relevance gap.** Ranking by observation count/confidence/recency ignores session context. At 100+ entries, high-observation entries like "Reviewer Iteration Count as Complexity Signal" (observation count 3) will always outrank "Read real file samples when parsing" (observation count 1), even in a parser-building session where the latter is directly relevant. The current system has no concept of what the session is about.

2. **Capture gap.** Entries are created only during retrospectives (after `/finish`). Learnings during sessions -- debugging insights, codebase discoveries, architectural decisions -- are lost unless manually added. At best, they're recalled imprecisely during the next retro.

3. **Richness gap.** Entries are flat text with observation count and confidence. No keyword labels for cross-topic matching. No code/file references for traceability. No reasoning chains explaining *why* a conclusion was reached. No recency or recall-frequency tracking for intelligent decay.

**Question:** How should we evolve the memory system to address relevance, capture, and richness -- while staying lightweight (GB scale, not TB), maintaining the 3-second session-start timeout, and preserving the ability to fall back to simple MD-based injection?

**Answer:** A phased approach that delivers immediate value via FTS5 keyword filtering, then incrementally adds keyword labels, mid-session capture via MCP, and finally embedding-based semantic search -- each phase validated before advancing to the next.

## Prior Art Research

### External Projects

| Project | Architecture | Key Technique | Relevance |
|---------|-------------|---------------|-----------|
| **claude-mem** | SQLite + ChromaDB, 5 lifecycle hooks, Express.js worker on port 37777 | 3-layer MCP progressive disclosure retrieval, AI-compressed summaries | Required 60-120s timeouts and async background worker -- synchronous execution too slow |
| **OpenClaw** | Markdown source of truth + SQLite overlay, sqlite-vec | Hybrid vector + BM25 with temporal decay, daily append-only logs | Closest to our architecture; markdown as source of truth matches our approach |
| **mcp-memory-service** | ChromaDB + sentence-transformers | Graph relationships between entries, MCP protocol | Heavy dependencies (ChromaDB, sentence-transformers); MCP tool pattern is portable |
| **MemCP** | Dual-store graph + vector memory | Knowledge graph linking entries by relationships | Over-engineered for our scale; graph relationships interesting at 1000+ entries |
| **SimpleMem** | 3-stage pipeline: Semantic Structured Compression, Online Semantic Synthesis, Intent-Aware Retrieval Planning | LLM-planned retrieval queries; 26.4% F1 improvement, 30x token reduction | Compression insight valuable; retrieval planning requires LLM call at query time |
| **Auto-Claude / Super-Claude-Kit** | Hook-based memory injection patterns | Lifecycle hooks for automatic capture | Similar hook architecture to ours |

### Research Findings

| Finding | Source | Implication |
|---------|--------|-------------|
| BM25 performs competitively with embeddings on corpora <500 entries | BM25 vs Vector Search benchmarks, Searchable Agent Memory blog | FTS5 is sufficient for our current and near-term scale |
| Ebbinghaus forgetting curves: retention R = e^(-t/S), recall reinforces S | MemoryBank (2023) | Recency decay + recall reinforcement is well-modeled; implement when corpus warrants it |
| sqlite-vec: single maintainer, weekend-only dev, declining sponsorship, 141 open issues | GitHub Issue #226 | Do not hard-depend; treat as optional accelerator behind an interface |
| macOS default Python lacks `enable_load_extension` | Python sqlite3 docs, macOS testing | sqlite-vec requires Homebrew Python; breaks "stdlib preferred" constraint |
| Gemini embedding API: 700ms best-case, 11s worst-case latency | Google Developer Forums | Cannot fit in 3-second session-start timeout synchronously |
| Google gemini-embedding-001: MTEB 68.32 (#1 multilingual), FREE tier | Google AI docs | Best quality-to-cost ratio when embeddings are needed |
| FTS5 IDF statistics unreliable at <200 documents | SQLite FTS5 docs, BM25 algorithm analysis | FTS5 works as binary keyword filter but noisy ranking at current scale |
| claude-mem required 60-120s timeouts, persistent Express.js worker | claude-mem GitHub | Synchronous embedding-based search at session start is architecturally challenging |

### Embedding Model Comparison

| Model | MTEB Score | Price | Dimensions | Notes |
|-------|-----------|-------|------------|-------|
| Google gemini-embedding-001 | 68.32 (#1) | Free | 768/1536/3072 | Best quality, free tier, but 700ms-11s latency |
| Voyage AI voyage-code-3 | +13.8% vs OpenAI on code | $0.06/1M tokens | 1024 | Code-specialized, free first 200M tokens |
| OpenAI text-embedding-3-small | 62.3 | $0.02/1M tokens | 512/1536 | Reliable, cost-effective |
| nomic-embed-text (Ollama) | 62.4 | Free (local) | 768 | 548MB, runs on CPU, zero API dependency |

## Advisory Analysis

### First-Principles Assessment
The core problem is correctly identified -- at scale, observation count is a poor proxy for session relevance. However, the FTS5 approach is sufficient at current scale (50 entries). BM25's IDF statistics are unreliable at <200 documents, but its binary signal (matches vs. non-matches) is useful, and the blended scoring with prominence compensates for noisy within-match ranking. The ephemeral in-memory index decision is sound first-principles thinking -- it eliminates an entire class of staleness/consistency problems.

### Pre-Mortem Assessment
**Most likely failure mode: death by latency stacking.** The 3-second session-start timeout was designed for reading local markdown files. Adding embedding API calls (Gemini: 700ms-11s), sqlite-vec extension loading (macOS compatibility unknown), and vector KNN search creates a latency stack that could silently timeout, returning zero memory context. All failures are silent by design (`2>/dev/null || memory_output=""`). A user could run for weeks with a broken memory system. **Mitigation:** Decouple embedding generation from query-time; pre-compute at write time, query with FTS5 as fast path.

### Opportunity-Cost Assessment
The completed FTS5-only spec (Feature #024, 185 lines, reviewed through 3 iterations) solves the core relevance problem with zero external dependencies and ~150 lines of new code. Reworking it into the broader scope is 5x+ the complexity for uncertain incremental value at current scale. The "do nothing" baseline is surprisingly tolerable -- at 50 entries, the failure mode is "suboptimal context injection" not "system breakdown." The original phased roadmap was prescient; trust it.

### Vision-Horizon Assessment
The reworked scope represents a time-horizon shift from a tactical 6-month improvement to a 12-24 month strategic platform build. This skips the validation checkpoints the original roadmap defined. **Platform convergence risk:** Claude Code's native auto memory is evolving monthly (topic files, per-project memory at `~/.claude/projects/`). Deeper custom investment increases sunk cost if Anthropic ships native cross-project memory with filtering. **Recommendation:** Ship FTS5 now, preserve off-ramps, phase the broader vision.

### Working-Backwards Assessment
**Press release:** "iflow's memory system now understands what you are working on. Start a parser session and it surfaces parser anti-patterns and file-reading heuristics -- even when titles don't match. Entries captured automatically from every session carry keyword labels, code references, and reasoning chains. A lesson from project A helps on project B. Toggleable, local-first, starts in under 3 seconds."

**Minimum viable deliverable that makes this true:**
1. FTS5 relevance filtering (Feature #024 spec -- done)
2. Keyword labels added during retrospectives (in-session Claude, no external API)
3. MCP `store_memory` tool for mid-session capture (lightest path to "every session")

**What can be cut:** Embeddings/vector search, Gemini API, sqlite-vec, automatic hook-based capture, forgetting curves, rich reasoning metadata. These are Phase 3b/3c items.

## User Requirements

The following 8 requirements were gathered during the brainstorm clarification session (2026-02-19). They represent the user's vision for evolving the memory system beyond Feature #024's original FTS5-only scope:

1. **Lightweight semantic search DB** -- Handle at most GB of data, not TB. Text context is unlikely to build up to TB scale.
2. **Recency measure per entry** -- More recent experiences "might" matter more. Each entry should track when it was last updated.
3. **Recall measure, actively updated** -- More frequently recalled learnings are "likely" to matter more. Track and reinforce on each injection.
4. **Max 10 keyword labels per entry** -- Use a good LLM to generate keyword labels for cross-topic matching. Tiered provider: Claude API (Haiku) first, fall back to in-session Claude, then Ollama.
5. **Code/project/feature references** -- Each entry should reference actual code files, projects, or features for traceability and explainability.
6. **Record conclusions AND reasoning/whys** -- Not just what was learned, but why it matters and how it was discovered.
7. **Toggle on/off with MD fallback** -- Long-term memory can be turned on/off; fallback to current MD-based memory injection.
8. **Automatic entry creation from every session** -- Not just from retrospectives. The DB is primary storage; markdown from retros is one data source, but there are other ways to insert entries (automatic session capture).

Additional design decisions from clarification:
- **Embeddings:** Default Google Gemini (free, MTEB #1 multilingual), user-configurable primary model, FTS5 keyword fallback. Same adapter pattern for keyword label generation.
- **Architecture:** SQLite DB is primary storage with multiple data sources (retro markdown, session capture, manual).

## Options Evaluated

### Option A: Ship Feature #024 FTS5-Only (Original Spec)
- **Description:** Implement the completed spec as-is: in-memory FTS5 index, BM25 relevance scoring blended with prominence, context signals from active feature + git diff
- **Pros:** Zero external dependencies, fits 3-second timeout easily (<10ms), already fully specced and reviewed, addresses core relevance gap immediately
- **Cons:** No semantic understanding (keyword-only), no mid-session capture, no rich metadata, no recall tracking
- **Effort:** Low (~1 day based on Feature #023 velocity)
- **Risk:** Low -- pure stdlib, ephemeral, backward-compatible

### Option B: Full Semantic Memory System (Reworked Scope)
- **Description:** Persistent SQLite + sqlite-vec for vector search, Google Gemini embeddings (user-configurable), LLM keyword labels, automatic session capture, recall/recency tracking, code references, reasoning chains, toggle with MD fallback
- **Pros:** Addresses all 8 user requirements, future-proof for 500+ entries, rich metadata enables sophisticated retrieval
- **Cons:** 5x+ implementation complexity, external API dependencies (Gemini, Claude API, Ollama), sqlite-vec macOS compatibility issues, 3-second timeout risk, maintenance burden, platform convergence risk
- **Effort:** High (~2-3 weeks estimated)
- **Risk:** High -- multiple external dependencies, untested latency stack, single-maintainer sqlite-vec

### Option C: Phased Approach (Recommended)
- **Description:** Deliver the 8 requirements across 4 phases, each with explicit trigger criteria and off-ramps. Phase 3a ships FTS5 immediately, subsequent phases add richness as corpus grows and validates need.
- **Pros:** Immediate value from Phase 3a, each phase independently valuable and testable, preserves platform convergence off-ramp, validates assumptions before committing
- **Cons:** Slower to reach full vision, requires discipline to maintain phased roadmap
- **Effort:** Low per phase, medium-high cumulative
- **Risk:** Low per phase, managed overall

## Decision Matrix

| Criterion (weight) | Option A: FTS5-Only | Option B: Full System | Option C: Phased |
|---------------------|--------------------|-----------------------|------------------|
| **Immediate value** (25%) | 9 -- ships now, solves relevance gap | 3 -- weeks to ship | 9 -- Phase 3a ships now |
| **Completeness** (20%) | 4 -- relevance only | 9 -- all 8 requirements | 8 -- all 8 requirements over time |
| **Risk** (20%) | 9 -- zero dependencies, proven approach | 3 -- multiple external deps, untested latency | 8 -- risk spread across phases |
| **Maintainability** (15%) | 9 -- stdlib only, ephemeral | 4 -- persistent DB, API integrations, extension loading | 7 -- each phase self-contained |
| **Future-proofing** (10%) | 5 -- good off-ramp but limited ceiling | 7 -- rich foundation but high sunk cost | 9 -- validates before committing, preserves off-ramps |
| **Effort efficiency** (10%) | 8 -- high ROI for low effort | 4 -- high effort for uncertain incremental value | 7 -- effort matched to validated need |
| **Weighted total** | **7.50** | **4.85** | **8.10** |

**Scoring rationale for contentious scores:**
- Option A Completeness (4): Solves the most pressing gap (relevance) but does not address capture, richness, or recall tracking -- 5 of 8 requirements are unaddressed.
- Option A Future-proofing (5): Good off-ramp (can extend later) but limited ceiling without persistent state or embeddings. Scored lower than C because C explicitly plans the extension path.
- Option B Future-proofing (7): Rich foundation but high sunk cost reduces pivot flexibility. Scored lower than C because accumulated investment makes abandonment harder if Anthropic ships native.
- Option C Maintainability (7): Each phase is self-contained but cumulative complexity grows. Scored lower than A because the final state (Phase 3d) approaches Option B's complexity.

**Decision: Option C (Phased Approach)**

## Phased Roadmap

### Phase 3a: FTS5 Relevance Filtering (Feature #024 -- immediate)
**Trigger:** Now -- relevance gap already observable at 35+ entries.

**Scope:** Implement the existing Feature #024 spec as-is:
- Context signal collection (active feature description, current phase, git diff keywords)
- In-memory FTS5 index (ephemeral, rebuilt each session)
- BM25 relevance scoring blended with prominence (configurable weight)
- Category balance preserved
- Diagnostic output for debugging
- Backward-compatible fallback when no context signals

**What this addresses (from 8 requirements):**
- Requirement 3 (recency): prominence_score includes recency weighting
- Requirement 8 (toggle): `memory_injection_enabled` already exists; `memory_relevance_weight: 0.0` disables relevance
- Partial requirement 1 (semantic search): keyword-based, not embedding-based, but sufficient at current scale

**Effort:** ~1 day. **Dependencies:** None. **Files:** `memory.py`, `session-start.sh`, config template.

### Phase 3b: Keyword Labels + Rich Metadata (when corpus reaches ~80 entries)
**Trigger:** Corpus exceeds ~80 entries AND FTS5 keyword matching shows precision gaps (relevant entries not surfaced because their text doesn't overlap with context signals).

**Scope:**
- Extend retrospecting skill Step 4 to generate 3-10 keyword labels per entry using in-session Claude (no external API call -- the model is already running during retro)
- Add keyword labels to knowledge bank markdown format: `- Keywords: parsing, files, error-handling, design-patterns`
- FTS5 indexes keyword labels alongside name/description, expanding matching surface
- Add code/file references to entries: `- References: plugins/iflow-dev/hooks/lib/memory.py, docs/features/024-*/spec.md`
- Add reasoning field: `- Reasoning: Discovered during parser feature that...`
- Extend entry schema for recall_count and last_recalled_at tracking

**What this addresses:**
- Requirement 5 (keyword labels): LLM-generated during retro, no external API
- Requirement 6 (code references): File paths captured from git diff during retro
- Requirement 7 (reasoning/whys): Reasoning field in knowledge bank format
- Requirement 4 (recall measure): recall_count incremented on injection, stored in `.last-injection.json`

**Effort:** ~2-3 days. **Dependencies:** Phase 3a. **Files:** `memory.py`, retrospecting skill, knowledge bank format.

### Phase 3c: MCP Memory Tools + Session Capture (when retro-only capture proves insufficient)
**Trigger:** User manually adds entries outside the retro workflow more than 3 times in a 2-week period, OR retro captures fewer than 50% of learnings discussed mid-session (assessed by comparing session topics with retro entries over a 2-week sample).

**Scope:**
- MCP server with `store_memory` tool: model can save a learning mid-session
- Entries stored in `session-captures.jsonl` staging file (one JSON object per line)
- Staging entries promoted/deduplicated during next retrospective
- LLM keyword generation for staged entries (using tiered provider: Claude API Haiku → in-session Claude → Ollama)
- User-configurable embedding provider adapter pattern (interface designed but implementation deferred to Phase 3d unless needed)

**What this addresses:**
- Requirement 8 partially (automatic from every session): model-initiated via MCP tool, not fully automatic
- Requirement 5 (keyword labels): Tiered LLM generation for staged entries

**Effort:** ~3-5 days. **Dependencies:** Phase 3a (FTS5 index). Phase 3b is not required -- keyword labels enhance captured entries but are not a prerequisite for the capture mechanism. **Files:** New MCP server, `memory.py`, retrospecting skill.

### Phase 3d: Embedding-Based Semantic Search (when FTS5+keywords demonstrably fails)
**Trigger:** Corpus exceeds 200 entries AND FTS5 + keyword match rate (percentage of sessions where at least one FTS5-matched entry appears in the injected set) drops below 80%, measured by comparing FTS5 MATCH results against final injected entries in the diagnostic output over a 2-week sample.

**Scope:**
- Persistent SQLite database (replaces ephemeral in-memory index)
- Pre-computed embeddings stored at write time (retro/MCP capture), NOT at query time
- User-configurable embedding provider: Google Gemini (default, free), Voyage AI, OpenAI, nomic-embed-text via Ollama
- Query embedding at session start using local Ollama model (fast, no network) or FTS5 fast path with async vector enrichment
- Hybrid retrieval: FTS5 BM25 (fast path) + vector cosine similarity (enrichment)
- Ebbinghaus-inspired decay: `relevance = base_score * e^(-t/S)` where S is reinforced by recall_count
- sqlite-vec or alternative vector backend behind adapter interface

**What this addresses:**
- Requirement 1 (semantic search DB): Full embedding-based retrieval
- Requirement 2 (lightweight/efficient): SQLite single-file, GB scale
- Requirement 3 (recency): Ebbinghaus decay model
- Requirement 4 (recall): Recall-reinforced memory strength

**Effort:** ~1-2 weeks. **Dependencies:** Phase 3c. **Files:** `memory.py`, new embedding adapter, SQLite schema.

**Off-ramp:** Before Phase 3d, evaluate whether Claude Code's native memory has converged on cross-project filtering. **Adopt native if it supports:** (a) cross-project entry aggregation and (b) context-aware relevance ranking. Check at each phase gate by reviewing Claude Code changelog and testing native memory capabilities against the Phase 3d success criteria.

### Phase 4: MCP Server for Mid-Session Pull-Based Retrieval (future)
**Trigger:** Push-based injection at session start proves insufficient -- model needs to query memory mid-session for specific topics.

**Scope:** Full MCP server exposing `search_memory`, `store_memory`, `list_memories` tools. This is the original PRD Phase 4 vision.

**Off-ramp:** If Anthropic ships native MCP-based memory tools, adopt those instead.

## Technical Architecture (Cross-Phase)

### Entry Schema (Phase 3b+)
```
Entry:
  id: str                    # content_hash (SHA-256 first 16 hex)
  name: str                  # Short title
  description: str           # Full description with conclusions
  reasoning: str             # Why this conclusion was reached
  category: str              # anti-patterns | patterns | heuristics (matches existing knowledge bank files)
  keywords: list[str]        # Max 10, LLM-generated
  references: list[str]      # Code files, features, projects
  observation_count: int     # Times observed across retros
  confidence: str            # high | medium | low
  recall_count: int          # Times injected into sessions
  last_recalled_at: str      # ISO timestamp of last injection
  created_at: str            # ISO timestamp
  updated_at: str            # ISO timestamp
  source: str                # retro | session-capture | manual
  source_project: str        # Project where entry originated
```

### Storage Architecture
```
Phase 3a: Markdown files (source of truth) + ephemeral in-memory FTS5
Phase 3b: Markdown files (source of truth) + ephemeral in-memory FTS5 + recall tracking in .last-injection.json
Phase 3c: Markdown files + session-captures.jsonl staging + ephemeral FTS5
Phase 3d: SQLite DB (primary) + markdown files (legacy import) + persistent FTS5 + vector index
```

### Embedding Provider Adapter (Phase 3d)
```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimensions(self) -> int: ...

# Implementations: GeminiProvider, VoyageProvider, OpenAIProvider, OllamaProvider
# Config: memory_embedding_provider in iflow-dev.local.md
# Fallback chain: configured provider -> FTS5 keyword search
```

### Keyword Generation Adapter (Phase 3b+)
```python
class KeywordGenerator(Protocol):
    def generate(self, text: str, max_keywords: int = 10) -> list[str]: ...

# Tiered: in-session Claude (during retro) -> Claude API Haiku -> Ollama
# In-session Claude is free (model already running during retro)
```

### Retrieval Pipeline (Final State, Phase 3d)
```
Session Start (3-second budget):
  1. Collect context signals (active feature, phase, git diff) [<50ms]
  2. Build FTS5 query from signals [<1ms]
  3. Run FTS5 MATCH for keyword candidates [<5ms]
  4. If embeddings available: query vector index for semantic candidates [<10ms with pre-computed]
  5. Merge + re-rank with hybrid scoring [<1ms]
  6. Apply category balance + limit [<1ms]
  7. Format output with diagnostics [<1ms]
  Total: <70ms estimated (verify during Phase 3d implementation; git subprocess timing is load-dependent)
```

## Configuration

### Existing (Phase 3a)
```yaml
memory_injection_enabled: true
memory_injection_limit: 20
memory_relevance_weight: 0.6  # 0.0 = pure prominence, 1.0 = pure relevance
```

### Phase 3b Additions
```yaml
memory_keyword_generation: true  # Generate keywords during retro
memory_recall_tracking: true     # Track recall counts
```

### Phase 3c Additions
```yaml
memory_session_capture: true     # Enable MCP store_memory tool
memory_keyword_provider: auto    # auto | claude-api | ollama
```

### Phase 3d Additions
```yaml
memory_embedding_enabled: true        # Enable vector search
memory_embedding_provider: gemini     # gemini | voyage | openai | ollama
memory_embedding_fallback: fts5       # Fallback when embedding unavailable
memory_decay_enabled: true            # Ebbinghaus-inspired decay
```

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 3-second timeout exceeded by embedding API calls | High (if synchronous) | Silent failure, zero memory context | Pre-compute embeddings at write time; FTS5 fast path at query time |
| sqlite-vec macOS incompatibility (load_extension unavailable) | High on default Python | Vector search non-functional | Adapter pattern; FTS5 primary until vector proven necessary |
| sqlite-vec project maintenance decline | Medium | No updates, potential breaking changes | Abstract behind interface; numpy brute-force as fallback at small scale |
| Gemini API rate limits / availability | Medium | Embedding generation fails | Tiered fallback: Gemini -> Ollama local -> skip embeddings |
| Auto-extracted entries dilute quality | Medium | Memory becomes noise-dominated | Staging file + retro promotion; minimum observation_count before injection |
| Claude Code ships native cross-project memory | Medium (6-12 months) | Custom system becomes redundant | Phased approach preserves off-ramps; at each phase gate, check if native supports cross-project aggregation + relevance ranking |
| FTS5 BM25 ranking noise at small corpus | Low-Medium | Suboptimal ranking within matches | Blend with prominence score (configurable weight); binary match signal still useful |

## Success Criteria

### Overall (cross-phase)
The memory system is considered successful when: (a) contextually relevant entries appear in the injected set in >90% of sessions with an active feature (measured via diagnostic output showing FTS5 match count > 0), (b) learnings from all workflow-engaged sessions are captured (via retro or MCP tool), and (c) entries include enough metadata for cross-project discovery.

### Phase 3a (measurable)
1. Given a 30-entry test fixture with "parser" entries mixed in, context_query="parser file reading" surfaces at least 7 of 10 parser entries in top 20
2. Fallback to prominence-only when context_query is None produces identical results to relevance_weight=0.0
3. No disk files created (in-memory only)
4. Completes within 500ms on 200-entry fixture
5. `./validate.sh` passes

### Phase 3b (measurable)
1. Retro-generated entries include 3-10 keyword labels each
2. FTS5 matching on keyword labels surfaces entries not findable by description text alone
3. recall_count incremented on each injection; entries with higher recall_count are available for decay calculation

### Phase 3c (qualitative + measurable)
1. MCP `store_memory` tool successfully captures an entry mid-session
2. Staged entries appear in retro for promotion/dedup
3. User reports fewer "lost learnings" (qualitative)

### Phase 3d (measurable)
1. Hybrid retrieval (vector + FTS5) outperforms FTS5-only on a curated test set of 200+ entries with known relevant pairs
2. Session-start injection completes within 3 seconds including vector query (pre-computed embeddings)
3. Embedding provider swap (Gemini -> Ollama) produces valid results with no code changes

## Scope Boundaries

### In Scope (All Phases)
- FTS5-based relevance filtering with context signals
- Keyword label generation during retrospectives
- Rich entry metadata (references, reasoning, recall tracking)
- MCP tool for mid-session memory capture
- Embedding-based semantic search with user-configurable provider
- Toggle on/off with MD-based fallback
- Phased delivery with explicit trigger criteria and off-ramps

### Out of Scope
- Real-time streaming memory (continuous capture during every tool call)
- Multi-user / team-shared memory
- Memory visualization UI
- Graph-based knowledge relationships (MemCP-style)
- Custom embedding model training/fine-tuning
- Integration with external knowledge bases (Confluence, Notion, etc.)
- Changes to the retrospective workflow beyond adding keyword generation
- Persistent index rebuilt on retro write (original PRD Phase 3 approach -- replaced with ephemeral for 3a)

## Dependencies

- Python 3.9+ with sqlite3 + FTS5 (stdlib, all phases)
- Claude model access during retro (in-session, Phase 3b+)
- Claude API / Ollama (optional, Phase 3c+ for keyword generation)
- Google Gemini API / Ollama (optional, Phase 3d for embeddings)
- sqlite-vec or alternative (optional, Phase 3d for vector search)
- MCP server infrastructure (Phase 3c+)

## Appendix: User Requirements Traceability

| # | User Requirement | Phase | How Addressed |
|---|-----------------|-------|---------------|
| 1 | Lightweight/efficient semantic search DB (GB not TB) | 3d | SQLite single-file DB with FTS5 + vector index |
| 2 | Recency measure per entry | 3a | prominence_score includes recency weighting; 3d adds Ebbinghaus decay |
| 3 | Recall measure, actively updated | 3b | recall_count in .last-injection.json, incremented on each injection |
| 4 | Max 10 keyword labels, LLM-generated | 3b | In-session Claude during retro; tiered API for session captures |
| 5 | Code/project/feature references | 3b | references field populated from git diff during retro |
| 6 | Record conclusions AND reasoning/whys | 3b | reasoning field in knowledge bank entry format |
| 7 | Toggle on/off with MD fallback | 3a | memory_injection_enabled config; relevance_weight=0.0 for pure prominence |
| 8 | Automatic entry creation from every session | 3c | MCP store_memory tool (model-initiated); staging + retro promotion |

*Source: Brainstorm clarification session 2026-02-19, gathered via /iflow-dev:brainstorm Stage 1 Q&A*
