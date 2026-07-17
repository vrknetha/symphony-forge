"""forge roadmap — the durable project backlog (plans/roadmap.json).

Task-scoped .factory state is cleared on every intake; this file is the
cross-task handoff artifact: the PM-owned epics and the EM-groomed, ordered
stories left to build. It is recorded once from the project-level
decomposition after sign-off (gated on an accepted `epics-approved` decision
— the PM handoff), then refined by PR. intake marks items active, pr_ready
marks them done, `forge roadmap assign` distributes them across the team,
and `forge next` suggests the next pending one.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from factory_lib import (
    dump_json, load_json, now_iso, repo_root, require_grill, validate_payload,
)

from .common import fail

# Set by the lifecycle scripts or grooming, never by import — re-importing a
# refined roadmap must not resurrect items, un-finish them, or unassign devs.
LIFECYCLE_FIELDS = {"status", "completed_at", "history", "assignee"}
ITEM_SKILLS = {"frontend", "backend", "fullstack"}


def roadmap_path(base: Path) -> Path:
    return base / "plans" / "roadmap.json"


def load_roadmap(base: Path) -> dict:
    return load_json(roadmap_path(base), default={})


def load_items(base: Path) -> list[dict]:
    return load_roadmap(base).get("items", [])


def save_roadmap(base: Path, items: list[dict], epics: list[dict] | None = None) -> None:
    data = load_roadmap(base)
    items.sort(key=lambda item: item.get("order", 0))
    data["items"] = items
    if epics is not None:
        data["epics"] = epics
    data["updated_at"] = now_iso()
    roadmap_path(base).parent.mkdir(parents=True, exist_ok=True)
    dump_json(roadmap_path(base), data)


def mark_status(base: Path, key: str, status: str, **extra: str) -> bool:
    """Flip an item's lifecycle status; False if the key is not on the roadmap."""
    items = load_items(base)
    for item in items:
        if item.get("key") == key:
            item["status"] = status
            item.update(extra)
            save_roadmap(base, items)
            return True
    return False


def epics_approved(base: Path) -> bool:
    """The PM->EM handoff gate: an accepted epics-approved decision record."""
    for record in (base / "docs" / "decisions").glob("*epics-approved*.md"):
        text = record.read_text()
        confirmed = re.search(r'confirmed_by:\s*"([^"]+)"', text)
        if "status: accepted" in text and confirmed:
            return True
    return False


def check_item(item: dict, pos: int) -> None:
    if not isinstance(item, dict) or not item.get("key") or not item.get("title"):
        fail(f"roadmap item {pos} needs at least 'key' and 'title'")
    criteria = item.get("acceptance_criteria")
    if criteria is not None and not isinstance(criteria, list):
        fail(f"roadmap item {item['key']}: acceptance_criteria must be a list")
    skill = item.get("skill")
    if skill is not None and skill not in ITEM_SKILLS:
        fail(f"roadmap item {item['key']}: skill must be one of "
             f"{', '.join(sorted(ITEM_SKILLS))}")
    deps = item.get("depends_on")
    if deps is not None and not isinstance(deps, list):
        fail(f"roadmap item {item['key']}: depends_on must be a list of story keys")


def ready_pending(items: list[dict]) -> tuple[list[dict], list[tuple[dict, list[str]]]]:
    """The parallelizable frontier: pending items whose depends_on are all
    done. Anything else pending is blocked, with the keys it waits on."""
    status = {i.get("key"): i.get("status", "pending") for i in items}
    ready: list[dict] = []
    blocked: list[tuple[dict, list[str]]] = []
    for item in items:
        if item.get("status", "pending") != "pending":
            continue
        waiting = [d for d in item.get("depends_on", []) if status.get(d) != "done"]
        if waiting:
            blocked.append((item, waiting))
        else:
            ready.append(item)
    return ready, blocked


def cmd_import(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    # Grill BEFORE the PM accepts: the epics/stories are interrogated for
    # coverage gaps and contradictions against BRIEF + decisions, so what the
    # EM distributes downstream is already de-risked.
    require_grill(
        base, "epics",
        ("docs/product/", "docs/decisions/"),
        ignore_names=("epics-approved", "client-signoff"),
    )
    if not epics_approved(base):
        fail(
            "the roadmap import is the PM->EM handoff and requires PM approval of "
            "the epics first: `./forge decision new epics-approved` (list the epics "
            "in the record), then A HUMAN runs "
            '`./forge decision accept epics-approved --by "<PM name>"`.'
        )
    source = Path(args.input).expanduser()
    if not source.is_file():
        fail(f"roadmap input {source} not found")
    try:
        payload = json.loads(source.read_text())
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {source}: {exc}")
    if not isinstance(payload, dict):
        fail('roadmap input must be {"generated_by": "...", "epics": [...], "items": [...]}')
    validate_payload(base, "roadmap", payload)
    incoming = payload["items"]
    if not incoming:
        fail("roadmap input has no items")
    seen: set[str] = set()
    for pos, item in enumerate(incoming, 1):
        check_item(item, pos)
        if item["key"] in seen:
            fail(f"duplicate roadmap key: {item['key']}")
        seen.add(item["key"])
    # Dependency edges must resolve to real stories (incoming or existing) —
    # a dangling edge would silently serialize or silently unblock.
    known = seen | {i["key"] for i in load_items(base)}
    for item in incoming:
        for dep in item.get("depends_on", []):
            if dep == item["key"]:
                fail(f"roadmap item {item['key']} depends on itself")
            if dep not in known:
                fail(f"roadmap item {item['key']}: depends_on '{dep}' is not on the roadmap")
    incoming_epics = payload.get("epics", [])
    for pos, epic in enumerate(incoming_epics, 1):
        if not isinstance(epic, dict) or not epic.get("id") or not epic.get("title"):
            fail(f"epic {pos} needs at least 'id' and 'title'")
    existing = {item["key"]: item for item in load_items(base)}
    merged: list[dict] = []
    added = updated = 0
    for pos, item in enumerate(incoming, 1):
        entry = existing.pop(item["key"], None)
        if entry is None:
            entry = {"status": "pending"}
            added += 1
        else:
            updated += 1
        entry.update({k: v for k, v in item.items() if k not in LIFECYCLE_FIELDS})
        entry["order"] = item.get("order", pos)
        merged.append(entry)
    # Items on the roadmap but absent from the input are kept — removing
    # scope is a deliberate PR edit, never a silent import side effect.
    kept = list(existing.values())
    merged.extend(kept)
    # Epics merge by id, same keep-what-input-omits rule.
    current_epics = {e["id"]: e for e in load_roadmap(base).get("epics", [])}
    for epic in incoming_epics:
        current_epics[epic["id"]] = {**current_epics.get(epic["id"], {}), **epic}
    save_roadmap(base, merged, epics=list(current_epics.values()))
    summary = f"Roadmap: {added} added, {updated} updated"
    if kept:
        summary += f", {len(kept)} existing item(s) kept"
    if incoming_epics:
        summary += f", {len(incoming_epics)} epic(s) recorded"
    print(f"{summary} -> {roadmap_path(base).relative_to(base)}")


def cmd_add(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    items = load_items(base)
    if any(item.get("key") == args.key for item in items):
        fail(f"{args.key} is already on the roadmap")
    order = max((item.get("order", 0) for item in items), default=0) + 1
    item = {"key": args.key, "title": args.title, "order": order, "status": "pending"}
    if args.epic:
        item["epic"] = args.epic
    if args.skill:
        if args.skill not in ITEM_SKILLS:
            fail(f"skill must be one of {', '.join(sorted(ITEM_SKILLS))}")
        item["skill"] = args.skill
    items.append(item)
    save_roadmap(base, items)
    print(f"Added {args.key} to the roadmap (order {order})")


def cmd_assign(args: argparse.Namespace) -> None:
    """EM distribution: put a dev's handle on a story, checked against the roster."""
    base = Path(args.repo).resolve() if args.repo else repo_root()
    from .team import member_handles  # local import: team is optional machinery
    handles = member_handles(base)
    if handles and args.to not in handles:
        fail(
            f"'{args.to}' is not on the team roster ({', '.join(sorted(handles))}) — "
            f"add them first: ./forge team set {args.to} --skills <frontend,backend|fullstack>"
        )
    if not mark_status_free_update(base, args.key, assignee=args.to):
        fail(f"{args.key} is not on the roadmap")
    print(f"{args.key} assigned to {args.to}")


def mark_status_free_update(base: Path, key: str, **fields: str) -> bool:
    items = load_items(base)
    for item in items:
        if item.get("key") == key:
            item.update(fields)
            save_roadmap(base, items)
            return True
    return False


def cmd_parallel(args: argparse.Namespace) -> None:
    """The orchestrator's fan-out view: which stories can run CONCURRENTLY
    right now (pending, dependencies done), each in its own worktree —
    one task per branch with its own committed .factory state (decision
    0002), implementations driven via /codex:rescue --background."""
    base = Path(args.repo).resolve() if args.repo else repo_root()
    from factory_lib import slugify
    items = load_items(base)
    if not items:
        print("No roadmap yet — nothing to parallelize (./forge roadmap import first).")
        return
    ready, blocked = ready_pending(items)
    if not ready:
        print("No pending stories are unblocked right now.")
    else:
        print(f"{len(ready)} stor{'y is' if len(ready) == 1 else 'ies are'} independent "
              "and can run IN PARALLEL — one worktree each:")
        for item in ready:
            who = f" @{item['assignee']}" if item.get("assignee") else ""
            skill = f" [{item['skill']}]" if item.get("skill") else ""
            branch = f"feat/{item['key']}-{slugify(item['title'])}"
            print(f"\n  {item['key']} — {item['title']}{skill}{who}")
            print(f"    git worktree add ../{base.name}-{item['key']} -b {branch}")
            print(f"    (cd ../{base.name}-{item['key']} && python3 .agents/scripts/intake.py "
                  f"--issue {item['key']} --title \"{item['title']}\")")
    for item, waiting in blocked:
        print(f"\n  BLOCKED {item['key']} — waiting on: {', '.join(waiting)}")
    print("\nEach worktree carries its own branch + .factory state; roadmap "
          "status flips converge when branches merge. Parallelize stories, "
          "never one story's dependent leaf tasks.")


def cmd_list(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    data = load_roadmap(base)
    items = data.get("items", [])
    if not items:
        print("No roadmap yet — record the project decomposition as the backlog: "
              "./forge roadmap import --input <json> (see .agents/prompts/decomposer.md)")
        return
    epic_titles = {e["id"]: e.get("title", e["id"]) for e in data.get("epics", [])}
    marks = {"pending": " ", "active": ">", "done": "x"}
    shown = 0
    by_epic: dict[str, list[dict]] = {}
    for item in items:
        by_epic.setdefault(item.get("epic", ""), []).append(item)
    for epic_id in by_epic:
        if epic_id:
            print(f"# {epic_titles.get(epic_id, epic_id)}")
        for item in by_epic[epic_id]:
            status = item.get("status", "pending")
            if args.pending and status != "pending":
                continue
            shown += 1
            extras = []
            if item.get("skill"):
                extras.append(item["skill"])
            if item.get("assignee"):
                extras.append(f"@{item['assignee']}")
            suffix = f" ({', '.join(extras)})" if extras else ""
            print(f"[{marks.get(status, '?')}] {item.get('order', 0):>3}. "
                  f"{item['key']} — {item['title']}{suffix}")
    done = sum(1 for item in items if item.get("status") == "done")
    if args.pending and not shown:
        print("Nothing pending — everything is in flight or done.")
    if not args.pending:
        print(f"({done}/{len(items)} done)")
