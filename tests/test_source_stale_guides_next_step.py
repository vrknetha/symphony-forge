"""Close names uv run --frozen forge sync for stale guides in Forge's own checkout."""
import os
import re
import shutil
import subprocess

import pytest

from conftest import ROOT
from test_close import env  # noqa: F401

STORY = "when-forge-s-branch-templates-differ-fro"


@pytest.mark.parametrize("version_change", [False, True], ids=["same-version", "version-change"])
def test_1_source_stale_guides_suggests_uv_run_sync(env, version_change):
    # Audit: protects the Next line for stale guides in forge-source on both same-version and
    # version-changing fixes, checks that close compares against the branch's templates rather
    # than the installed release, and proves `uv run --frozen forge sync` regenerates the guides
    # from the branch's templates so close then passes. Closest existing test:
    # test_close_stops_stale_guides.py overwrites the forge shim to point at the branch and never
    # tests version-changing source fixes or `uv run --frozen forge sync`.
    repo = env.repo
    repo.git("checkout", "-q", "-b", "fix/setup-source")
    shutil.copytree(ROOT / "src/forge", repo.path / "src/forge",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for rel in (".gitignore", "pyproject.toml", "uv.lock", "README.md"):
        shutil.copyfile(ROOT / rel, repo.path / rel)
    base_toml = (repo.path / "forge.toml").read_text("utf-8") + 'repo = "forge-source"\n'
    installed = re.search(r'^version = "(.+)"$', base_toml, re.M)[1]
    repo.write("forge.toml", base_toml)
    synced = repo.forge("sync")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    hooks = env.tmp / "fixture-hooks"
    hooks.mkdir()
    repo.git("config", "core.hooksPath", hooks.as_posix())
    if version_change:
        repo.write("forge.toml", base_toml.replace(installed, "v1.0.0", 1))
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "Keep source project and generated guides")
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--ff-only", "fix/setup-source")
    repo.git("push", "-q", "origin", "main")

    rel = "src/forge/templates/skill.md"
    template = (repo.path / rel).read_text("utf-8")
    edited = template + "\nBranch template change.\n"
    guide = (repo.path / ".codex/skills/forge/SKILL.md").read_text("utf-8")
    expected = edited.rstrip("\n") + guide[len(template.rstrip("\n")):]
    changes = {rel: edited}
    if version_change:
        # Branch pins the installed Forge while its committed guides still match the installed
        # templates rather than the branch's edited template.
        changes["forge.toml"] = base_toml
    item, where = env.start_fix(changes)

    closed = repo.forge("close", item, cwd=where if version_change else repo.path)

    assert closed.returncode == 1, closed.stdout + closed.stderr
    expected_next = (
        f"Next: uv run --frozen forge sync in {where}, commit what it wrote, then forge close {item}\n"
        if version_change else
        f"Next: in {where.as_posix()}, run uv run --frozen forge sync, "
        "then commit the generated guides and run close again.\n"
    )
    assert closed.stderr.endswith(expected_next), closed.stderr
    assert not env.review_calls()

    run_env = os.environ.copy()
    run_env.pop("VIRTUAL_ENV", None)
    run_env.pop("PYTHONPATH", None)
    run_env["UV_PROJECT_ENVIRONMENT"] = str(env.tmp / "uv-venv")
    rebuilt = subprocess.run(["uv", "run", "--frozen", "forge", "sync"],
                             cwd=where, env=run_env, capture_output=True, text=True)
    assert rebuilt.returncode == 0, rebuilt.stdout + rebuilt.stderr
    for host in (".claude", ".codex"):
        assert (where / host / "skills/forge/SKILL.md").read_text("utf-8") == expected

    repo.git("add", "-A", cwd=where)
    repo.git("commit", "-q", "-m",
             "Sync guides\n\nProof list:\n- Done when: check: The readme opens with a greeting",
             cwd=where)
    done = repo.forge("close", item, cwd=where if version_change else repo.path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Ready:" in done.stdout
