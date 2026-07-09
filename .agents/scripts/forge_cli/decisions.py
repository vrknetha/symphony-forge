"""forge decision new/accept — decision records with human confirmation."""
from __future__ import annotations

import argparse
import datetime
import re
from pathlib import Path

from factory_lib import repo_root

from .common import fail

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


def cmd_new(args: argparse.Namespace) -> None:
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


def cmd_accept(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    decisions = base / "docs" / "decisions"
    slug = args.slug.strip().lower().replace(" ", "-")
    matches = sorted(decisions.glob(f"[0-9][0-9][0-9][0-9]-{slug}.md"))
    if not matches:
        fail(f"no decision record matching docs/decisions/NNNN-{slug}.md")
    record = matches[-1]
    text = record.read_text()
    if "status: accepted" in text:
        print(f"{record.relative_to(base)} is already accepted.")
        return
    text = text.replace("status: proposed", "status: accepted", 1)
    if 'confirmed_by: ""' in text:
        text = text.replace('confirmed_by: ""', f'confirmed_by: "{args.by}"', 1)
    else:
        text = re.sub(r"confirmed_by: .*", f'confirmed_by: "{args.by}"', text, count=1)
    record.write_text(text)
    rel = record.relative_to(base)
    print(f"Accepted: {rel} (confirmed_by: {args.by})")
    print("Commit it with the audit trailer:")
    print(f'  git add {rel} && git commit -m "docs(decisions): accept {slug}" '
          f'--trailer "Confirmed-by: {args.by}"')
    if slug == "client-signoff":
        print("Then arm the gate: python3 .agents/scripts/record_signoff.py")
