"""Client CI, hook and pinned runner package requirements."""
import sys

from conftest import ROOT, _install
from test_fix_when_the_installed_forge_differs_from_th import _calls, _uv
from test_mod_sync import _calls as _claude_calls, _claude
from test_setup import _on_a_branch_with_forge_toml, _version
from test_upgrade_check import BASH, UV_STUB, _release_shim, _review_job_steps, _run_pr_check_job
from test_upgrade_command import NAME, RELEASE, env, unsynced_up  # noqa: F401
from test_upgrade_pending import OLD, _pin_old

STORY = "FIX-FORGE-INSTALLS-FROM-PYPI"


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
def test_5_upgrade_stops_until_the_trusted_workflow_uses_pypi(unsynced_up):
    up = unsynced_up
    repo = up.repo
    workflow = ".github/workflows/forge.yml"
    up.on_main("forge.toml", 'version = "v1.2.2"\n')
    up.on_main(workflow, (ROOT / "tests/fixtures/doctor-v1.2.2" / workflow).read_text("utf-8"))
    before = up.snapshot()

    refused = up.run(RELEASE)
    assert refused.returncode == 1
    assert "default branch still installs Forge from the retired GitHub repository" in refused.stderr
    assert "recovering-upgrades-from-the-retired-github-repository" in refused.stderr
    assert up.snapshot() == before

    # The owner repairs the trusted workflow first. This repo's old pin has no PyPI package.
    text = (repo.path / workflow).read_text("utf-8")
    up.on_main(workflow, text.replace("git+https://github.com/knacklabs/symphony-forge@v",
                                      "symphony-forge=="))
    done = up.run(RELEASE)
    assert done.returncode == 0, done.stdout + done.stderr
    assert up.uv()[0]["args"][-1] == f"symphony-forge=={RELEASE.removeprefix('v')}"
    assert up.uv()[-1]["args"][5:] == ["close", NAME]

    # The runner checks out the trusted base, including its old pin. Execute that workflow's
    # shell steps to verify it installs the new pin and really runs the new release's check.
    (up.tmp / "uvbin" / "forge").unlink()
    _install(repo.bin, "uv", UV_STUB.format(python=sys.executable, release=_release_shim()))
    steps = _review_job_steps(repo.git("show", f"main:{workflow}"))
    checked = _run_pr_check_job(up.env, up.folder, steps, branch=f"fix/{NAME}")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert f"forge-pr-check passed for fix/{NAME}." in checked.stdout


def test_6_upgrade_without_a_version_uses_the_pypi_release(unsynced_up):
    up = unsynced_up
    up.repo.pypi(RELEASE[1:])
    shown = up.repo.forge("next")
    assert f"Next: forge upgrade {RELEASE}" in shown.stdout, shown.stdout + shown.stderr
    (up.repo.bin / "uv-install-fails").touch()
    done = up.run()
    assert "network is unreachable" in done.stderr + done.stdout
    assert up.uv()[0]["args"][-1] == f"symphony-forge=={RELEASE.removeprefix('v')}"
