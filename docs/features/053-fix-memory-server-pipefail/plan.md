# Plan: Fix memory-server MCP pipefail crash

## Overview

3 changes across 2 files. No dependencies between changes. All can be implemented in a single step.

## Steps

### Step 1: Fix shell pipefail crashes (R1, R2) and add provider error logging (R3)

**Files:**
- `plugins/pd/mcp/run-memory-server.sh` — lines 22, 34
- `plugins/pd/hooks/lib/semantic_memory/embedding.py` — imports + line 711

**Changes:**

1. **run-memory-server.sh line 22:** Append `|| true` to the `.env` key grep pipeline
   ```bash
   # Before
   _val=$(grep -E "^${_key}=" .env 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^["'"'"']//;s/["'"'"']$//')
   # After
   _val=$(grep -E "^${_key}=" .env 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^["'"'"']//;s/["'"'"']$//' || true)
   ```

2. **run-memory-server.sh line 34:** Append `|| true` to the `pd.local.md` provider grep pipeline
   ```bash
   # Before
   _PROVIDER=$(grep -E "^memory_embedding_provider:" .claude/pd.local.md 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | tr -d '[:space:]')
   # After
   _PROVIDER=$(grep -E "^memory_embedding_provider:" .claude/pd.local.md 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | tr -d '[:space:]' || true)
   ```

3. **embedding.py:** Add `import sys` at top (alongside existing `import os`), then replace silent exception handler:
   ```python
   # Before
   except Exception:
       return None
   # After
   except Exception as exc:
       print(f"memory-server: create_provider failed for {provider_name}: {exc}", file=sys.stderr)
       return None
   ```

**Test:** Run from project root:
```bash
# Smoke test — should reach exec without dying
bash -x plugins/pd/mcp/run-memory-server.sh < /dev/null 2>&1 | tail -5

# Automated regression
plugins/pd/.venv/bin/python -m pytest plugins/pd/mcp/test_memory_server.py -v
plugins/pd/.venv/bin/python -m pytest plugins/pd/hooks/lib/semantic_memory/ -v -k embedding
bash plugins/pd/mcp/test_run_memory_server.sh
```

**Depends on:** Nothing
**Risk:** Very low — surgical append of `|| true` and a print statement

## Dependency Graph

```
Step 1 (all changes) → Done
```

No dependencies. Single atomic step.
