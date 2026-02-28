# Token Efficiency & Inter-Agent Context Passing in `iflow`

## 1. Current Implementation Analysis

Based on a review of the `iflow` plugin mechanisms (specifically looking at `/iflow:implement` and `/iflow:create-plan`), the current method for passing context between agents is **Full Artifact Injection**.

When a downstream agent (such as `plan-reviewer` or `security-reviewer`) is invoked, the orchestrator injects the **entire contents** of all upstream artifacts directly into the prompt template.

**Example from `/iflow:implement` (Security Reviewer Dispatch):**
```text
Validate implementation against full requirements chain...
## PRD (original requirements)
{content of prd.md}
## Spec (acceptance criteria)
{content of spec.md}
## Design (architecture to follow)
{content of design.md}
## Plan (implementation plan)
{content of plan.md}
## Tasks (what should be done)
{content of tasks.md}
## Implementation files
{list of files with code}
```

### Token Efficiency Impact

This approach has a severe compounding effect on token usage:
*   **O(N) Token Growth per Phase:** As a feature progresses from PRD → Spec → Design → Plan → Implementation, the context window grows linearly or worse.
*   **Massive Redundancy:** In the 5-iteration Review Loop of the implementation phase, the orchestrator sends the exact same 5 upstream markdown files to 3 different agents (Implementation Reviewer, Quality Reviewer, Security Reviewer), potentially multiple times if issues are found. 
*   **Cost & Latency:** For large features, injecting 5 highly detailed markdown files + source code into *every single agent dispatch* wastes input tokens, increases API latency, and risks blowing out the context window limits of smaller/cheaper models (like Sonnet or Haiku).

---

## 2. Best Practices & Alternative Patterns

To improve token efficiency, the architecture should move away from "Full Artifact Injection" toward more efficient state-sharing patterns common in anthropic/openai multi-agent architectures.

### Pattern A: Shared Context via System Prompts & File References
Instead of passing the *contents* of files within the user prompt message, modern agents should be granted access to the file system (or a virtual file system) and provided only the *references* (paths). If the LLM environment supports a persistent context or cache (like Anthropic's Prompt Caching), the static upstream documents should be loaded once at the system level.

### Pattern B: LLM-Generated Summarization (The Telephone Game)
Instead of passing the full PRD, Spec, and Design to the Implementation Reviewer, an intermediate agent summarizes the constraints of the upstream documents into a dense, abbreviated "Implementation Constraints" ledger. (Note: `iflow` avoids this to explicitly prevent "translation loss", prioritizing accuracy over tokens).

### Pattern C: Semantic Search / RAG
If the PRD and Design are massive, the agent only receives snippets relevant to the specific file it is reviewing, fetched via embedding similarity.

---

## 3. Proposal for Improving `iflow` Token Efficiency

Given `iflow`'s strict requirement for high accuracy (hence the adversarial review loops), we cannot use lossy summarization (Pattern B). Instead, we should implement a combination of **Prompt Caching** and **Targeted Handoffs**.

### Recommendation 1: Implement Prompt Caching for Static Artifacts
*(Highest Impact, Lowest Effort if using Anthropic API)*

In the implementation review loop, the `prd.md`, `spec.md`, `design.md`, `plan.md`, and `tasks.md` are **static**. Only the implementation code and review history change between iterations.
*   **Implementation:** Bundle the static documents into a single chunk at the very beginning of the prompt and flag them for API-level Prompt Caching (`ephemeral` cache blocks in Claude).
*   **Result:** You pay for the large input tokens once at the start of the 5-iteration loop. Subsequent review iterations by the 3 agents will hit the cache, reducing input token costs by up to 90% per loop and dramatically speeding up the generation of the review.

### Recommendation 2: Role-Specific Context Pruning
Currently, the `code-quality-reviewer` receives the *entire* PRD and Spec. However, assessing SOLID principles, readability, and KISS likely only requires the `design.md` (for architecture rules) and the code files themselves.
*   **Implementation:** Refactor the prompt templates so that agents only receive the artifacts strictly necessary for their specific rubric.
    *   `implementation-reviewer` → Gets all artifacts (Needs to verify full chain)
    *   `security-reviewer` → Gets `design.md` (for threat model/auth) and code files. Drops `plan.md` and `tasks.md`.
    *   `code-quality-reviewer` → Gets `design.md` and code files. Drops `prd.md`, `spec.md`.
*   **Result:** Cuts token usage for the secondary reviewers by 40-60%.

### Recommendation 3: Diffs over Full Files in Fix Loops
When the `implementer` agent is dispatched to fix issues found in iteration 1, it is currently fed the entire codebase again.
*   **Implementation:** If an agent is dispatched to fix a specific bug raised by a reviewer, only pass the explicit file chunk (or Git Diff) containing the problem, rather than the entire `{list of files with code}`.
*   **Result:** Drastically reduces token payload during repetitive micro-fix loops.

### Recommendation 4: Leverage the MCP Memory Server for Context
`iflow` already has an MCP memory server (`store_memory` / `search_memory`). 
*   **Implementation:** Instead of passing the full PRD text into the Plan Reviewer, the PRD could be indexed into the memory server. The agent is given a tool to query specific requirements from the PRD if/when it needs clarification, rather than front-loading the tokens.

### Recommendation 5: Agent Instance Reuse (Threaded State)
Currently, `iflow` instantiates a brand new agent for every single iteration of the review loop (i.e., replacing the entire context window).
*   **Implementation:** Instead of "passing" artifacts to a new agent 5 times, instantiate a single `Review Agent` loop that maintains conversational history. When the `implementer` finishes fixing bugs in Iteration 1, simply append the diff to the *existing* review agent's thread. 
*   **Pros:** This completely solves the O(N) redundant artifact injection problem. The static documents (PRD, Spec) remain in the conversation history, and the agent only processes the tiny delta of the new user prompt (the diff) in subsequent turns.
*   **Cons:** Over 5 iterations, the conversational context window grows very long. The agent may become distracted by old review comments from Iteration 1 when reviewing Iteration 4 code. Explicitly managing the lifecycle of these 28 separate agents might also require significant structural rewrites of the `ClaudeCommand` orchestration layer.
