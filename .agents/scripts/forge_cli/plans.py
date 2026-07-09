"""forge plan save/assume — approved plans and implementation assumptions."""
from __future__ import annotations

import argparse
import datetime
from pathlib import Path

from factory_lib import dump_json, load_json, now_iso, repo_root, run_state_path, slugify

from .common import fail
from .context import pending_context


def cmd_save(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    if not state or not state.get("client_signoff"):
        fail(
            "plan approval requires an initialized run with client sign-off. Run "
            "intake, get docs/decisions/NNNN-client-signoff.md accepted, run "
            "record_signoff.py, then save the plan."
        )
    pending = pending_context(base)
    if pending:
        fail(
            f"{len(pending)} docs/context/ file(s) are unharvested: {', '.join(pending[:5])}"
            f"{'…' if len(pending) > 5 else ''}. Plans must not be approved over pending "
            "context — run `forge.py context scan`, harvest per .agents/prompts/harvester.md "
            "or mark irrelevant ones `forge.py context mark <file> --ignored`, then save."
        )
    issue = args.issue or state.get("issue_key")
    if not issue:
        fail("no --issue given and no issue_key in .factory/run.json (run intake first)")
    source = Path(args.source).expanduser()
    if not source.is_file():
        fail(f"plan source {source} not found — pass the approved plan file via --from")
    title = args.title or state.get("title") or issue
    dest_dir = base / "plans" / "active"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{issue}-{slugify(title)}.md"
    header = (
        f"---\nissue: {issue}\ntitle: {title}\nstatus: approved\nsaved: {now_iso()}\n---\n\n"
    )
    dest.write_text(header + source.read_text())
    if state:
        state["plan_status"] = "approved"
        state["plan_file"] = str(dest.relative_to(base))
        state["updated_at"] = now_iso()
        dump_json(run_state_path(base), state)
    print(f"Plan saved to {dest.relative_to(base)} (plan_status: approved)")
    print(
        "Decisions made while planning must exist as docs/decisions/ records "
        "(forge.py decision new <slug>) and be referenced in the plan."
    )


def cmd_assume(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    issue = args.issue or state.get("issue_key")
    if not issue:
        fail("no --issue given and no issue_key in .factory/run.json (run intake first)")
    plans = sorted((base / "plans" / "active").glob(f"{issue}-*.md"))
    if not plans:
        fail(
            f"no active plan for {issue} (plans/active/{issue}-*.md). Save the approved "
            "plan first with `forge.py plan save` — assumptions attach to a plan."
        )
    plan = plans[-1]
    text = plan.read_text()
    heading = "## Implementation Assumptions"
    entry = f"- {datetime.date.today().isoformat()}: {args.text.strip()}\n"
    if heading in text:
        text = text.rstrip("\n") + "\n" + entry
    else:
        text = (
            text.rstrip("\n")
            + f"\n\n{heading}\n\n"
            "<!-- Made during implementation, NOT part of the approved plan. "
            "Dev: review these before merge; promote any that matter to docs/decisions/. -->\n"
            + entry
        )
    plan.write_text(text)
    print(f"Assumption recorded in {plan.relative_to(base)}")
    print("Dev reviews these before merge; promote durable ones: forge.py decision new <slug>")
