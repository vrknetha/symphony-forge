#!/usr/bin/env python3
from __future__ import annotations

import argparse
from factory_lib import dump_json, ensure_issue_key, load_json, now_iso, repo_root, run_state_path, slugify

parser = argparse.ArgumentParser(description="Initialize factory run state")
parser.add_argument("--issue", help="Linear issue key, e.g. ENG-123")
parser.add_argument("--title", required=True, help="Issue or feature title")
parser.add_argument("--tracker", default="linear")
parser.add_argument("--branch")
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
# Task-scoped artifacts belong to the previous task (pr_ready.py archived them
# to .factory/history/); clear them so the new task starts at planning.
factory = root / ".factory"
for stale in ("decomposition.json", "verify.json", "tests.json"):
    (factory / stale).unlink(missing_ok=True)
for review in (factory / "reviews").glob("*.json"):
    review.unlink()
dump_json(run_state_path(root), state)
print(f"Initialized factory state for {issue_key} -> {branch}")
if not signed_off:
    print(
        "Phase set to 'discovery': client sign-off not recorded yet. "
        "Run `python3 .agents/scripts/record_signoff.py` before planning."
    )
