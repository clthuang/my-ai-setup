"""Apply orchestrator — 5-stage atomic write per FR-5.

Stages implemented here (1-4):

  Stage 1 — Pre-flight validation (no writes):
    * modify targets must exist; create targets must NOT exist.
    * `hooks.json` targets: the patched `after` must parse as JSON.
    * TD-8 collision scan: any existing `.sh` in the hook's directory or any
      sibling markdown file in the edited dirs that already carries a
      `Promoted ... {entry.name}` marker aborts the run.

  Stage 2 — Snapshot + baseline validate.sh (per FR-5 Stage 4 / TD-5):
    * For every modify edit, read and record current bytes keyed by path.
    * Record the list of create-edits (rollback: unlink).
    * Run `./validate.sh` and record (error_count, error_categories_set) as
      the baseline BEFORE any Stage 3 write. If the baseline run itself fails
      (non-zero exit), abort with NO writes and stage_completed="baseline".

  Stage 3 — Write:
    * Apply each FileEdit in ascending `write_order`, breaking ties by path.
    * Any exception during write -> rollback every edit applied so far.

  Stage 4 — Post-write validation:
    * Every FileEdit's path must exist after write.
    * hooks.json targets must re-parse as JSON.
    * If target_type == "hook": execute the test script (write_order=1) with
      `subprocess.run(..., timeout=<env|30>, capture_output=True)`.
      Non-zero exit OR timeout -> rollback.
    * Baseline-delta validate.sh: re-run and rollback ONLY if
      post_count > baseline_count OR any new error category appears.

Stage 5 (KB marker) is delegated to the `mark` CLI subcommand; see design C-7.

Every stage emits a "[promote-pattern] Stage N: <label>" line to stderr so
the skill orchestrator can show progress via Bash stderr capture.

Env:
  PATTERN_PROMOTION_SKIP_VALIDATE_SH=1  -- skip the baseline-delta validate.sh
    step. Used by unit tests that don't want a real ./validate.sh invocation.
  PATTERN_PROMOTION_HOOK_TEST_TIMEOUT=<secs>  -- override default 30s timeout
    on the generated hook test script execution.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from pattern_promotion.kb_parser import KBEntry
from pattern_promotion.types import DiffPlan, FileEdit, Result


# ---------------------------------------------------------------------------
# Constants / environment
# ---------------------------------------------------------------------------

_TIMEOUT_ENV = "PATTERN_PROMOTION_HOOK_TEST_TIMEOUT"
_DEFAULT_TIMEOUT_SECS = 30

_SKIP_VALIDATE_ENV = "PATTERN_PROMOTION_SKIP_VALIDATE_SH"
_VALIDATE_TIMEOUT_SECS = 60  # validate.sh typically <5s; generous ceiling

# Regex for extracting error count / category headers from validate.sh output.
# Matches "Errors: N", "N errors", "Total errors: N" (case-insensitive).
_ERROR_COUNT_RE = re.compile(
    r"(?:^|\s)(?:total\s+errors|errors?)\s*[:=]\s*(\d+)",
    re.IGNORECASE | re.MULTILINE,
)
# Category headers look like "Checking X..." in validate.sh output. We treat
# the set of check headers whose subsequent section contains an ERROR line as
# distinct categories. Simpler proxy: any line matching `[ERROR] <category>:`
# or `ERROR in <category>:` or `<category>: ERROR`.
_ERROR_CATEGORY_RE = re.compile(
    r"(?:\[ERROR\]|ERROR)\s*(?:in\s+)?([A-Za-z][\w\-./ ]*?)\s*[:\-]",
)

# Marker patterns per TD-8. Both the bash-comment form and the HTML-comment
# form contain the literal `Promoted` adjacent to the entry name.
_BASH_MARKER_RE = re.compile(r"^\s*#\s*Promoted\s+from\s+KB\s+entry\s*:\s*(.+?)\s*$")
_MD_MARKER_RE = re.compile(r"<!--\s*Promoted\s*:\s*(.+?)\s*-->")


# ---------------------------------------------------------------------------
# Stage logging
# ---------------------------------------------------------------------------


def _log_stage(n: int, label: str) -> None:
    """Emit a stage-boundary progress line to stderr."""
    print(f"[promote-pattern] Stage {n}: {label}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Stage 1 helpers
# ---------------------------------------------------------------------------


def _is_hooks_json(path: Path) -> bool:
    return path.name == "hooks.json"


def _stage1_preflight(
    entry: KBEntry,
    diff_plan: DiffPlan,
) -> tuple[bool, Optional[str]]:
    """Run all three pre-flight checks. Return (ok, reason)."""
    # 1. file existence vs action
    for edit in diff_plan.edits:
        if edit.action == "modify":
            if not edit.path.is_file():
                return False, f"modify target does not exist: {edit.path}"
        elif edit.action == "create":
            if edit.path.exists():
                return (
                    False,
                    f"create target already exists: {edit.path}",
                )
        else:
            return False, f"unknown action {edit.action!r} for {edit.path}"

    # 2. JSON validity for any hooks.json edit (check the `after` content).
    for edit in diff_plan.edits:
        if _is_hooks_json(edit.path):
            try:
                json.loads(edit.after)
            except (ValueError, TypeError) as exc:
                return (
                    False,
                    f"patched hooks.json is not valid JSON: {exc}",
                )

    # 3. TD-8 partial-run collision detection.
    #    Scan the directories that will be touched (plus the hook-target's
    #    hooks/ dir for bash markers) for existing files carrying the same
    #    entry-name marker. Any match -> abort.
    scan_dirs: set[Path] = set()
    for edit in diff_plan.edits:
        parent = edit.path.parent
        if parent.is_dir():
            scan_dirs.add(parent)
    for d in scan_dirs:
        # Only scan files at the top level of each touched directory;
        # avoid recursive walks on large trees.
        try:
            candidates = list(d.iterdir())
        except OSError:
            continue
        for cand in candidates:
            if not cand.is_file():
                continue
            # Ignore the files that this plan itself will create/modify — a
            # modify target legitimately pre-exists, and its pre-image content
            # is what we compare against the TD-8 marker.
            if cand in {e.path for e in diff_plan.edits}:
                # Allow modify targets: only a pre-existing marker for a
                # DIFFERENT action would indicate partial-run state.
                # But collision is really about OTHER files not in this plan,
                # so skip these.
                continue
            try:
                text = cand.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            # Fast-path pre-filter: skip anything without `Promoted` substring.
            if "Promoted" not in text:
                continue
            # Match either dialect against the entry name.
            for line in text.splitlines():
                m = _BASH_MARKER_RE.match(line)
                if m and m.group(1).strip() == entry.name.strip():
                    return (
                        False,
                        (
                            f"possible prior partial run: found TD-8 marker "
                            f"for {entry.name!r} in {cand}"
                        ),
                    )
            for m in _MD_MARKER_RE.finditer(text):
                if m.group(1).strip() == entry.name.strip():
                    return (
                        False,
                        (
                            f"possible prior partial run: found TD-8 marker "
                            f"for {entry.name!r} in {cand}"
                        ),
                    )

    return True, None


# ---------------------------------------------------------------------------
# Stage 2 / 3 — snapshot + write
# ---------------------------------------------------------------------------


def _stage2_snapshot(diff_plan: DiffPlan) -> dict[Path, Optional[str]]:
    """Record pre-image content for every edit.

    Maps path -> original content (modify) or None (create).
    """
    snapshot: dict[Path, Optional[str]] = {}
    for edit in diff_plan.edits:
        if edit.action == "modify":
            snapshot[edit.path] = edit.path.read_text(encoding="utf-8")
        else:
            snapshot[edit.path] = None
    return snapshot


def _stage3_write(
    diff_plan: DiffPlan,
) -> tuple[bool, Optional[str], list[FileEdit]]:
    """Write in ascending write_order (ties broken by path).

    Returns (ok, reason, applied_edits). `applied_edits` lists the edits that
    were successfully written up to (and not including) the failing one — used
    by rollback.
    """
    applied: list[FileEdit] = []
    ordered = sorted(diff_plan.edits, key=lambda e: (e.write_order, str(e.path)))
    for edit in ordered:
        try:
            edit.path.parent.mkdir(parents=True, exist_ok=True)
            edit.path.write_text(edit.after, encoding="utf-8")
            applied.append(edit)
        except Exception as exc:  # deliberate: any failure = abort
            return False, f"write failed for {edit.path}: {exc}", applied
    return True, None, applied


def _rollback(
    snapshot: dict[Path, Optional[str]],
    applied: list[FileEdit],
) -> None:
    """Reverse every applied edit using the snapshot.

    For modify: write back the original content.
    For create: unlink the created file (if it exists).
    Rollback must be best-effort — per-file failures are logged to stderr but
    do not re-raise (otherwise rollback errors would mask the original cause).
    """
    for edit in reversed(applied):
        try:
            original = snapshot.get(edit.path)
            if edit.action == "create":
                if edit.path.exists():
                    edit.path.unlink()
            else:  # modify
                if original is not None:
                    edit.path.write_text(original, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - rollback-of-rollback
            print(
                f"[promote-pattern] rollback warning for {edit.path}: {exc}",
                file=sys.stderr,
            )


# ---------------------------------------------------------------------------
# Stage 4 — post-write validation
# ---------------------------------------------------------------------------


def _hook_test_script_path(diff_plan: DiffPlan) -> Optional[Path]:
    """Return the test script path (write_order=1) for a hook DiffPlan."""
    for edit in diff_plan.edits:
        if edit.write_order == 1:
            return edit.path
    return None


def _run_hook_test_script(script: Path) -> tuple[bool, Optional[str]]:
    """Execute the generated test script with a bounded timeout.

    Returns (ok, reason). On timeout the reason mentions "timeout" so callers
    can surface it verbatim.
    """
    timeout_secs = _DEFAULT_TIMEOUT_SECS
    override = os.environ.get(_TIMEOUT_ENV)
    if override:
        try:
            timeout_secs = int(override)
        except ValueError:
            pass  # use default; bad env values are not fatal
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            timeout=timeout_secs,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            f"hook test script timeout after {timeout_secs}s: {script}",
        )
    except FileNotFoundError as exc:
        return False, f"hook test script not found: {exc}"
    except OSError as exc:
        return False, f"hook test script failed to execute: {exc}"
    if proc.returncode != 0:
        snippet = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
        tail = snippet[0] if snippet else ""
        return (
            False,
            f"hook test script exited {proc.returncode}: {tail}",
        )
    return True, None


def _run_validate_sh(
    cwd: Optional[Path] = None,
) -> tuple[bool, int, set[str], Optional[str]]:
    """Run ./validate.sh once and parse error count + category set.

    Returns:
      (ok, error_count, categories, reason)
      - ok=True means validate.sh exited 0 (clean OR warnings-only depending on
        the script's exit-code semantics). ok=False indicates non-zero exit.
      - error_count is the highest "Errors: N" mention found; 0 if none.
      - categories is the set of error-category tokens (see _ERROR_CATEGORY_RE).
      - reason is non-None only when ok=False (contains a short summary).

    If validate.sh is absent, timeout, or otherwise unexecutable, returns
    ok=False with a reason so callers can surface the error. Unit tests that
    don't need real validate.sh should set PATTERN_PROMOTION_SKIP_VALIDATE_SH=1
    and call apply() directly; this helper won't be invoked in that case.
    """
    script_path = Path("validate.sh")
    if cwd is not None:
        script_path = cwd / "validate.sh"
    if not script_path.is_file():
        return False, 0, set(), f"validate.sh not found at {script_path}"
    try:
        proc = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(cwd) if cwd else None,
            timeout=_VALIDATE_TIMEOUT_SECS,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            0,
            set(),
            f"validate.sh timeout after {_VALIDATE_TIMEOUT_SECS}s",
        )
    except OSError as exc:
        return False, 0, set(), f"validate.sh failed to execute: {exc}"

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    count = 0
    for m in _ERROR_COUNT_RE.finditer(combined):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if n > count:
            count = n
    categories: set[str] = set()
    for m in _ERROR_CATEGORY_RE.finditer(combined):
        cat = m.group(1).strip()
        if cat:
            categories.add(cat.lower())

    if proc.returncode != 0:
        return False, count, categories, f"validate.sh exited {proc.returncode}"
    return True, count, categories, None


def _stage4_validate(
    diff_plan: DiffPlan, target_type: str
) -> tuple[bool, Optional[str]]:
    """Post-write validation: existence + re-parse + (hook) test script."""
    # 1. Every edited path must exist.
    for edit in diff_plan.edits:
        if not edit.path.is_file():
            return False, f"post-write file missing: {edit.path}"

    # 2. hooks.json must re-parse as JSON.
    for edit in diff_plan.edits:
        if _is_hooks_json(edit.path):
            try:
                json.loads(edit.path.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                return (
                    False,
                    f"post-write hooks.json parse failed: {exc}",
                )

    # 3. Hook target: run the TD-7 test script.
    if target_type == "hook":
        test_script = _hook_test_script_path(diff_plan)
        if test_script is None:
            return False, "hook target missing test script (write_order=1)"
        ok, reason = _run_hook_test_script(test_script)
        if not ok:
            return False, reason

    return True, None


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def apply(
    entry: KBEntry,
    diff_plan: DiffPlan,
    target_type: str,
) -> Result:
    """Run Stages 1-4 atomically. Return Result with success + rollback flags.

    On Stage 1 failure: returns (success=False, rolled_back=False) because no
    writes were performed.
    On Stage 2/3/4 failure: rollback runs and returns rolled_back=True.
    """
    # ---- Stage 1
    _log_stage(1, "pre-flight validation")
    ok, reason = _stage1_preflight(entry, diff_plan)
    if not ok:
        return Result(
            success=False,
            target_path=None,
            reason=reason,
            rolled_back=False,
            stage_completed=1,
        )

    # ---- Stage 2
    _log_stage(2, "snapshot")
    try:
        snapshot = _stage2_snapshot(diff_plan)
    except Exception as exc:
        return Result(
            success=False,
            target_path=None,
            reason=f"snapshot failed: {exc}",
            rolled_back=False,
            stage_completed=2,
        )

    # ---- Stage 2b: baseline validate.sh (per FR-5 Stage 4 baseline-delta).
    # Run immediately after snapshot, BEFORE any Stage 3 writes so a baseline
    # failure aborts with zero writes. Tests may skip via env var.
    skip_validate = os.environ.get(_SKIP_VALIDATE_ENV) == "1"
    baseline_count = 0
    baseline_categories: set[str] = set()
    if not skip_validate:
        _log_stage(2, "baseline validate.sh")
        ok_v, baseline_count, baseline_categories, v_reason = _run_validate_sh()
        if not ok_v:
            return Result(
                success=False,
                target_path=None,
                reason=(
                    f"baseline validate.sh failed before any writes: "
                    f"{v_reason}"
                ),
                rolled_back=False,
                stage_completed="baseline",
            )

    # ---- Stage 3
    _log_stage(3, "write")
    ok, reason, applied = _stage3_write(diff_plan)
    if not ok:
        print(
            f"[promote-pattern] rollback: {reason}",
            file=sys.stderr,
        )
        _rollback(snapshot, applied)
        return Result(
            success=False,
            target_path=None,
            reason=reason,
            rolled_back=True,
            stage_completed=3,
        )

    # ---- Stage 4
    _log_stage(4, "post-write validation")
    ok, reason = _stage4_validate(diff_plan, target_type)
    if not ok:
        print(
            f"[promote-pattern] rollback: {reason}",
            file=sys.stderr,
        )
        _rollback(snapshot, applied)
        return Result(
            success=False,
            target_path=None,
            reason=reason,
            rolled_back=True,
            stage_completed=4,
        )

    # ---- Stage 4b: baseline-delta validate.sh.
    # Re-run validate.sh; rollback only if post_count > baseline_count OR any
    # new category appeared (pre-existing errors are tolerated per TD-5).
    if not skip_validate:
        _log_stage(4, "baseline-delta validate.sh")
        _, post_count, post_categories, post_reason = _run_validate_sh()
        new_categories = post_categories - baseline_categories
        if post_count > baseline_count or new_categories:
            delta_reason = (
                f"validate.sh regression: baseline={baseline_count} "
                f"post={post_count} new_categories={sorted(new_categories)}"
            )
            print(f"[promote-pattern] rollback: {delta_reason}", file=sys.stderr)
            _rollback(snapshot, applied)
            return Result(
                success=False,
                target_path=None,
                reason=delta_reason,
                rolled_back=True,
                stage_completed=4,
            )

    return Result(
        success=True,
        target_path=diff_plan.target_path,
        reason=None,
        rolled_back=False,
        stage_completed=4,
    )
