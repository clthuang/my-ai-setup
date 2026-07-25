#!/usr/bin/env bash
# phase-gate.sh — FR-4 tier-1 mechanical phase-boundary gate (workflow-rebuild).
# Zero-dispatch checks: artifact existence, required sections, duplicate
# contract blocks (#074 restatement class). LLM review moments are NOT here.
#
# Usage: phase-gate.sh <phase> <feature-dir>
#   phase ∈ specify|design|create-plan|implement|finish
# Exit 0 = gate passes; nonzero prints each failure on its own line.
set -uo pipefail

PHASE="${1:-}"
DIR="${2:-}"
FAIL=0
say() { echo "GATE FAIL [$PHASE]: $1"; FAIL=1; }

[ -n "$PHASE" ] && [ -n "$DIR" ] || { echo "usage: phase-gate.sh <phase> <feature-dir>"; exit 2; }
[ -d "$DIR" ] || { say "feature dir missing: $DIR"; echo "1 failure"; exit 1; }

need_file() { [ -f "$DIR/$1" ] || say "missing artifact: $1"; }
need_section() { [ -f "$DIR/$1" ] && grep -q "^## $2" "$DIR/$1" || say "$1 missing section: ## $2"; }

# Duplicate fenced code blocks across the artifact set = restated contract (#074).
# Blocks under 3 lines are ignored (single-line snippets legitimately repeat).
dupe_contract_blocks() {
  # Pure awk (BSD-portable: macOS uniq lacks -z). Prints DUPE on first repeat.
  find "$DIR" -maxdepth 1 -name '*.md' -print0 | xargs -0 cat 2>/dev/null |
    awk '
      /^```/ {
        if (inblk) { if (n > 3 && ++seen[blk] == 2) { print "DUPE"; exit } inblk = 0 }
        else { inblk = 1; blk = ""; n = 0 }
        next
      }
      inblk { blk = blk "\n" $0; n++ }
    '
}

case "$PHASE" in
  specify)
    need_file shape.md
    need_section shape.md Requirements
    ;;
  design)
    need_file shape.md
    need_section shape.md Requirements
    need_section shape.md Design
    [ -n "$(dupe_contract_blocks)" ] && say "duplicate contract block in artifact set (pin each contract once)"
    ;;
  create-plan)
    need_file shape.md
    need_file plan.md
    need_section plan.md Plan
    [ -n "$(dupe_contract_blocks)" ] && say "duplicate contract block in artifact set (pin each contract once)"
    ;;
  implement)
    need_file shape.md
    need_file plan.md
    # Uncommitted artifact edits at implement-entry mean the prior phase exit skipped its commit.
    if command -v git >/dev/null && git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1; then
      DIRTY=$(git -C "$DIR" status --porcelain -- . 2>/dev/null | grep -c '\.md$' || true)
      [ "${DIRTY:-0}" -gt 0 ] && say "uncommitted artifact files at implement entry ($DIRTY)"
    fi
    ;;
  finish)
    need_file retro.md
    ;;
  *)
    echo "usage: phase-gate.sh <phase> <feature-dir> (unknown phase: $PHASE)"; exit 2
    ;;
esac

if [ "$FAIL" -ne 0 ]; then exit 1; fi
echo "GATE PASS [$PHASE] $DIR"
