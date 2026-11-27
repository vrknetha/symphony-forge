"""Owner stops, parked items, and desktop notices for the background runner."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from forge import codex, repo, story, task


def _path(top: Path) -> Path:
    return repo.forge_dir(top) / "runner.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    stopped_list = [x for x in raw.get("stopped", []) if isinstance(x, str)]
    told_raw = raw.get("told", {})
    told_map = {k: v for k, v in told_raw.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(told_raw, dict) else {}
    return {"stopped": stopped_list, "told": told_map}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def _worktree(top: Path, item: str) -> Path:
    for branch, tree in story.worktrees(top).items():
        if branch.startswith("story/"):
            continue
        found = task.branch_item(branch, tree)
        if found and found[0] == item:
            return tree
    return top


def _sig(top: Path, item: str, tree: Path | None = None) -> str:
    location = tree if tree is not None else _worktree(top, item)
    head = ""
    state_text = ""
    if location.is_dir():
        head = repo.run("git", "rev-parse", "HEAD", cwd=location).stdout.strip()
        state_file = location / repo.state_path(item)
        if state_file.is_file():
            with contextlib.suppress(OSError):
                state_text = state_file.read_text(encoding="utf-8")
    question = codex.record(top, item).get("question") or ""
    payload = json.dumps([head, state_text, question], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stopped(top: Path, item: str) -> bool:
    """Whether the owner has stopped this item."""
    return item in _read(_path(top))["stopped"]


def parked(top: Path, item: str, tree: Path | None = None) -> bool:
    """Whether this item was already told to the owner with the same signature."""
    recorded = _read(_path(top))["told"].get(item)
    return recorded is not None and recorded == _sig(top, item, tree)


def lift(top: Path, item: str) -> None:
    """Clear the owner's stop and parked state when a person runs forge land on this item."""
    path = _path(top)
    with codex._one_at_a_time(path):
        data = _read(path)
        changed = False
        if item in data["stopped"]:
            data["stopped"] = [x for x in data["stopped"] if x != item]
            changed = True
        if item in data["told"]:
            data["told"].pop(item, None)
            changed = True
        if changed:
            _write(path, data)


def add(top: Path, item: str) -> None:
    """Record that the owner stopped this item."""
    path = _path(top)
    with codex._one_at_a_time(path):
        data = _read(path)
        if item not in data["stopped"]:
            data["stopped"].append(item)
            _write(path, data)


def _still_waiting(top: Path, item: str, default: str) -> bool:
    if task._merged(f"origin/{default}", item, top):
        return False
    tree = _worktree(top, item)
    state = repo.read_state(item, tree)
    return bool(state and state.get("status") != "dropped")


def _notice_body(top: Path, item: str, code: int, lines: list[str]) -> str:
    question = codex.record(top, item).get("question")
    if isinstance(question, str) and question.strip():
        return question.strip()
    tree = _worktree(top, item)
    state = repo.read_state(item, tree) or {}
    stop = state.get("stop") or {}
    if stop and not stop.get("choice"):
        if isinstance(stop.get("question"), str) and stop["question"].strip():
            return stop["question"].strip()
        from forge import review

        return review.stop_question(tree, item, state).strip()
    if code == 0:
        for line in lines:
            if line.startswith(f"{item} is ready; a human merges"):
                return line.strip()
    tail = lines
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith(("Stopped:", "Stopped after ")):
            tail = lines[i + 1:]
            break
    next_line = ""
    refusal = ""
    for raw in tail:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Next: "):
            next_line = line
            continue
        if not refusal:
            refusal = line
    if not refusal:
        refusal = next((raw.strip() for raw in lines if raw.strip()), f"{item} needs you.")
    if next_line and next_line not in refusal:
        return f"{refusal}\n{next_line}"
    return refusal


def _notify(title: str, body: str) -> None:
    if os.name == "nt":
        return
    if sys.platform == "darwin":
        cmd = [
            "osascript",
            "-e", "on run argv",
            "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
            "-e", "end run",
            title,
            body,
        ]
    else:
        cmd = ["notify-send", title, body]
    with contextlib.suppress(OSError):
        subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def ended(top: Path, item: str, code: int, lines: list[str]) -> None:
    """Record that an item stopped and needs the owner, sending one desktop notice per state."""
    sig = _sig(top, item)
    path = _path(top)
    with codex._one_at_a_time(path):
        data = _read(path)
        if data["told"].get(item) == sig:
            return
        data["told"][item] = sig
        _write(path, data)
    _notify(f"{top.name}: {item}", _notice_body(top, item, code, lines))


def summary(top: Path, merged: list[str]) -> None:
    """Send the end-of-run summary notice for a repo the runner worked on."""
    path = _path(top)
    default = repo.default_branch(top)
    merged_set = set(merged)
    with codex._one_at_a_time(path):
        data = _read(path)
        kept_stopped = [item for item in data["stopped"]
                        if item not in merged_set and _still_waiting(top, item, default)]
        kept_told = {item: sig for item, sig in data["told"].items()
                     if item not in merged_set and _still_waiting(top, item, default)}
        if kept_stopped != data["stopped"] or kept_told != data["told"]:
            data["stopped"] = kept_stopped
            data["told"] = kept_told
            _write(path, data)
    waiting = list(dict.fromkeys([*kept_told, *kept_stopped]))
    body = f"{len(merged)} merged."
    if waiting:
        body += f" Waiting for you: {', '.join(waiting)}."
    _notify(f"{top.name}: Forge runner done", body)
