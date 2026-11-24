"""Which forge.toml supplies the routing settings: the default branch's, unless a branch changed them."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from forge import repo

ROUTING = ("tools", "workers", "models")


def _tried(read, top: Path):
    try:
        return read(top)
    except (repo.Refused, subprocess.CalledProcessError):
        return None


def _fork_config(top: Path, ref: str) -> dict[str, Any] | None:
    """The settings at the fork point of ref and the default branch, or None when unreadable."""
    try:
        fork = repo.git("merge-base", ref, f"origin/{repo.default_branch(top)}", cwd=top)
        text = repo.read_blob(top, f"{fork}:forge.toml")
        return repo._config_text(text) if text is not None else None
    except (repo.Refused, subprocess.CalledProcessError):
        return None


def routed(top: Path, cfg: dict[str, Any], ref: str = "HEAD") -> dict[str, Any]:
    """cfg with each of tools, workers and models taken from the default branch's forge.toml, then
    this clone's forge.local.toml, unless the branch at ref changed that key itself since it left
    the default branch. So a change on main reaches open stories and tasks before they merge main."""
    # Fetched once per command, even when it fails, whatever the worktree.
    main = repo.command_fact("routing main", top, lambda: _tried(repo.default_config, top))
    shared = cfg.get("shared", cfg)
    if main is None or all(shared[key] == main[key] for key in ROUTING):
        return cfg  # nothing to take from main, so no fork lookup
    fork = repo.command_fact(("routing fork", ref if ref != "HEAD" else str(top)), top, lambda: _fork_config(top, ref))
    if fork is None:
        return cfg
    # Keep what repo.config already adjusted (sample mode clears checks), then lay the local file over.
    base = {**shared, **{key: cfg[key] for key in ("test", "fast_test", "checks", "test_place")}}
    for key in ROUTING:
        if shared[key] == fork[key]:
            base[key] = main[key]
    return repo._with_local(base, top)
