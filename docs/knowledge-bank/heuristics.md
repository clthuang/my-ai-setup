# Heuristics

Decision guides for common situations. Updated through retrospectives.

---

## Decision Heuristics

### Reference File Sizing
Target ~100-160 lines per reference file for balance between completeness and readability.
- 4 files at ~480 total lines is a good ratio for a thin orchestrator pattern
- Benefit: Each file is independently readable without scrolling fatigue
- Source: Feature #018
- Last observed: Feature #018
- Observation count: 1

### Line Budget Management
Target 90-95% of SKILL.md budget (450-475 of 500 lines).
- Landing at 96% (482/500) is acceptable but leaves minimal room for future additions
- If approaching 98%+, consider extracting content to reference files
- Source: Feature #018
- Last observed: Feature #018
- Observation count: 1

### AskUserQuestion Option Count
Keep AskUserQuestion to 6 explicit options maximum (7 with built-in "Other").
- The system automatically provides "Other" for free text — no need to waste an option slot
- 7 total choices is the upper limit for usability
- Source: Feature #018
- Last observed: Feature #018
- Observation count: 1

### Cross-Skill Coupling Depth
Keep cross-skill dependencies to read-only access of reference files only.
- Never have one skill Write to another skill's directory
- One fallback level (hardcoded content) is sufficient for graceful degradation
- Two levels of fallback adds complexity without proportional reliability gain
- Source: Feature #018
- Last observed: Feature #018
- Observation count: 1

### Graph-Text Consistency as First-Pass Check
When reviewing plans with dependency graphs, validate graph-text consistency before deeper review.
- 4 of 6 plan iterations in Feature #021 were caused by graph-text mismatches
- Check: Every dependency mentioned in text appears as an edge in the graph, and vice versa
- Source: Feature #021
- Last observed: Feature #021
- Observation count: 1

### Read Target Files During Task Creation
When creating tasks for file modifications, read the target file first and include exact line numbers.
- Tasks without this specificity (7.1, 7.2, 7.3) were the ones blocked in task review
- Investment in precision during task creation pays off with lower implementation iteration count
- Source: Feature #021
- Last observed: Feature #021
- Observation count: 1

### Reviewer Iteration Count as Complexity Signal
Reviewer iteration counts suggest complexity: 2 = straightforward, 3 = moderate, 4+ = initially underspecified.
- Feature #021 plan had 6 iterations (highest), mostly from dependency graph contradictions
- If plan iterations exceed 3, check for structural issues (dual representations, missing test cases)
- Source: Feature #021
- Last observed: Feature #021
- Observation count: 1

<!-- Example format:
### When to Create a New Service
Create a new service when:
- Functionality is used by 3+ other components
- Has distinct lifecycle from parent
- Needs independent scaling

Otherwise: Keep it as a module within existing service.
-->
