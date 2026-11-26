"""Coordinator chat cues from host transcripts and the shared handoff note."""
from __future__ import annotations

import json
import mmap
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from forge import repo

CLAUDE_USAGE = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
                "output_tokens")


def _counts(path: str, window: object) -> tuple[object, object] | None:
    # Walk backwards so each Bash call only reads the tail needed for the latest count.
    with open(path, "rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        end = len(data)
        while end > 0:
            start = data.rfind(b"\n", 0, end)
            line = data[start + 1:end]
            end = start
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                continue
            if not isinstance(record, dict):
                continue
            event = record.get("payload")
            if isinstance(event, dict) and event.get("type") == "token_count":
                info = event.get("info") or {}
                latest = info.get("last_token_usage") or {}
                return latest.get("total_tokens"), info.get("model_context_window")
            if record.get("type") == "assistant":
                usage = (record.get("message") or {}).get("usage")
                if isinstance(usage, dict):
                    values = [usage.get(key, 0) for key in CLAUDE_USAGE]
                    if all(type(value) is int and value >= 0 for value in values):
                        return sum(values), window or 1_000_000
                return None
    return None


def warning(payload: dict[str, Any]) -> str | None:
    path, session = payload.get("transcript_path"), payload.get("session_id")
    if (payload.get("agent_id") or os.environ.get("FORGE_WORKER") == "1"
            or not isinstance(path, str) or not path or not isinstance(session, str) or not session):
        return None
    try:
        counts = _counts(path, payload.get("context_window") or payload.get("model_context_window"))
        if counts is None:
            return None
        used, window = counts
        if type(used) is not int or type(window) is not int or window <= 0 or used * 2 <= window:
            return None
        tenth = used * 10 // window
        state = repo.forge_dir(repo.root()) / "context-warnings.json"
        from forge.codex import _one_at_a_time

        with _one_at_a_time(state):
            warned = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
            if tenth <= warned.get(session, 0):
                return None
            warned[session] = tenth
            pending = state.with_suffix(".new")
            pending.write_text(json.dumps(warned), encoding="utf-8")
            pending.replace(state)
    except (OSError, ValueError, AttributeError, TypeError, RecursionError,
            subprocess.CalledProcessError, repo.Refused):
        return None
    return (f"This chat uses {_tokens(used)} of {_tokens(window)} tokens. "
            "Hand over at the next quiet moment: see Handoff in the Forge guide.")


def _tokens(count: int) -> str:
    for unit, size in (("M", 1_000_000), ("K", 1_000)):
        if count % size == 0 and count >= size:
            return f"{count // size}{unit}"
    return f"{count:,}"


def handoff_hint(top: Path) -> str:
    if os.environ.get("FORGE_WORKER") == "1":
        return ""
    try:
        path = repo.forge_dir(top) / "handoff.md"
        with path.open(encoding="utf-8") as note:
            for line in note:
                if date := re.fullmatch(r"## Current state \((\d{4}-\d{2}-\d{2})\)\s*", line):
                    return f"Read the handoff note {path.as_posix()} from {date[1]} first, then run forge next."
    except (OSError, UnicodeError):
        pass
    return ""
