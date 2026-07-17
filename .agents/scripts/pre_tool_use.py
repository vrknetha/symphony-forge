#!/usr/bin/env python3
from __future__ import annotations

import json
import re

from factory_lib import load_json, read_hook_input, repo_root, run_state_path

payload = read_hook_input()
tool_name = payload.get("tool_name", "")
tool_input = payload.get("tool_input") or {}
command = (tool_input.get("command") or "").strip()
permission_mode = payload.get("permission_mode", "")


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    raise SystemExit(0)


# Planning lock: while an active task is UNPLANNED, implementation is refused
# and the dev is pushed into plan mode. Planning-phase writes (the plan,
# decisions, docs, harness machinery) stay allowed; PRODUCT code does not.
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
PLANNING_WRITE_OK = (
    "plans/", "docs/", ".factory/", ".agents/", ".claude/", ".codex/",
    ".gstack/", ".github/", "constitution/", "harness/", "prototype/",
)
PLANNING_WRITE_OK_FILES = {
    "AGENTS.md", "CLAUDE.md", "WORKFLOW.md", "harness.yaml", "README.md",
    ".gitignore", ".gitattributes", ".envrc",
}
PLAN_MODE_MSG = (
    "Task {issue} is in PLANNING — implementation is blocked until the plan is "
    "approved and saved. Switch Claude Code to PLAN MODE (shift+tab) and plan per "
    ".agents/prompts/planner.md (or use the Codex planner-high agent), then "
    "`forge.py plan save --from <plan-file>`. Exploration stays available: "
    "/codex:rescue --model gpt-5.6-terra --effort high (read-only by default)."
)


def planning_locked(state: dict) -> bool:
    return bool(
        state.get("issue_key")
        and state.get("client_signoff")
        and state.get("plan_status") != "approved"
    )


blocked = [
    r"\brm\s+-rf\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\s+--force\b",
    r"\bterraform\s+destroy\b",
    r"\bkubectl\s+delete\b",
]
for pattern in blocked:
    if re.search(pattern, command):
        deny(f"Blocked by factory policy: {command}")

# Raw `codex exec` bypasses the sanctioned runtime (/codex:rescue -> the
# plugin companion): no session threading, no background management, no
# repo-pinned invocation shape. There is NO escape hatch — doctor installs
# codex-plugin-cc as a required tool; if it breaks, repair it or work in a
# Codex session directly (docs/degraded-mode.md).
if "codex exec" in command:
    deny(
        "Direct `codex exec` is off-contract — invoke Codex through the plugin: "
        "/codex:rescue [--background] [--write] [--model <m>] [--effort <e>] \"<task>\" "
        "(read-only unless --write). Plugin missing or broken? `./forge doctor --fix` "
        "reinstalls it; meanwhile work in a Codex session directly "
        "(docs/degraded-mode.md) — same prompts, same artifacts, same gates."
    )

check_bypass = ["pnpm test", "pnpm lint", "pnpm typecheck", "pnpm check:all"]
if any(token in command for token in check_bypass) and ".agents/scripts/verify.py" not in command:
    deny(
        "Use `python3 .agents/scripts/verify.py` so verification artifacts stay deterministic."
    )

# Sign-off gate: heavy factory phases cannot start before client sign-off.
# Discovery/prototype phases and record_signoff.py itself stay allowed.
PHASE_ADVANCING = (
    "record_decomposition_from_json.py",
    "pr_ready.py",
)
GATED_PHASES = (
    "planning",
    "decomposing",
    "awaiting-approval",
    "implementing",
    "testing",
    "reviewing",
    "functional-check",
    "pr-ready",
)
root = repo_root()
run_state = load_json(run_state_path(root), default={})

if run_state and planning_locked(run_state) and permission_mode != "plan":
    issue = run_state.get("issue_key", "?")
    if tool_name in EDIT_TOOLS:
        target = (tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        rel = target
        if target.startswith(str(root)):
            rel = target[len(str(root)):].lstrip("/")
        if rel and not rel.startswith(PLANNING_WRITE_OK) and rel not in PLANNING_WRITE_OK_FILES:
            deny(PLAN_MODE_MSG.format(issue=issue))
    if tool_name == "Bash" and "codex-companion.mjs" in command \
            and " task" in command and "--write" in command:
        # Writing delegation during planning = implementation before a plan.
        deny(PLAN_MODE_MSG.format(issue=issue))

if run_state and not run_state.get("client_signoff"):
    advancing = any(script in command for script in PHASE_ADVANCING)
    if "update_run.py" in command and "--phase" in command:
        advancing = advancing or any(phase in command for phase in GATED_PHASES)
    if advancing:
        deny(
            "Client sign-off not recorded. Get docs/decisions/NNNN-client-signoff.md "
            "accepted (non-empty confirmed_by), then run "
            "`python3 .agents/scripts/record_signoff.py` before advancing the phase."
        )

print(json.dumps({}))
