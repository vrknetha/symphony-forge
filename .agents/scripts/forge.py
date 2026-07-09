#!/usr/bin/env python3
"""forge — bootstrap a new client repo from this harness, and manage decision records.

Usage:
  python3 .agents/scripts/forge.py init --name <project> [--target <dir>] [--stack nestjs-react] [--force]
  python3 .agents/scripts/forge.py decision new <slug> [--title <title>] [--repo <dir>]
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

from factory_lib import dump_json, now_iso, repo_root

COPY_TREES = [".agents", ".claude", "constitution", "harness", ".github"]
COPY_CODEX = ["config.toml", "hooks.json"]  # + agents/ dir
COPY_FILES = ["harness.yaml", ".gitignore", "WORKFLOW.md"]
DOC_CONTRACTS = [
    ("docs/product/README.md", "docs/product/README.md"),
    ("docs/architecture/README.md", "docs/architecture/README.md"),
    ("docs/decisions/README.md", "docs/decisions/README.md"),
    ("docs/FACTORY.md", "docs/FACTORY.md"),
    ("docs/QUALITY.md", "docs/QUALITY.md"),
    ("docs/harness-philosophy.md", "docs/harness-philosophy.md"),
    ("docs/degraded-mode.md", "docs/degraded-mode.md"),
]

DISCOVERY_TEMPLATE = """# Discovery — {name}

Phase 0a. Lightweight on purpose: no .factory ceremony until client sign-off.

## Problem
<!-- What hurts, for whom, observed where? -->

## Stakeholders
<!-- Client-side names and roles; who signs off? -->

## Client-approved decisions
<!-- Each becomes docs/decisions/NNNN-<slug>.md via:
     python3 .agents/scripts/forge.py decision new <slug> -->
- [ ]

## Prototype notes (phase 0b)
<!-- What was shown, what the client said, what changed. -->
"""

DECISION_TEMPLATE = """---
status: proposed
confirmed_by: ""
date: {date}
---

# {title}

## Context
<!-- Why this decision was needed; the forces at play. -->

## Decision
<!-- What was decided, in one or two sentences. -->

## Consequences
<!-- What follows: tradeoffs accepted, doors closed, work implied. -->
"""


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    root = repo_root()
    target = Path(args.target or args.name).resolve()
    if target.exists() and any(target.iterdir()):
        if not args.force:
            fail(
                f"target {target} is not empty. forge init has no merge mode; "
                "use --force to overwrite an existing scaffold."
            )
    target.mkdir(parents=True, exist_ok=True)

    for tree in COPY_TREES:
        src = root / tree
        if src.exists():
            shutil.copytree(src, target / tree, dirs_exist_ok=True)
    (target / ".codex").mkdir(exist_ok=True)
    for name in COPY_CODEX:
        shutil.copy2(root / ".codex" / name, target / ".codex" / name)
    shutil.copytree(root / ".codex" / "agents", target / ".codex" / "agents", dirs_exist_ok=True)
    for name in COPY_FILES:
        src = root / name
        if src.exists():
            shutil.copy2(src, target / name)
    for src_rel, dst_rel in DOC_CONTRACTS:
        src = root / src_rel
        if src.exists():
            dst = target / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Pin the vendored constitution to its source commit.
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "unknown"
    (target / "constitution" / "VENDORED_FROM").write_text(
        f"symphony-forge @ {commit}\nUpdate by re-vendoring from the harness repo; do not edit in place.\n"
    )

    brief_src = root / "harness" / "nestjs-react" / "BRIEF_TEMPLATE.md"
    brief_dst = target / "docs" / "product" / "BRIEF.md"
    brief_dst.parent.mkdir(parents=True, exist_ok=True)
    if brief_src.exists():
        shutil.copy2(brief_src, brief_dst)
    (target / "docs" / "product" / "DISCOVERY.md").write_text(
        DISCOVERY_TEMPLATE.format(name=args.name)
    )
    (target / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    for sub in ("active", "completed", "debt"):
        plan_dir = target / "plans" / sub
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / ".gitkeep").touch()
    (target / ".factory" / "reviews").mkdir(parents=True, exist_ok=True)
    dump_json(
        target / ".factory" / "run.json",
        {"project": args.name, "client_signoff": False, "created_at": now_iso()},
    )

    agents_md = (root / "AGENTS.md").read_text().replace("Symphony Forge", args.name, 1)
    (target / "AGENTS.md").write_text(agents_md)

    if not (target / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)

    print(f"Scaffolded {args.name} at {target}")
    print("Next steps:")
    print("  1. Fill docs/product/DISCOVERY.md (phase 0a) and BRIEF.md")
    print("  2. Prototype (phase 0b), then: forge.py decision new client-signoff")
    print("  3. After the record is accepted: python3 .agents/scripts/record_signoff.py")
    print(f"  4. Generate the {args.stack} workspace via harness/{args.stack}/SCAFFOLD_PROMPT.md")


def cmd_decision_new(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    decisions = base / "docs" / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    taken = set()
    for existing in decisions.glob("[0-9][0-9][0-9][0-9]-*.md"):
        taken.add(int(existing.name[:4]))
    number = 1
    while number in taken:
        number += 1
    slug = args.slug.strip().lower().replace(" ", "-")
    path = decisions / f"{number:04d}-{slug}.md"
    title = args.title or slug.replace("-", " ").title()
    path.write_text(
        DECISION_TEMPLATE.format(date=datetime.date.today().isoformat(), title=title)
    )
    print(f"Created {path}")
    print(
        "Reminder: status: accepted requires a non-empty confirmed_by (a human), "
        "and the commit adding it should carry a `Confirmed-by:` trailer."
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="forge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold a new client repo from this harness")
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--target")
    p_init.add_argument("--stack", default="nestjs-react")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_dec = sub.add_parser("decision", help="manage decision records")
    dec_sub = p_dec.add_subparsers(dest="decision_command", required=True)
    p_new = dec_sub.add_parser("new", help="create the next NNNN-<slug>.md record")
    p_new.add_argument("slug")
    p_new.add_argument("--title")
    p_new.add_argument("--repo", help="target repo (defaults to this repo)")
    p_new.set_defaults(func=cmd_decision_new)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
