"""Client CI, hook and pinned runner package requirements."""
from test_fix_when_the_installed_forge_differs_from_th import _calls, _uv
from test_mod_sync import _calls as _claude_calls, _claude
from test_setup import _on_a_branch_with_forge_toml, _version
from test_upgrade_command import RELEASE, env, unsynced_up  # noqa: F401
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
