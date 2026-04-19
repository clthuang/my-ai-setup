# Patterns

Shared KB patterns file used as the snapshot fixture for feature 085
hardening tests. Entries are deliberately clean: no HTML comment
markers (opening or closing) and no triple-backtick fences in either
entry_name or description. This avoids FR-1 rejection while still
exercising the unchanged happy-path markdown rendering.

### Always pass absolute paths to tools

Always use absolute paths for Read, Edit, Glob, and Bash tool calls.
Relative paths break when the working directory changes mid-session.

- Used in: Feature #001, Feature #002, Feature #003
- Confidence: high

### Close SQLite connections in a context manager

Wrap MemoryDatabase usage in a context manager so connections are
closed even on exceptions. Leaked handles cause WAL checkpoint drift.

- Used in: Feature #004, Feature #005, Feature #006
- Confidence: high

### Verify test failures before fixing

When a test fails, read the error before editing. Guessing at fixes
wastes iterations and masks the real defect.

- Used in: Feature #007, Feature #008, Feature #009
- Confidence: high
