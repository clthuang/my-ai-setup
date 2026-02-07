# Heuristics

Decision guides for common situations. Updated through retrospectives.

---

## Decision Heuristics

### Reference File Sizing
Target ~100-160 lines per reference file for balance between completeness and readability.
- 4 files at ~480 total lines is a good ratio for a thin orchestrator pattern
- Benefit: Each file is independently readable without scrolling fatigue
- Source: Feature #018

### Line Budget Management
Target 90-95% of SKILL.md budget (450-475 of 500 lines).
- Landing at 96% (482/500) is acceptable but leaves minimal room for future additions
- If approaching 98%+, consider extracting content to reference files
- Source: Feature #018

### AskUserQuestion Option Count
Keep AskUserQuestion to 6 explicit options maximum (7 with built-in "Other").
- The system automatically provides "Other" for free text — no need to waste an option slot
- 7 total choices is the upper limit for usability
- Source: Feature #018

### Cross-Skill Coupling Depth
Keep cross-skill dependencies to read-only access of reference files only.
- Never have one skill Write to another skill's directory
- One fallback level (hardcoded content) is sufficient for graceful degradation
- Two levels of fallback adds complexity without proportional reliability gain
- Source: Feature #018

<!-- Example format:
### When to Create a New Service
Create a new service when:
- Functionality is used by 3+ other components
- Has distinct lifecycle from parent
- Needs independent scaling

Otherwise: Keep it as a module within existing service.
-->
