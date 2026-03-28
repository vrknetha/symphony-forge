#!/usr/bin/env python3
from __future__ import annotations

import json
from factory_lib import load_json, read_hook_input, repo_root, run_state_path

payload = read_hook_input()
prompt = (payload.get("prompt") or "").lower()
run_state = load_json(run_state_path(repo_root()), default={})
needs_plan = any(word in prompt for word in ["implement", "build", "code", "fix", "ship"])
if needs_plan and not run_state:
    print(json.dumps({"decision": "block", "reason": "No factory state found. Run intake and planning before implementation."}))
    raise SystemExit(0)
if needs_plan and run_state.get("plan_status") in {"needs-plan", "awaiting-approval"}:
    print(json.dumps({"decision": "block", "reason": "Implementation is blocked until the plan is approved. Update .factory/run.json phase first."}))
    raise SystemExit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "If the request is vague, clarify it into acceptance criteria and task decomposition before coding."
    }
}))
