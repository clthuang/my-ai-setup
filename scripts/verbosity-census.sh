#!/usr/bin/env bash
# verbosity-census.sh — pinned regression baseline for the workflow-rebuild track.
# Source of truth for the PRD's word-count, schema-restatement, and dispatch metrics
# (docs/brainstorms/20260710-153500-workflow-rebuild.prd.md rev 2: Success Criteria + FR-9).
#
# Scope: ALL *.md under plugins/pd/commands/ and plugins/pd/skills/ (references included).
# Test files: none exist under either tree at authoring time; if any appear they are IN
# scope until this comment is amended — the metric is prose the orchestrator loads, and
# anything .md in these trees gets loaded.
#
# One pinned pattern per metric. Output is TSV (metric<TAB>count), stable order, exit 0.
# These numbers supersede the PRD's 2026-07-10 session-sweep approximations.
set -euo pipefail
cd "$(dirname "$0")/.."
CMD=plugins/pd/commands
SKL=plugins/pd/skills

# Orchestration scope (PRD SC ≤5,000-word target denominator, pinned 2026-07-25).
# Domain-knowledge packs are PRD Non-Goals ("knowledge, not orchestration") and are
# excluded here; scope_words_total keeps counting everything for continuity.
DOMAIN_SKILLS="game-design crypto-analysis data-science-analysis choosing-ds-modeling-approach spotting-ds-analysis-pitfalls structuring-ds-projects writing-ds-python implementing-with-tdd systematic-debugging root-cause-analysis structured-problem-solving promptimize writing-skills creating-specialist-teams"
DOMAIN_COMMANDS="init-ds-project review-ds-analysis review-ds-code promptimize refresh-prompt-guidelines create-specialist-team"
# Advisor personas are ideation-lens KNOWLEDGE loaded one-at-a-time by the
# advisor agent (several are domain-pack lenses: DS/game/crypto) — same
# knowledge-not-orchestration class as DOMAIN_SKILLS.
ADVISOR_REFS="plugins/pd/skills/brainstorming/references/advisors"

words() { cat $(find "$@" -name '*.md' | sort) | wc -w | tr -d ' '; }
occurrences() { local pat=$1; shift; grep -rE --include='*.md' -o "$pat" "$@" 2>/dev/null | wc -l | tr -d ' '; }
orch_words() {
  local skl_prune=() cmd_prune=()
  for d in $DOMAIN_SKILLS;   do skl_prune+=(-not -path "$SKL/$d/*"); done
  skl_prune+=(-not -path "$ADVISOR_REFS/*")
  for c in $DOMAIN_COMMANDS; do cmd_prune+=(-not -name "$c.md"); done
  cat $(find "$CMD" -name '*.md' "${cmd_prune[@]}"; find "$SKL" -name '*.md' "${skl_prune[@]}") | wc -w | tr -d ' '
}

printf 'scope_words_commands\t%s\n'          "$(words "$CMD")"
printf 'scope_words_skills\t%s\n'            "$(words "$SKL")"
printf 'scope_words_total\t%s\n'             "$(words "$CMD" "$SKL")"
printf 'scope_words_orchestration\t%s\n'     "$(orch_words)"
printf 'resume_state\t%s\n'                  "$(occurrences 'resume_state' "$CMD" "$SKL")"
printf 'delta_size_guards\t%s\n'             "$(occurrences 'delta_content|delta_stat|delta[- ]size' "$CMD" "$SKL")"
printf 'compaction_detection\t%s\n'          "$(occurrences '[Cc]ompaction' "$CMD" "$SKL")"
printf 'files_read_ritual\t%s\n'             "$(occurrences 'Files read:' "$CMD" "$SKL")"
printf 'lazy_load_warnings\t%s\n'            "$(occurrences 'LAZY-LOAD' "$CMD" "$SKL")"
printf 'schema_restatements_commands\t%s\n'  "$(occurrences '"approved"' "$CMD")"
printf 'schema_restatements_skills\t%s\n'    "$(occurrences '"approved"' "$SKL")"
printf 'yolo_block_headers\t%s\n'            "$(occurrences '^#{2,4} .*YOLO' "$CMD" "$SKL")"
printf 'yolo_mentions\t%s\n'                 "$(occurrences 'YOLO' "$CMD" "$SKL")"
printf 'dispatch_sites_commands\t%s\n'       "$(occurrences 'subagent_type' "$CMD")"
printf 'dispatch_sites_reviewer_commands\t%s\n' "$(occurrences 'subagent_type[^\n]*[Rr]eview' "$CMD")"
