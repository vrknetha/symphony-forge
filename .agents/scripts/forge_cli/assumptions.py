"""forge assumptions — the structured ledger (plans/assumptions.md).

Every call an implementer makes that the plan does not cover lands here as a
row the ORCHESTRATOR (the coordinating session / EM) can scan and guide:
confirm it, demand a fix, or promote it to a decision record. `forge plan
assume` appends rows during implementation; `pr_ready.py` refuses to ship a
task while any of its assumptions are still `open` or `fix-needed` — guidance
is a gate, not a hope. The file is markdown so humans read it in the PR; the
row format is strict so the tooling can manage it.
"""
from __future__ import annotations

import argparse
import datetime
import re
from pathlib import Path

from factory_lib import repo_root

from .common import fail

HEADER = """# Implementation Assumptions Ledger

One row per assumption made during implementation (`forge plan assume`).
The orchestrator reviews open rows and guides:
`./forge assumptions resolve <id> --status confirmed|fix-needed|promoted --notes "..."`.
`pr_ready.py` refuses while the task has rows at `open` or `fix-needed`.

| id | date | issue | assumption | status | guidance |
|----|------|-------|------------|--------|----------|
"""

STATUSES = {"open", "confirmed", "fix-needed", "promoted"}
BLOCKING = {"open", "fix-needed"}
ROW = re.compile(r"^\| (A-\d{4}) \| ([^|]*) \| ([^|]*) \| (.*) \| ([a-z-]+) \| (.*) \|$")


def ledger_path(base: Path) -> Path:
    return base / "plans" / "assumptions.md"


def _clean(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def load_rows(base: Path) -> list[dict]:
    path = ledger_path(base)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        match = ROW.match(line)
        if match:
            rows.append({
                "id": match.group(1), "date": match.group(2).strip(),
                "issue": match.group(3).strip(), "assumption": match.group(4).strip(),
                "status": match.group(5).strip(), "guidance": match.group(6).strip(),
            })
    return rows


def save_rows(base: Path, rows: list[dict]) -> None:
    lines = [f"| {r['id']} | {r['date']} | {r['issue']} | {r['assumption']} "
             f"| {r['status']} | {r['guidance']} |" for r in rows]
    ledger_path(base).parent.mkdir(parents=True, exist_ok=True)
    ledger_path(base).write_text(HEADER + "\n".join(lines) + ("\n" if lines else ""))


def append_row(base: Path, issue: str, assumption: str) -> str:
    rows = load_rows(base)
    next_id = max((int(r["id"][2:]) for r in rows), default=0) + 1
    rows.append({
        "id": f"A-{next_id:04d}", "date": datetime.date.today().isoformat(),
        "issue": _clean(issue), "assumption": _clean(assumption),
        "status": "open", "guidance": "",
    })
    save_rows(base, rows)
    return rows[-1]["id"]


def blocking_for_issue(base: Path, issue: str) -> list[dict]:
    return [r for r in load_rows(base) if r["issue"] == issue and r["status"] in BLOCKING]


def open_count(base: Path) -> int:
    return sum(1 for r in load_rows(base) if r["status"] in BLOCKING)


def cmd_list(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    rows = load_rows(base)
    if not rows:
        print("No assumptions recorded (plans/assumptions.md) — "
              "implementers add them via `forge plan assume`.")
        return
    for r in rows:
        if args.open and r["status"] not in BLOCKING:
            continue
        guidance = f" — {r['guidance']}" if r["guidance"] else ""
        print(f"[{r['status']:<10}] {r['id']} {r['issue']}: {r['assumption']}{guidance}")


def cmd_resolve(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    if args.status not in STATUSES - {"open"}:
        fail(f"--status must be one of {', '.join(sorted(STATUSES - {'open'}))}")
    if not (args.notes or "").strip():
        fail("--notes required: the guidance IS the record "
             "(what to do about it / why it stands / which decision it became)")
    rows = load_rows(base)
    row = next((r for r in rows if r["id"] == args.id), None)
    if row is None:
        fail(f"{args.id} is not in plans/assumptions.md")
    row["status"] = args.status
    row["guidance"] = _clean(args.notes)
    save_rows(base, rows)
    print(f"{args.id}: {args.status} — {row['guidance']}")
    if args.status == "promoted":
        print("Promoted assumptions need a record: ./forge decision new <slug>")
