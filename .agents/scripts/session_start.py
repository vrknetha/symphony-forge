#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from factory_lib import load_json, read_hook_input, repo_root, run_state_path

payload = read_hook_input()
root = repo_root()
run_state = load_json(run_state_path(root), default={})

# Per-clone, idempotent: register the JSONL union merge driver that
# .gitattributes references, so two devs appending to .gstack stores merge
# cleanly. Quiet — configuration, not conversation.
attributes = root / ".gitattributes"
if attributes.exists() and "merge=jsonl-append" in attributes.read_text():
    have = subprocess.run(
        ["git", "config", "merge.jsonl-append.driver"],
        cwd=root, capture_output=True, text=True,
    )
    driver = Path.home() / ".claude" / "skills" / "gstack" / "bin" / "gstack-jsonl-merge"
    if have.returncode != 0 and driver.is_file():
        subprocess.run(
            ["git", "config", "merge.jsonl-append.driver", f"{driver} %O %A %B"],
            cwd=root, capture_output=True,
        )
context = []
if run_state.get("issue_key"):
    context += [
        f"Active issue: {run_state.get('issue_key')} — {run_state.get('title')}",
        f"Current phase: {run_state.get('phase')}",
        f"Plan status: {run_state.get('plan_status')}",
        f"Decomposition status: {run_state.get('decomposition_status')}",
        f"Client sign-off: {run_state.get('client_signoff', False)}",
    ]
ledger = load_json(root / "docs" / "context" / "ledger.json", default={"files": {}})
pending = sum(1 for e in ledger.get("files", {}).values() if e.get("status") == "pending")
if pending:
    context.append(
        f"Unharvested context: {pending} file(s) in docs/context/ — harvest before planning."
    )
from forge_cli.assumptions import open_count  # noqa: E402
assumptions_open = open_count(root)
if assumptions_open:
    context.append(
        f"Assumptions awaiting orchestrator guidance: {assumptions_open} "
        "(plans/assumptions.md — `forge.py assumptions list --open`)."
    )
proposed = len(list((root / ".agents" / "skills" / "proposed").glob("*.md")))
if proposed:
    context.append(
        f"Proposed skills awaiting human review: {proposed} in .agents/skills/proposed/."
    )
if not context:
    print(json.dumps({}))
    raise SystemExit(0)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(context)
    }
}))
