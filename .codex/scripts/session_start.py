#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from factory_lib import load_json, read_hook_input, repo_root, run_state_path

payload = read_hook_input()
root = repo_root()
run_state = load_json(run_state_path(root), default={})
context = [
    "Factory mode: planning -> approval -> ACP Codex implementation -> verify -> review -> PR-ready.",
    "Use WORKFLOW.md and AGENTS.md as the operating contract.",
    "For coding work, prefer ACP/ACPX Codex workers over stuffing context into the coordinator.",
    "After verify passes, spawn the read-only review subagents: quality-reviewer, performance-reviewer, security-reviewer.",
]
if run_state:
    context.append(f"Active issue: {run_state.get('issue_key')} — {run_state.get('title')}")
    context.append(f"Current phase: {run_state.get('phase')}")
    context.append(f"Plan status: {run_state.get('plan_status')}")
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(context)
    }
}))
