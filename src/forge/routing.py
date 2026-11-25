"""Which forge.toml supplies the routing settings: the default branch's, unless a branch changed them."""
from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from forge import repo

ROUTING = ("tools", "workers", "models")
REVIEW_REFRESH_REFUSAL = ("Forge could not check the latest reader settings.",
                          "check origin, then forge read {target}")


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


def _review_selector(top: Path) -> dict[str, Any]:
    """Read the landed review setting without rejecting keys this installed Forge does not know."""
    from forge import story

    text = story.show(top, story.landed_ref(top), "forge.toml")
    if text is None:
        return {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        repo.refuse(repo.REFUSALS["bad_config"], problem=exc)
    selected = {key: data[key] for key in ("version", "reviews") if key in data}
    if problem := repo._config_problem(selected):
        repo.refuse(repo.REFUSALS["bad_config"], problem=problem)
    return selected


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


def routed_reviews(top: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Use the last-fetched default review family unless this branch changed it since its fork."""
    local, shared = cfg.get("local", {}), cfg.get("shared", cfg)
    if "reviews" in local:
        return cfg
    main = repo.command_fact("review routing main", top, lambda: _review_selector(top))
    if shared.get("reviews") == main.get("reviews"):
        return cfg
    fork = repo.command_fact(("review routing fork", str(top)), top, lambda: _fork_config(top, "HEAD"))
    if fork is None or shared.get("reviews") != fork.get("reviews"):
        return cfg
    updated = dict(cfg)
    if "reviews" in main:
        updated["reviews"] = main["reviews"]
    else:
        updated.pop("reviews", None)
    return updated


def refresh_reviews(top: Path, target: str) -> None:
    """Refresh the default branch before a read, with checkout hooks disabled for this fetch."""
    remotes = repo.run("git", "remote", cwd=top)
    if remotes.returncode:
        repo.refuse(REVIEW_REFRESH_REFUSAL, target=target)
    if "origin" not in remotes.stdout.splitlines():
        return  # Local-only repos use their current default branch.
    default = repo.default_branch(top)
    with TemporaryDirectory() as temp:
        hooks = Path(temp) / "hooks"
        hooks.mkdir()
        try:
            count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
            env = {**os.environ, "GIT_CONFIG_COUNT": str(count + 1),
                   f"GIT_CONFIG_KEY_{count}": "core.hooksPath",
                   f"GIT_CONFIG_VALUE_{count}": str(hooks)}
            repo.git("fetch", "-q", "--no-recurse-submodules", "origin",
                     f"+refs/heads/{default}:refs/remotes/origin/{default}", cwd=top, env=env)
        except (ValueError, subprocess.CalledProcessError):
            repo.refuse(REVIEW_REFRESH_REFUSAL, target=target)
