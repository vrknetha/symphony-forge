"""The real next command offers releases without upgrading, and shares daily checks across trees.

The harness fakes GitHub setup and the PyPI release lookup.
Removing the notice, its deadline, or its shared daily cache breaks this command contract.
"""
import shutil
import tomllib

import pytest

from conftest import ROOT
from test_setup import _fresh_client, _version

STORY = "client-repos-never-learn-that-a-newer-fo"


@pytest.mark.parametrize("adoption", ["new", "previous release"])
def test_1_next_announces_new_releases_with_a_shared_daily_cache(repo, gh, tmp_path,
                                                               monkeypatch, adoption):
    if adoption == "new":
        client, made = _fresh_client(repo, gh, tmp_path)
    else:
        # Build an actual earlier adoption from text, then run this release's upgrade sync.
        shutil.copytree(ROOT / "tests/fixtures/adopted-v1.2.2/client", repo.path,
                        dirs_exist_ok=True)
        repo.git("switch", "-q", "-c", "fix/upgrade-client")
        config = (repo.path / "forge.toml").read_text("utf-8")
        repo.write("forge.toml", config.replace('version = "v1.2.2"',
                                               f'version = "{_version(repo)}"'))
        client, made = repo.path, repo.forge("sync")
    assert made.returncode == 0, made.stdout + made.stderr
    pin = tomllib.loads((client / "forge.toml").read_text("utf-8"))["version"]
    before = repo.git("status", "--porcelain", cwd=client)
    monkeypatch.setenv("FORGE_NOW", "2030-01-01T10:00:00+00:00")
    repo.pypi("99.10.0")
    notice = f"Forge v99.10.0 is out (you pin {pin}): forge upgrade v99.10.0"

    # A release announcement formerly replaced the machine state line. Both new
    # and earlier-adopted clients must receive the actual next state instead.
    first = repo.forge("next", cwd=client)
    assert first.returncode == 0, first.stderr
    assert first.stdout.splitlines().count(notice) == 1
    # The release line must not hide the current work state or its next step.
    lines = first.stdout.splitlines()
    assert "No story or fix is in progress." in lines
    assert 'Next: forge start "<idea>"' in lines
    assert repo.git("status", "--porcelain", cwd=client) == before
    assert repo.pypi_calls() == [3]

    tree = tmp_path / "another worktree with spaces"
    repo.git("worktree", "add", "-q", "-b", "fix/another", str(tree), cwd=client)
    (tree / "forge.toml").write_text(f'version = "{pin}"\n', encoding="utf-8")
    repo.pypi(404)
    again = repo.forge("next", cwd=tree)
    assert again.returncode == 0, again.stderr
    assert again.stdout.splitlines().count(notice) == 1
    assert repo.pypi_calls() == [3]

    # Failed attempts are also cached; a recovered network waits until the following day.
    monkeypatch.setenv("FORGE_NOW", "2030-01-02T10:00:00+00:00")
    failed = repo.forge("next", cwd=client)
    assert failed.returncode == 0, failed.stderr
    assert " is out (you pin " not in failed.stdout + failed.stderr
    repo.pypi("99.10.0")
    cached_failure = repo.forge("next", cwd=tree)
    assert cached_failure.returncode == 0, cached_failure.stderr
    assert " is out (you pin " not in cached_failure.stdout
    assert repo.pypi_calls() == [3] * 2

    for day, tag in ((3, "v99.10.0"), (4, pin), (5, "v0.0.1"), (6, "not a release")):
        monkeypatch.setenv("FORGE_NOW", f"2030-01-{day:02}T10:00:00+00:00")
        repo.pypi(tag.removeprefix("v"))
        checked = repo.forge("next", cwd=client)
        assert checked.returncode == 0, checked.stderr
        assert (" is out (you pin " in checked.stdout) == (day == 3)

    # Verify the deadline sent to PyPI and the handling of a transport timeout.
    repo.pypi("timeout")
    cached = repo.forge("next", cwd=client)
    assert cached.returncode == 0, cached.stderr
    assert repo.pypi_calls() == [3] * 6
    monkeypatch.setenv("FORGE_NOW", "2030-01-07T10:00:00+00:00")
    timed_out = repo.forge("next", cwd=client)
    assert timed_out.returncode == 0, timed_out.stderr
    assert " is out (you pin " not in timed_out.stdout + timed_out.stderr
    assert repo.pypi_calls() == [3] * 7

    cached_timeout = repo.forge("next", cwd=tree)
    assert cached_timeout.returncode == 0, cached_timeout.stderr
    assert " is out (you pin " not in cached_timeout.stdout + cached_timeout.stderr
    assert repo.pypi_calls() == [3] * 7

    # Both hosts receive the owner decision rule via init and upgrade sync.
    for host in (".codex", ".claude"):
        skill = (client / host / "skills/forge/SKILL.md").read_text("utf-8")
        assert "offer the upgrade to the owner" in skill
        assert "Never upgrade without the owner's agreement" in skill
