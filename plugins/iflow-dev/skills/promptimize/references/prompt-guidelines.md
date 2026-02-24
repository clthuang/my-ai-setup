# Prompt Engineering Guidelines

## Last Updated: 2026-02-24

## Core Principles
1. **Be explicit, not implicit** — State requirements directly [Anthropic Claude 4.x guide]
2. **Provide context and rationale** — Explain WHY, not just WHAT [The Prompt Report]
3. **Use XML tags for structure** — Separates instructions from context [Anthropic docs]
4. **Decompose complex tasks** — Break into steps with semantic labels [The Prompt Report]
5. **Few-shot Chain-of-Thought** — Include reasoning examples [The Prompt Report]
6. **Positive framing** — "Do X" not "Don't do Y" [Anthropic Claude 4.x]
7. **Calibrated emphasis** — Normal-intensity language; avoid ALL-CAPS/excessive MUST [Anthropic Claude 4.x]
8. **Provide additional context** — "Massively underrated" technique [The Prompt Report]
9. **Quality examples** — Quantity, order, and format matter; small tweaks yield up to 90% accuracy improvement [The Prompt Report]
10. **Instruction placement** — Place key instructions at top AND bottom for agentic tasks [OpenAI GPT-4.1 Guide]

## Plugin-Specific Patterns

### Skills
- **Structure:** Frontmatter → YOLO overrides → Process (numbered steps with bold semantic labels) → Output format → Error handling → Self-check → PROHIBITED section [Codebase analysis]
- **Token budget:** <500 lines, <5000 tokens. Use reference files for overflow. [component-authoring.md]
- **Progressive disclosure:** SKILL.md = overview/routing, references/ = detailed content loaded on demand [anthropic-best-practices.md]
- **Description:** Gerund name, third person, includes trigger conditions and key terms [component-authoring.md]
- **Conditional logic:** Use response-action tables for conditionals, quality-gate loops for review stages [Codebase analysis]

### Agents
- **Structure:** Frontmatter (name/description/model/tools/color) → Two `<example>` blocks → Single-question focus → Input → Output format (JSON schema) → Process → MUST NOT section [Codebase analysis]
- **Tool scoping:** Explicitly list allowed tools; read-only agents get [Read, Glob, Grep] only [component-authoring.md]
- **Output severity:** Universal blocker/warning/suggestion with "Blocks Approval?" column [Codebase analysis]
- **Description:** Action/role noun form, includes delegation triggers [component-authoring.md]

### Commands
- **Structure:** Frontmatter (description + argument-hint) → Conditional routing → Delegation to skills/agents → Completion [Codebase analysis]
- **Argument handling:** Use $ARGUMENTS for direct input, AskUserQuestion for interactive selection when no args [Codebase analysis]
- **Delegation pattern:** Task tool for agent dispatch, Skill tool for skill invocation [Codebase analysis]

## Persuasion Techniques
- **Authority:** Use "the system" or established norms, not "I think" [persuasion-principles.md]
- **Commitment & Consistency:** Reference prior agreements ("As established in the spec...") [persuasion-principles.md]
- **Loss Aversion:** Frame omissions as risks ("Skipping this step risks...") [persuasion-principles.md]
- **Unity/Identity:** Invoke shared standards ("We follow TDD in this codebase") [persuasion-principles.md]

## Techniques by Evidence Tier

### Strong Evidence
- Few-shot Chain-of-Thought — Highest-performing across benchmarks [The Prompt Report]
- Task decomposition — Strong across all models [The Prompt Report]
- Self-criticism / reflection — Strong for iterative tasks [The Prompt Report]
- Additional context — "Massively underrated" [The Prompt Report]
- Example quality tuning — Up to 90% accuracy improvement from small tweaks [The Prompt Report]

### Moderate Evidence
- XML tags for structure (Claude-specific) — Recommended in official docs [Anthropic guide]
- Instruction placement top AND bottom — ~4% benchmark improvement for agentic tasks [OpenAI GPT-4.1 Guide]
- Positive framing over negation — Preferred in Claude 4.x [Anthropic Claude 4.x guide]

### Emerging / Experimental
- Context engineering framing — Endorsed by Karpathy, Willison, Gartner [Multiple practitioners 2025]
- Degrees-of-freedom matching — Prompt constraints should match task flexibility [anthropic-best-practices.md]

## Anti-Patterns
- **Role prompting for correctness** — Affects tone only, not accuracy [The Prompt Report]
- **Self-consistency** — Underperforms despite popularity [The Prompt Report]
- **Emphasis overuse** — ALL-CAPS, excessive MUST/CRITICAL causes overtriggering in Claude 4.x [Anthropic docs]
- **Anti-laziness language** — "Be thorough", "Don't be lazy" causes overthinking in newer models [Anthropic Claude 4.x guide]
- **All content in one file** — Violates progressive disclosure principle [anthropic-best-practices.md]
- **Weak constraint language** — "Should", "try to", "consider" instead of definitive "MUST", "NEVER" for hard constraints [Codebase analysis]

## Update Log
| Date | Changes | Sources |
|------|---------|---------|
| 2026-02-24 | Initial seed from PRD research + codebase analysis + component-authoring.md + anthropic-best-practices.md + persuasion-principles.md | The Prompt Report, Anthropic docs, OpenAI GPT-4.1 Guide, codebase patterns |
