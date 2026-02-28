# Critical Review: Entity Registry & Knowledge Bank Systems

**Date:** 2026-02-27
**Purpose:** Assess current architecture for expansion into a unified context management system, knowledge graph, and RAG optimized for coding agents.

---

## Executive Summary

Both systems are well-engineered for their current scope — clean code, good test coverage (184 entity tests, ~5,000 lines of memory tests), graceful degradation, and pragmatic SQLite choices. However, they are **two independent systems that should converge** to support the knowledge graph / RAG vision.

---

## 1. The Core Problem: Two Disconnected Systems

The entity registry and knowledge bank are completely disconnected. Separate databases, separate MCP servers, separate schemas, no foreign keys, no shared identifiers.

**What this means concretely:**
- A memory entry about "never use shallow merge in feature X" has no link to `feature:X` in the entity DB
- When you ask "what did we learn from feature 029?", there's no join path — you'd grep for "029" in description text
- Entity lineage gives you structure (brainstorm -> feature), memory gives you knowledge (patterns, anti-patterns), but nothing connects *knowledge to structure*

**For a knowledge graph, you need edges between these.** Currently there are two disconnected subgraphs.

---

## 2. Entity Registry Assessment

### Strengths
- Circular reference detection via recursive CTE
- Immutability triggers on type_id/entity_type/created_at
- Backfill with topological ordering (backlog -> brainstorm -> project -> feature)
- WAL mode + busy_timeout — production-ready concurrency
- Comprehensive test coverage (184 tests in 0.91s)
- Graceful error handling (MCP tools never raise)

### Problems for Future Expansion

**Fixed entity types are a straitjacket.**
`CHECK(entity_type IN ('backlog','brainstorm','project','feature'))` is hardcoded in the schema. Adding `session`, `conversation`, `code_change`, `decision`, `dependency`, `agent_run` requires a migration each time. A knowledge graph needs flexible node types.

**Single parent_type_id = tree, not graph.**
Real relationships are multi-dimensional:
- A feature *originated from* a brainstorm
- A feature *depends on* features X, Y (currently shoved into metadata JSON)
- A feature *was implemented during* sessions A, B, C
- A pattern *was discovered in* feature Z
- A decision *affects* features P, Q

Storing `depends_on_features` in a JSON blob inside metadata is a sign the data model is fighting the domain.

**No deletion.**
Cannot remove entities. No soft-delete with `is_deleted` + `deleted_at`. The entity registry has no lifecycle management — entities appear and never change state in practice.

**INSERT OR IGNORE is a footgun.**
Registering the same type_id with *different* data silently does nothing. No upsert, no conflict detection, no warning. Stale data persists indefinitely.

**No audit trail.**
`created_at` and `updated_at` but no change log, no who/why tracking. For a knowledge graph, provenance is essential.

**Status field is freeform.**
No enum validation; allows arbitrary strings. No defined lifecycle states or transitions.

---

## 3. Knowledge Bank Assessment

### Strengths
- Hybrid retrieval (vector + BM25 + prominence) is genuinely well-designed
- 4 embedding providers (Gemini, OpenAI, Ollama, Voyage) with NormalizingWrapper
- Category-balanced selection prevents monoculture in injections
- Prominence scoring (observation count, recency, recall, confidence) is thoughtful
- Content-hash dedup is elegant
- ~5,000 lines of test code for ~8,400 lines of implementation

### Problems for Future Expansion

**Knowledge is just text blobs.**
Every entry is (name, description, reasoning, category). No structure to express:
- "Pattern A contradicts Anti-pattern B"
- "This heuristic applies when condition X holds"
- "This pattern was superseded by pattern Y"
- "This anti-pattern has 3 known exceptions"

**Keywords are dead code.**
`TieredKeywordGenerator` only contains `SkipKeywordGenerator`. Every entry has `keywords: []`. BM25 search runs on name + description only, missing the keyword signal entirely.

**Dual-path problem.**
`memory.py` (legacy) and `semantic_memory/` (new) do similar things with different capabilities. Legacy has no embeddings, different selection logic, different output format. Doubles maintenance cost.

**Observation count inflation.**
Every upsert increments `observation_count` even when nothing changed. Frequently-imported entries dominate prominence scores regardless of actual utility. No decay mechanism.

**No negative signal.**
Tracks `recall_count` (how often injected) but not "was this helpful?" If an entry keeps getting injected and the agent ignores it, that signal is lost.

---

## 4. Integration Architecture Gaps

| Gap | Impact on RAG for Coding Agents |
|-----|------|
| No session/conversation tracking | Can't learn from agent interactions over time |
| No code change linking | Can't associate knowledge with actual commits/diffs |
| No temporal context | "What was the state of knowledge when we made decision X?" is unanswerable |
| No relevance feedback | Injected knowledge is fire-and-forget; no learning from usage |
| No cross-entity knowledge aggregation | "What patterns apply to features with >3 review rounds?" requires manual grep |
| No agent run tracking | Which agent produced which knowledge? No provenance chain |

---

## 5. RAG-Specific Concerns

**Chunking strategy is wrong for code.**
Memory entries are freeform text. For code-agent RAG, you need semantically meaningful chunks: functions, classes, API contracts, test patterns, error-fix pairs.

**No retrieval-augmented *generation* loop.**
Current system retrieves at session start only. A real RAG system should:
1. Retrieve relevant context *during* agent work (not just at start)
2. Re-rank based on the *current task* (not just the active feature)
3. Provide provenance ("this pattern was learned from feature X, observed 5 times")
4. Allow the agent to *query* for specific knowledge mid-task

**Embedding provider lock-in risk.**
Switching providers requires re-embedding everything. Consider storing multiple embedding versions or using a provider-agnostic similarity layer.

**No retrieval evaluation.**
No way to measure retrieval quality. No labeled relevance judgments, no A/B testing, no precision/recall metrics. Weights (vector=0.5, keyword=0.2, prominence=0.3) are tuned by intuition.

---

## 6. Recommended Expansion Roadmap

### Phase 1: Unify the Data Model
- Merge entity DB and memory DB into a single graph database (or add a relationships table bridging them)
- Replace fixed entity types with flexible `node_type` + `node_type_schema` pattern
- Add a proper `edges` table: `(source_type_id, target_type_id, relationship_type, metadata, created_at)`
- Relationship types: `originated_from`, `depends_on`, `learned_during`, `applies_to`, `contradicts`, `supersedes`

### Phase 2: Close the Feedback Loop
- Track which injected entries the agent actually *used* (referenced in output, influenced decisions)
- Add a `helpfulness_score` that decays when entries are injected but not referenced
- Make retrieval *on-demand during work*, not just at session start

### Phase 3: Richer Knowledge Representation
- Structured entry types: `pattern`, `anti-pattern`, `decision`, `error-fix-pair`, `api-contract`, `code-convention`
- Each type has its own schema (conditions, exceptions, examples, counter-examples)
- Support conditional knowledge: "Use pattern X *when* condition Y holds"

### Phase 4: Agent-Aware RAG
- Track agent runs as entities: which agent, what task, what knowledge was accessed, what was produced
- Build a provenance chain: backlog -> brainstorm -> feature -> agent_run -> knowledge_entry
- Enable queries like: "Show me all patterns discovered by the implementation-reviewer agent"

### Phase 5: Evaluation and Tuning
- Build a retrieval evaluation harness: labeled queries + expected relevant entries
- A/B test different weight configurations
- Track retrieval latency (currently unmeasured; important for session-start UX)

---

## 7. The Single Most Impactful Change

**Add a relationships/edges table that connects entities to knowledge entries**, turning two trees into one graph. Everything else builds on that foundation.

```sql
CREATE TABLE edges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id     TEXT NOT NULL,       -- type_id from entities OR entry id from memory
    target_id     TEXT NOT NULL,       -- type_id from entities OR entry id from memory
    relationship  TEXT NOT NULL,       -- originated_from, depends_on, learned_during, applies_to, etc.
    metadata      TEXT,                -- JSON for edge properties
    created_at    TEXT NOT NULL,
    UNIQUE(source_id, target_id, relationship)
);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_relationship ON edges(relationship);
```

This single addition would enable:
- "What did we learn from feature 029?" -> follow `learned_during` edges
- "What features does this pattern apply to?" -> follow `applies_to` edges
- "What's the full provenance of this decision?" -> traverse edge chain
- "What knowledge contradicts this anti-pattern?" -> follow `contradicts` edges

---

## Current System Stats

| Component | Lines of Code | Tests | Quality | Status |
|-----------|:---:|:---:|:---:|:---:|
| Entity Database | 562 | 184 tests | High | Stable |
| Entity Backfill | ~300 | Covered | High | Stable |
| Entity Server Helpers | ~400 | Covered | High | Stable |
| Memory Database | 609 | ~1,000 | High | Stable |
| Memory Retrieval | 407 | ~850 | High | Stable |
| Memory Ranking | 273 | ~570 | High | Stable |
| Memory Embedding | 689 | ~800 | High | Stable |
| Memory Writer | 298 | ~525 | High | Stable |
| Memory Injector | 254 | ~480 | Medium | Stable |
| Memory Keywords | 149 | ~320 | Low | Incomplete |
| Legacy memory.py | 296 | None | Medium | Deprecated |
| **Totals** | **~4,200** | **~5,000+** | **High** | **Production** |
