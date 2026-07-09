#!/usr/bin/env python3
from __future__ import annotations

import argparse
from factory_lib import dump_json, ensure_issue_key, load_json, now_iso, repo_root, run_state_path, slugify

parser = argparse.ArgumentParser(description="Initialize factory run state")
parser.add_argument("--issue", help="Linear issue key, e.g. ENG-123")
parser.add_argument("--title", required=True, help="Issue or feature title")
parser.add_argument("--tracker", default="linear")
parser.add_argument("--branch")
parser.add_argument("--discard-active", action="store_true",
                    help="deliberately abandon the previous task's unarchived artifacts")
args = parser.parse_args()

root = repo_root()
issue_key = ensure_issue_key(args.issue, root)
branch = args.branch or f"feat/{issue_key}-{slugify(args.title)}"
previous = load_json(run_state_path(root), default={})
signed_off = bool(previous.get("client_signoff"))
state = {
    "issue_key": issue_key,
    "title": args.title,
    "tracker": args.tracker,
    "branch": branch,
    # Intake must never bypass or erase the sign-off gate.
    "phase": "planning" if signed_off else "discovery",
    "plan_status": "needs-plan",
    "decomposition_status": "pending",
    "implementation_status": "pending",
    "tests_status": "pending",
    "verify_status": "pending",
    "review_status": "pending",
    "created_at": now_iso(),
    "updated_at": now_iso(),
}
for key in ("project", "client_signoff", "client_signoff_record", "client_signoff_at"):
    if key in previous:
        state[key] = previous[key]
# Task-scoped artifacts belong to the previous task. Clear them only when that
# task was archived (pr_ready/done); otherwise they are unrecovered evidence.
factory = root / ".factory"
stale_files = [
    p for p in (factory / "decomposition.json", factory / "verify.json", factory / "tests.json")
    if p.exists()
] + list((factory / "reviews").glob("*.json"))
if stale_files:
    prev_archived = previous.get("phase") in {"pr-ready", "done"}
    if not prev_archived and not args.discard_active:
        raise SystemExit(
            f"Task {previous.get('issue_key', '?')} has unarchived artifacts "
            f"({len(stale_files)} file(s) in .factory/). Finish it (pr_ready.py archives "
            "the evidence) or pass --discard-active to abandon it deliberately."
        )
    for stale in stale_files:
        stale.unlink()
dump_json(run_state_path(root), state)
print(f"Initialized factory state for {issue_key} -> {branch}")
if not signed_off:
    print(
        "Phase set to 'discovery': client sign-off not recorded yet. "
        "Run `python3 .agents/scripts/record_signoff.py` before planning."
    )
