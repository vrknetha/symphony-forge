"""forge next — the deterministic 'you are here, do this' phase engine."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_lib import load_json, repo_root, run_state_path

from .context import pending_context


def cmd_next(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    factory = base / ".factory"
    pending_ctx = len(pending_context(base))
    steps: list[str] = []

    def phase(label: str) -> None:
        issue = state.get("issue_key")
        suffix = f" ({issue} — {state.get('title')})" if issue else ""
        print(f"PHASE: {label}{suffix}")

    if pending_ctx:
        steps.append(
            f"Harvest {pending_ctx} pending docs/context/ file(s) first "
            "(.agents/prompts/harvester.md; then forge.py context mark ...)"
        )
    if not state:
        phase("uninitialized")
        steps.append("New project? scaffold with: forge.py init --name <project> --target <dir>")
        steps.append("Existing project, new feature? this repo has no .factory/run.json — "
                     "run: python3 .agents/scripts/intake.py --issue <KEY> --title \"<title>\"")
    elif not state.get("client_signoff"):
        phase("discovery/prototype (0a/0b)")
        steps.append("Fill docs/product/DISCOVERY.md and BRIEF.md; prototype freely (no ceremony)")
        steps.append("Capture client decisions: forge.py decision new <slug>")
        steps.append("When the client confirms: forge.py decision new client-signoff, "
                     "then forge.py decision accept client-signoff --by <name> (human), "
                     "then run record_signoff.py")
    elif not state.get("issue_key"):
        phase("signed off — no active task")
        steps.append("Start a task: python3 .agents/scripts/intake.py --issue <KEY> --title \"<title>\"")
    elif state.get("plan_status") != "approved":
        phase("planning")
        steps.append("Plan per .agents/prompts/planner.md — Claude Code plan mode (default, "
                     "exploration via Codex read-only) or the planner-high Codex agent")
        steps.append("Record new decisions as you go: forge.py decision new <slug>")
        steps.append("On approval: forge.py plan save --from <plan-file>")
    elif state.get("decomposition_status") != "recorded":
        phase("decomposing")
        steps.append("Run docs-decomposer (.agents/prompts/decomposer.md), then "
                     "record_decomposition_from_json.py and "
                     "update_run.py --phase implementing --decomposition-status recorded")
    else:
        tests = load_json(factory / "tests.json", default={})
        verify = load_json(factory / "verify.json", default={})
        reviews_missing = [
            a for a in ("quality", "performance", "security")
            if not load_json(factory / "reviews" / f"{a}.json", default={})
        ]
        if not tests.get("automated"):
            phase("implementing")
            steps.append("Implement the next bounded leaf task via /codex:rescue --background "
                         "(.agents/prompts/implementer.md)")
            steps.append("Then run automated-tester and record: "
                         "record_test_from_json.py --kind automated --input <json>")
        elif not verify.get("ok"):
            phase("verifying")
            steps.append("Run: python3 .agents/scripts/verify.py")
        elif reviews_missing:
            phase("reviewing")
            steps.append(f"Spawn review subagents for: {', '.join(reviews_missing)}; record via "
                         "record_review_from_json.py (escalate flagged tasks to autoreview "
                         "per harness.yaml)")
        elif not tests.get("functional"):
            phase("functional-check")
            steps.append("Run functional-checker and record: "
                         "record_test_from_json.py --kind functional --input <json>")
        else:
            phase("ready for PR gate")
            steps.append("Run: python3 .agents/scripts/pr_ready.py (archives the task; merge stays manual)")
            steps.append("Next task afterwards: intake.py --issue <KEY> --title \"<title>\"")
    proposed = len(list((base / ".agents" / "skills" / "proposed").glob("*.md")))
    if proposed:
        steps.append(f"(Also: {proposed} proposed skill(s) await human review in "
                     ".agents/skills/proposed/)")
    print("NEXT:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
