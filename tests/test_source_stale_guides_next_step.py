"""Close names uv run --frozen forge sync for stale guides in Forge's own checkout."""
import os
import shutil
import subprocess

from conftest import ROOT
from test_close import env  # noqa: F401

STORY = "when-forge-s-branch-templates-differ-fro"


def test_1_source_stale_guides_suggests_uv_run_sync(env):
    # Audit: protects the Next line for stale guides in forge-source and proves that running
    # `uv run --frozen forge sync` regenerates guides from the branch's templates rather than
    # an installed release. Closest existing test: test_close_stops_stale_guides.py overwrites
    # the forge shim to point at the branch, so it never exercises `uv run --frozen forge sync`.
    repo = env.repo
    repo.git("checkout", "-q", "-b", "fix/setup-source")
    shutil.copytree(ROOT / "src/forge", repo.path / "src/forge",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for rel in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copyfile(ROOT / rel, repo.path / rel)
    repo.write("forge.toml", (repo.path / "forge.toml").read_text("utf-8") + 'repo = "forge-source"\n')
    synced = repo.forge("sync")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    hooks = env.tmp / "fixture-hooks"
    hooks.mkdir()
    repo.git("config", "core.hooksPath", hooks.as_posix())
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
    item, where = env.start_fix({rel: edited})

    closed = env.close(item)

    assert closed.returncode == 1, closed.stdout + closed.stderr
    assert closed.stderr.endswith(
        f"Next: in {where.as_posix()}, run uv run --frozen forge sync, "
        "then commit the generated guides and run close again.\n"
    )
    run_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    rebuilt = subprocess.run(["uv", "run", "--frozen", "forge", "sync"],
                             cwd=where, env=run_env, capture_output=True, text=True)
    assert rebuilt.returncode == 0, rebuilt.stdout + rebuilt.stderr
    for host in (".claude", ".codex"):
        assert (where / host / "skills/forge/SKILL.md").read_text("utf-8") == expected
