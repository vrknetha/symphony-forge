"""Client CI, hook and pinned runner package requirements."""
import sys

import pytest
from claude_plugin_stub import _calls as _claude_calls, _claude
from conftest import ROOT, _install
from test_close import run
from test_fix_when_the_installed_forge_differs_from_th import _calls, _uv
from test_setup import _on_a_branch_with_forge_toml, _version
from test_upgrade_check import (
    BASH, UV_STUB, _install_release, _release_shim, _review_job_steps, _run_pr_check_job,
)
from test_upgrade_command import NAME, RELEASE, env, unsynced_up  # noqa: F401
from test_upgrade_pending import OLD, _pin_old

STORY = "FIX-FORGE-INSTALLS-FROM-PYPI"
pytestmark = pytest.mark.platform


def test_1_client_generated_commands_install_the_pypi_pin(repo):
    _on_a_branch_with_forge_toml(repo)
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Configure Forge")
    done = repo.forge("sync")
    assert done.returncode == 0, done.stderr
    requirement = f"symphony-forge=={_version(repo).removeprefix('v')}"
    workflow = (repo.path / ".github/workflows/forge.yml").read_text("utf-8")
    hooks = (repo.path / ".forge/hooks.sh").read_text("utf-8")
    assert f"uv tool install {requirement}" in workflow
    assert f"uvx -q --from {requirement} forge" in hooks
    assert f"uv tool install {requirement}, then run forge doctor." in hooks


def test_2_pinned_release_runner_uses_the_pypi_pin(repo):
    log = _uv(repo)
    _pin_old(repo)
    done = repo.forge("fix", "start", "Tidy the readme", "--done", "It reads well")
    assert done.returncode == 3, done.stderr
    assert _calls(log)[0]["args"][:5] == [
        "tool", "run", "--from", f"symphony-forge=={OLD.removeprefix('v')}", "forge",
    ]


def test_3_upgrade_installs_the_requested_pypi_release(unsynced_up):
    (unsynced_up.repo.bin / "uv-install-fails").touch()
    done = unsynced_up.run(RELEASE)
    assert "network is unreachable" in done.stderr + done.stdout
    assert unsynced_up.uv()[0]["args"][-1] == f"symphony-forge=={RELEASE.removeprefix('v')}"


def test_4_sync_replaces_the_disabled_claude_marketplace(repo):
    _on_a_branch_with_forge_toml(repo)
    _claude(repo, marketplace="knacklabs/symphony-forge", installed="1.2.47")
    done = repo.forge("sync")
    assert done.returncode == 0, done.stderr
    writes = [args for args in _claude_calls(repo) if args[:1] == ["plugin"] and "list" not in args]
    assert writes == [
        ["plugin", "marketplace", "remove", "forge", "--scope", "user"],
        ["plugin", "marketplace", "add", "vrknetha/symphony-forge"],
        ["plugin", "marketplace", "update", "forge"],
        ["plugin", "install", "forge@forge", "--scope", "user"],
    ]


@BASH
def test_5_upgrade_opens_a_recovery_pull_request_on_a_protected_branch(unsynced_up):
    up = unsynced_up
    repo = up.repo
    workflow = ".github/workflows/forge.yml"
    up.on_main("forge.toml", 'version = "v1.2.2"\nchecks = ["tests", "forge-pr-check"]\n')
    up.on_main(workflow, (ROOT / "tests/fixtures/doctor-v1.2.2" / workflow).read_text("utf-8"))
    base = repo.git("rev-parse", "main")
    remote = up.tmp / "remote.git"
    hook = remote / "hooks/pre-receive"
    hook.write_text('#!/bin/sh\nwhile read old new ref; do\n'
                    '  if [ "$ref" = refs/heads/main ]; then exit 1; fi\n'
                    'done\nexit 0\n', encoding="utf-8")
    hook.chmod(0o755)
    up.env.checks([run("tests")], [{"context": "forge-pr-check", "state": "failure"}])
    done = up.run(RELEASE)
    assert done.returncode == 1, done.stdout + done.stderr
    assert up.env.gh_calls("pr", "create"), done.stdout + done.stderr
    assert "Checks failed on the pull request: forge-pr-check." in done.stderr
    assert "recovering-upgrades-from-the-retired-github-repository" in done.stderr
    assert repo.git("rev-parse", "main", "origin/main").splitlines() == [base, base]
    assert up.show("forge.toml").splitlines() == [
        f'version = "{RELEASE}"', 'checks = ["tests", "forge-pr-check"]',
    ]
    assert up.uv()[0]["args"][-1] == f"symphony-forge=={RELEASE.removeprefix('v')}"
    assert up.uv()[-1]["args"][5:] == ["close", NAME]

    # Simulate the owner's reviewed GitHub merge. The server forbids direct pushes, so the
    # fixture moves the ref on the server, then the client fetches it like a normal merge.
    head = repo.git("rev-parse", f"origin/fix/{NAME}")
    repo.git("--git-dir", str(remote), "update-ref", "refs/heads/main", head, base)
    repo.git("pull", "--ff-only", "origin", "main")

    # The restored check runs from the upgraded trusted base and installs its pinned release.
    (up.tmp / "uvbin" / "forge").unlink()
    _install_release(up.env, RELEASE)
    up.env.checks([run("tests"), run("forge-pr-check")])
    item, where = up.env.start_fix()
    closed = up.env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    _install(repo.bin, "uv", UV_STUB.format(python=sys.executable, release=_release_shim()))
    steps = _review_job_steps(repo.git("show", f"main:{workflow}"))
    checked = _run_pr_check_job(up.env, where, steps, branch=f"fix/{item}")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert f"forge-pr-check passed for fix/{item}." in checked.stdout


def test_6_upgrade_without_a_version_uses_the_pypi_release(unsynced_up):
    up = unsynced_up
    up.repo.pypi(RELEASE[1:])
    shown = up.repo.forge("next")
    assert f"Next: forge upgrade {RELEASE}" in shown.stdout, shown.stdout + shown.stderr
    (up.repo.bin / "uv-install-fails").touch()
    done = up.run()
    assert "network is unreachable" in done.stderr + done.stdout
    assert up.uv()[0]["args"][-1] == f"symphony-forge=={RELEASE.removeprefix('v')}"
