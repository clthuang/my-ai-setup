---
name: researching
description: Dispatch contract for research subagents — one narrow question each, pointers back, no context pollution. Use when gathering evidence before a decision.
---

# Researching

Research runs in subagents so their reading never lands in the orchestrator's context. That property is the point; protect it.

**One question per dispatch.** "Research auth" is not a question; "which modules read the session cookie, and where is it written?" is. Name where to look.

**Dispatch in parallel, one message.** `pd:codebase-explorer` for what exists here, `pd:internet-researcher` for external prior art, `pd:skill-searcher` for installed capabilities — every call in the same message so they run concurrently.

**Return pointers, not payloads.** A finding is one claim plus its source (`file:line` or URL) and a relevance rating. Agents never paste file contents or search dumps back; the orchestrator opens the few files the pointers justify.

**Absence is a result.** An agent finding nothing says so, and says where it looked. Use that answer — do not re-dispatch it.

**Failure is a warning.** One agent down: proceed on what returned and state the gap. All down: stop and say research did not run. Never backfill a gap with unattributed assertions.
