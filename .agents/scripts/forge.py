#!/usr/bin/env python3
"""forge — the harness CLI. `./forge <command>` from the repo root.

Commands: doctor, init, next, plan (save|assume), context (scan|list|mark),
decision (new|accept). Implementations live in forge_cli/ — one module per
concern; this file is argument wiring only.
"""
from __future__ import annotations

import argparse

from forge_cli import context as ctx
from forge_cli import decisions, doctor, phase, plans, scaffold, upgrade


def main() -> None:
    parser = argparse.ArgumentParser(prog="forge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="check machine prerequisites for the harness")
    p_doc.add_argument("--fix", action="store_true",
                       help="auto-install everything installable; logins stay manual")
    p_doc.set_defaults(func=doctor.cmd_doctor)

    p_next = sub.add_parser("next", help="where am I and what do I do now (deterministic)")
    p_next.add_argument("--repo")
    p_next.set_defaults(func=phase.cmd_next)

    p_init = sub.add_parser("init", help="scaffold a new client repo from this harness")
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--target")
    p_init.add_argument("--stack", default="nestjs-react")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=scaffold.cmd_init)

    p_up = sub.add_parser("upgrade",
                          help="re-vendor harness machinery into a client repo (run from the harness)")
    p_up.add_argument("--target", required=True, help="the client repo to upgrade")
    p_up.add_argument("--force", action="store_true",
                      help="proceed even if the target has uncommitted changes")
    p_up.set_defaults(func=upgrade.cmd_upgrade)

    p_plan = sub.add_parser("plan", help="manage task plans")
    plan_sub = p_plan.add_subparsers(dest="plan_command", required=True)
    p_save = plan_sub.add_parser("save", help="persist an approved plan into plans/active/")
    p_save.add_argument("--from", dest="source", required=True,
                        help="path to the approved plan file (e.g. the Claude Code plan)")
    p_save.add_argument("--issue", help="issue key (defaults to .factory/run.json)")
    p_save.add_argument("--title", help="plan title (defaults to run.json title)")
    p_save.add_argument("--repo", help="target repo (defaults to this repo)")
    p_save.set_defaults(func=plans.cmd_save)
    p_assume = plan_sub.add_parser(
        "assume", help="record an implementation assumption on the active plan")
    p_assume.add_argument("text", help="the assumption, one sentence")
    p_assume.add_argument("--issue", help="issue key (defaults to .factory/run.json)")
    p_assume.add_argument("--repo")
    p_assume.set_defaults(func=plans.cmd_assume)

    p_ctx = sub.add_parser("context", help="track the docs/context inbox")
    ctx_sub = p_ctx.add_subparsers(dest="context_command", required=True)
    p_scan = ctx_sub.add_parser("scan", help="register new/changed context files in the ledger")
    p_scan.add_argument("--check", action="store_true",
                        help="fail if the ledger is out of sync (CI mode; writes nothing)")
    p_scan.add_argument("--repo")
    p_scan.set_defaults(func=ctx.cmd_scan)
    p_list = ctx_sub.add_parser("list", help="show ledger entries")
    p_list.add_argument("--pending", action="store_true")
    p_list.add_argument("--repo")
    p_list.set_defaults(func=ctx.cmd_list)
    p_mark = ctx_sub.add_parser("mark", help="record harvest outcome for a context file")
    p_mark.add_argument("file")
    group = p_mark.add_mutually_exclusive_group(required=True)
    group.add_argument("--harvested", action="store_true")
    group.add_argument("--ignored", action="store_true")
    p_mark.add_argument("--outputs", nargs="*", help="repo-relative paths the harvest produced")
    p_mark.add_argument("--notes")
    p_mark.add_argument("--repo")
    p_mark.set_defaults(func=ctx.cmd_mark)

    p_dec = sub.add_parser("decision", help="manage decision records")
    dec_sub = p_dec.add_subparsers(dest="decision_command", required=True)
    p_new = dec_sub.add_parser("new", help="create the next NNNN-<slug>.md record")
    p_new.add_argument("slug")
    p_new.add_argument("--title")
    p_new.add_argument("--repo", help="target repo (defaults to this repo)")
    p_new.set_defaults(func=decisions.cmd_new)
    p_acc = dec_sub.add_parser("accept", help="mark a decision accepted with a human's name")
    p_acc.add_argument("slug")
    p_acc.add_argument("--by", required=True, help="the human confirming (not an agent)")
    p_acc.add_argument("--repo")
    p_acc.set_defaults(func=decisions.cmd_accept)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
