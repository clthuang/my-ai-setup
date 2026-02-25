---
description: Add an item to the backlog for capturing ad-hoc ideas, todos, or fixes.
argument-hint: <description>
---

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

Add an item to the centralized backlog at `{iflow_artifacts_root}/backlog.md`.

## Instructions

1. **Validate input:** If no description was provided in the arguments, output:
   ```
   Usage: /iflow-dev:add-to-backlog <description>
   ```
   Then stop.

2. **Ensure directory exists:** `mkdir -p {iflow_artifacts_root}/`

3. **Read or initialize backlog:**
   - Try to read `{iflow_artifacts_root}/backlog.md`
   - If file exists: Parse the table to find the highest existing ID (5-digit numbers like `00001`)
   - If file doesn't exist or has no entries: The next ID will be `00001`

4. **Generate the new entry:**
   - ID: Next sequential 5-digit ID (e.g., `00001`, `00002`), zero-padded
   - Timestamp: Current time in ISO 8601 format (e.g., `2026-01-30T14:23:00Z`)
   - Description: The user's input (escape pipe characters `|` as `\|` if present)

5. **Write to backlog:**
   - If file doesn't exist, create it with this header:
     ```markdown
     # Backlog

     | ID | Timestamp | Description |
     |----|-----------|-------------|
     ```
   - Append the new row: `| {ID} | {Timestamp} | {Description} |`

6. **Confirm to user:**
   ```
   Added to backlog: #{ID} - {Description}
   ```

## Example

User runs: `/iflow-dev:add-to-backlog Fix the login timeout bug`

Output:
```
Added to backlog: #00001 - Fix the login timeout bug
```

And `{iflow_artifacts_root}/backlog.md` now contains:
```markdown
# Backlog

| ID | Timestamp | Description |
|----|-----------|-------------|
| 00001 | 2026-01-30T14:23:00Z | Fix the login timeout bug |
```
