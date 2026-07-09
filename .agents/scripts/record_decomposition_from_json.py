#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from factory_lib import decomposition_state_path, dump_json, load_json, now_iso, repo_root, run_state_path

parser = argparse.ArgumentParser(description="Record decomposition from structured JSON")
parser.add_argument("--input", help="Path to decomposition JSON. If omitted, read from stdin.")
args = parser.parse_args()

if args.input:
    payload = json.loads(Path(args.input).read_text())
else:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected JSON on stdin or via --input")
    payload = json.loads(raw)

root = repo_root()
state = load_json(run_state_path(root), default={})
if state and not state.get("client_signoff"):
    raise SystemExit(
        "Recording decomposition requires client sign-off first. Get "
        "docs/decisions/NNNN-client-signoff.md accepted, then run record_signoff.py."
    )
issue = state.get("issue_key", "") if state else ""
plan_files = list((root / "plans" / "active").glob(f"{issue}-*.md")) if issue else []
if state and (state.get("plan_status") != "approved" or not plan_files):
    raise SystemExit(
        "Recording decomposition requires an approved, saved plan first "
        f"(plans/active/{issue or '<issue>'}-*.md via `forge.py plan save`). "
        "Decomposition of an unapproved plan is the bug this gate exists to stop."
    )
dump_json(decomposition_state_path(root), payload)
if state:
    state["decomposition_status"] = "recorded"
    state["updated_at"] = now_iso()
    dump_json(run_state_path(root), state)
print("Recorded decomposition")
