"""forge upgrade — re-vendor harness machinery into an existing client repo.

Run FROM the harness clone, targeting the client repo (mirrors `forge init`).
Replaces machinery the harness owns; never touches project-owned content.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from factory_lib import head_sha, repo_root

from .common import fail
from .scaffold import COPY_CODEX, DOC_CONTRACTS

# Harness-owned: replaced wholesale on upgrade.
UPGRADE_TREES = [".agents", ".claude", "constitution", "harness", ".github"]
UPGRADE_FILES = ["forge", "CLAUDE.md", "WORKFLOW.md"]
# Project-owned: never touched — listed here as the explicit contract.
PROJECT_OWNED = [
    "harness.yaml", "AGENTS.md", ".factory/", "plans/", "prototype/",
    "docs/product/", "docs/decisions/", "docs/architecture/", "docs/context/",
]
# Preserved across the .agents replacement (project evolution state).
PRESERVE_IN_AGENTS = [".agents/skills/proposed"]


def cmd_upgrade(args: argparse.Namespace) -> None:
    harness = repo_root()
    target = Path(args.target).resolve()
    if not (target / ".git").exists() or not (target / "AGENTS.md").exists():
        fail(f"{target} does not look like a scaffolded repo (.git + AGENTS.md required)")
    if target == harness:
        fail("run upgrade FROM the harness clone TARGETING a client repo, not itself")
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=target, capture_output=True, text=True
    ).stdout.strip()
    if dirty and not args.force:
        fail(
            f"{target} has uncommitted changes. Commit or stash first so the upgrade "
            "is a reviewable diff (--force to override)."
        )

    preserved: dict[str, Path] = {}
    keep_root = Path(tempfile.mkdtemp(prefix="forge-upgrade-keep-"))
    for rel in PRESERVE_IN_AGENTS:
        src = target / rel
        if src.exists():
            dest = keep_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest)
            preserved[rel] = dest

    for tree in UPGRADE_TREES:
        src = harness / tree
        if not src.exists():
            continue
        dst = target / tree
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    (target / ".codex").mkdir(exist_ok=True)
    for name in COPY_CODEX:
        shutil.copy2(harness / ".codex" / name, target / ".codex" / name)
    for sub in ("agents", "skills"):
        src = harness / ".codex" / sub
        if src.is_dir():
            dst = target / ".codex" / sub
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    for name in UPGRADE_FILES:
        src = harness / name
        if src.exists():
            shutil.copy2(src, target / name)
    for src_rel, dst_rel in DOC_CONTRACTS:
        src = harness / src_rel
        if src.exists():
            dst = target / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for rel, kept in preserved.items():
        dst = target / rel
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(kept, dst)
    shutil.rmtree(keep_root, ignore_errors=True)

    commit = head_sha(harness) or "unknown"
    (target / "constitution" / "VENDORED_FROM").write_text(
        f"symphony-forge @ {commit}\nUpdate by re-vendoring from the harness repo; do not edit in place.\n"
    )

    drift = ""
    if (harness / "harness.yaml").read_text() != (target / "harness.yaml").read_text():
        drift = ("\nNOTE: harness.yaml differs from the harness default (project-owned, "
                 "left untouched) — diff manually if the phase contract changed upstream.")
    print(f"Upgraded {target} to symphony-forge @ {commit[:8]}")
    print("Replaced (harness-owned): " + ", ".join(UPGRADE_TREES + UPGRADE_FILES) + ", doc contracts")
    print("Untouched (project-owned): " + ", ".join(PROJECT_OWNED) + drift)
    print("Next: review with `git diff`, run `python3 .agents/scripts/check_dual_runtime.py` "
          "and the gate tests, then commit.")
