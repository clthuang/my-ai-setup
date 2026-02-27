# Backlog

| ID | Timestamp | Description |
|----|-----------|-------------|
| 00008 | 2026-01-31T12:05:00Z | add product manager, product owner team (agents, skills) |
| 00012 | 2026-02-17T12:00:00Z | fix the secretary AskUserQuestion formatting. The user should be able to select the options directly and also continue to chat if desired. |
| 00014 | 2026-02-24T12:01:00Z | Security Scanning — static rule-based security scanning alongside the agent-based security-reviewer (inspired by ECC's AgentShield with 102 rules). See ecc-comparison-improvements.md Item 10. |
| 00015 | 2026-02-24T12:02:00Z | Cross-Platform Hooks — port Bash hooks to Node.js for Windows compatibility. See ecc-comparison-improvements.md Item 11. |
| 00016 | 2026-02-24T12:03:00Z | Multi-Model Orchestration — route to multiple AI providers (Codex, Gemini) alongside Claude for cost optimization or specialized tasks. See ecc-comparison-improvements.md Item 12. |
| 00017 | 2026-02-27T12:00:00Z | Unified Central Context Management — expand the knowledge bank DB into a unified central context management service. All agents retrieve required context from the DB. The main orchestration agent sends background context as DB indices to subagents rather than full text. |
| 00018 | 2026-02-27T12:01:00Z | Knowledge Bank Auto-Logging — upgrade knowledge bank to automatically and asynchronously log all session conversations via subagents. Capture every prompt and response, index after each turn. Rethink DB schema to include enriched metadata: session_id, raw prompt/response, categories, timestamps, and other appropriate fields. |
| 00020 | 2026-02-27T13:53:55Z | Consider renaming the plugin/repository to `pedantic-drips` for the public MIT open-source release to highlight the adversarial reviewing nature of the workflow. |
