---
name: specifying
description: Quality criteria for a feature's Requirements section. Use when writing or reviewing `## Requirements` in a feature's shape document.
---

# Specifying

`## Requirements` lives in `{pd_artifacts_root}/features/{id}-{slug}/shape.md` and carries four things.

**Success criteria — mechanically checkable.** Each names the command, grep, or assertion that decides pass/fail plus the observable result. "Login works" is not a criterion; "`pytest tests/test_auth.py::test_expired_token` exits 0" is. A criterion resting on stdlib or library runtime behavior carries the verifying REPL line inline (`>>> expr → result`).

**Scope boundaries — both sides.** What gets built, and the out-of-scope items a reader would otherwise assume are included. YAGNI applies to both lists.

**Edge cases — named, not gestured at.** Invalid input, absent or empty state, concurrent access, and the failure mode of each external dependency, each with its expected behavior. Complex branching goes in a truth table instead of a linear list.

**Behavioral constraints — what the feature must NOT do**, each with the harm it avoids.

Requirements state what, never how: anything verifiable only by reading a diff belongs in `## Design`. Where the requirement names test symbols or existing test classes, say whether the scope is production behavior or test-only hardening.
