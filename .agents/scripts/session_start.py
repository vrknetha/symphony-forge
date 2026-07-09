#!/usr/bin/env python3
from __future__ import annotations

import json
from factory_lib import load_json, read_hook_input, repo_root, run_state_path

payload = read_hook_input()
root = repo_root()
run_state = load_json(run_state_path(root), default={})
if not run_state:
    print(json.dumps({}))
    raise SystemExit(0)
context = [
    f"Active issue: {run_state.get('issue_key')} — {run_state.get('title')}",
    f"Current phase: {run_state.get('phase')}",
    f"Plan status: {run_state.get('plan_status')}",
    f"Decomposition status: {run_state.get('decomposition_status')}",
    f"Client sign-off: {run_state.get('client_signoff', False)}",
]
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(context)
    }
}))
