#!/usr/bin/env bash
# PostToolUse hook: inject plan review instructions after EnterPlanMode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_ROOT="$(detect_project_root)"

# Guard: check config
config_file="${PROJECT_ROOT}/.claude/iflow-dev.local.md"
enabled=$(read_local_md_field "$config_file" "plan_mode_review" "true")
if [[ "$enabled" != "true" ]]; then
    echo '{}'; exit 0
fi

# Guard: skip if active iflow feature exists (standard /create-plan handles review)
has_active=$(python3 -c "
import os, json, glob
features = glob.glob(os.path.join('$PROJECT_ROOT', 'docs/features/*/.meta.json'))
for f in features:
    try:
        with open(f) as fh:
            if json.load(fh).get('status') == 'active':
                print('yes')
                raise SystemExit
    except SystemExit:
        raise
    except:
        pass
print('no')
" 2>/dev/null) || has_active="no"

if [[ "$has_active" == "yes" ]]; then
    echo '{}'; exit 0
fi

# Inject review instructions
context="## Plan Mode: Review Before Approval\n\n"
context+="After writing your plan but BEFORE calling ExitPlanMode, you MUST run plan review:\n\n"
context+="1. Read the full plan file content you just wrote\n"
context+="2. Dispatch the plan-reviewer agent:\n"
context+="   \`\`\`\n"
context+="   Task tool:\n"
context+="     subagent_type: iflow-dev:plan-reviewer\n"
context+="     prompt: |\n"
context+="       Review this plan for failure modes, untested assumptions,\n"
context+="       dependency accuracy, and feasibility.\n"
context+="       ## Plan\n"
context+="       {paste full plan file content here}\n"
context+="       Return JSON: {\"approved\": bool, \"issues\": [...], \"summary\": \"...\"}\n"
context+="   \`\`\`\n"
context+="3. If reviewer returns blocker issues: edit the plan file to address them, then re-review (max 3 iterations)\n"
context+="4. Once approved (or max iterations reached): call ExitPlanMode\n"

escaped=$(escape_json "$context")
cat <<EOF
{
  "hookSpecificOutput": {
    "additionalContext": "${escaped}"
  }
}
EOF
