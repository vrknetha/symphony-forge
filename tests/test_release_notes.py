"""Release notes ship inside Forge: the tag push needs them, and the guide lists open issues.

Test-audit: the pre-push hook and `forge init` / `forge sync` are the real entry points. Only
GitHub is faked. The guide case installs a copy of Forge with its own notes files.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FORGE_SHIM, ROOT, _install
from test_setup import _fresh_client
from test_testplace_fullrun import _set_status
from test_close import env  # noqa: F401
from test_upgrade_command import RELEASE, unsynced_up, up  # noqa: F401

STORY = "FORGE-RELNOTES-1"
pytestmark = pytest.mark.platform
NOTE = "# Forge v9.9.9\n\n## What changes for client repos\n\n- A change. Nothing to do.\n"
PART = "## Known Forge issues"


def test_1_the_release_tag_push_needs_notes_that_cover_the_shipped_files(repo, gh):
    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n')
    repo.write("pyproject.toml", "[tool.hatch.build.targets.wheel.force-include]\n")
    repo.write("src/forge/app.py", "a\n")

    def pushed(message):
        repo.git("add", "-A")
        repo.git("commit", "-q", "-m", message)
        repo.git("push", "-q", "origin", "main")
        sha = repo.git("rev-parse", "HEAD")
        _set_status(gh, sha, "success")
        return repo.forge("hook", "pre-push", input=f"refs/tags/v9.9.9 {sha} refs/tags/v9.9.9 {'0' * 40}\n")

    refused = pushed("Release without notes")
    assert refused.returncode != 0
    assert "Release v9.9.9 has no notes file src/forge/release-notes/v9.9.9.md." in refused.stderr
    repo.write("src/forge/release-notes/v9.9.9.md", NOTE)
    accepted = pushed("Add the notes")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    repo.write("src/forge/app.py", "b\n")
    late = pushed("Change the app")
    assert late.returncode != 0
    assert "Shipped Forge files changed after the notes of v9.9.9" in late.stderr
    # A client repo never runs a file from its checkout, and needs no notes.
    repo.write("forge.toml", f'version = "{version}"\n')
    repo.write(".github/release-notes-check.py", "open('ran', 'w').close()\n")
    client = pushed("A client with a planted script")
    assert client.returncode == 0, client.stderr
    assert not (repo.path / "ran").exists()


def test_4_the_guide_lists_open_issues_and_drops_fixed_ones(repo, gh, tmp_path):
    # A copy of the checkout's Forge, with the skills that sync reads from the checkout root.
    source = tmp_path / "source"
    for name in ("src/forge", ".claude", ".codex"):
        shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns("__pycache__"))
    _install(repo.bin, "forge", FORGE_SHIM.format(python=sys.executable, src=str(source / "src")))
    package = source / "src/forge"
    (package / "__init__.py").write_text('__version__ = "9.9.8"\n', encoding="utf-8")
    notes = package / "release-notes"
    (notes / "v9.9.8.md").write_text(
        NOTE.replace("9.9.9", "9.9.8") + "\n## Known issues\n\n- **Test issue one.** It breaks. "
        "Workaround: run the check again.\n", encoding="utf-8")

    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    guides = [client / ".claude/skills/forge/SKILL.md", client / ".codex/skills/forge/SKILL.md"]
    for guide in guides:
        part = guide.read_text(encoding="utf-8").split(PART)[-1]
        assert "**Test issue one.** It breaks. Workaround: run the check again. (Since v9.9.8.)" in part

    (package / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
    (notes / "v9.9.9.md").write_text(
        NOTE + "\n## Known issues\n\n- **Test issue two.** It breaks. Workaround: wait.\n"
        "\n## Fixed known issues\n\n- **Test issue one.**\n", encoding="utf-8")
    repo.git("switch", "-q", "-c", "fix/notes", cwd=client)
    toml = (client / "forge.toml").read_text(encoding="utf-8")
    (client / "forge.toml").write_text(toml.replace('version = "v9.9.8"', 'version = "v9.9.9"'),
                                       encoding="utf-8")
    synced = repo.forge("sync", cwd=client)
    assert synced.returncode == 0, synced.stdout + synced.stderr
    for guide in guides:
        part = guide.read_text(encoding="utf-8").split(PART)[-1]
        assert "**Test issue two.**" in part and "Test issue one" not in part


HEAD = "Forge changed from v1.2.44 to v9.9.9."
ISSUE_TWO = "- **Test issue two.** It waits. Workaround: none; it ends in a minute. (Since v9.9.9.)"
LIST = ["Forge v9.9.8:", "- Test change eight.", "Forge v9.9.9:", "- Test change nine.",
        "- Fixed known issue: Test issue one", ISSUE_TWO]


def _pin(version):
    return lambda toml: re.sub(r'^version = ".*"', f'version = "{version}"', toml, count=1, flags=re.M)


def _with_notes(up, stale=False):
    """Two newer releases than the pin, and a pin that the upgrade must start from."""
    folder = up.repo.bin / "extra-notes"
    folder.mkdir()
    (folder / "v9.9.8.md").write_text(
        "# Forge v9.9.8\n\n## What changes for client repos\n\n- Test change eight.\n\n"
        "## Known issues\n\n- **Test issue one.** It fails. Workaround: run it again.\n", encoding="utf-8")
    (folder / "v9.9.9.md").write_text(
        "# Forge v9.9.9\n\n## What changes for client repos\n\n- Test change nine.\n\n"
        "## Known issues\n\n- **Test issue two.** It waits. Workaround: none; it ends in a minute.\n\n"
        "## Fixed known issues\n\n- **Test issue one.**\n", encoding="utf-8")
    up.on_main("forge.toml", _pin("v1.2.44")(up.toml()))
    if stale:  # The remote moved to v1.2.46; this checkout has not pulled it.
        up.on_main("forge.toml", _pin("v1.2.46")(up.toml()))
        up.repo.git("reset", "-q", "--hard", "HEAD~1")


def _in_order(text, parts):
    at = 0
    for part in parts:
        found = text.find(part, at)
        assert found >= 0, f"{part!r} missing or out of order in:\n{text}"
        at = found + len(part)


OPEN = "Open known Forge issues in v9.9.9, with what to do:"


def _bullets(version):
    text = (ROOT / f"src/forge/release-notes/{version}.md").read_text(encoding="utf-8")
    part = text.split("## What changes for client repos")[1].split("\n## ")[0]
    return [line for line in part.splitlines() if line.startswith("- ")]


@pytest.mark.parametrize("case", ["current", "stale-starting-checkout", "prerelease"])
def test_2_upgrade_lists_the_changes_of_every_release_between(up, case):
    _with_notes(up, stale=case == "stale-starting-checkout")
    if case == "prerelease":  # v9.9.9-rc.1 comes before v9.9.9, and after v9.9.8
        up.on_main("forge.toml", _pin("v9.9.9-rc.1")(up.toml()))
    done = up.run(RELEASE)
    assert done.returncode == 0, done.stdout + done.stderr
    text = done.stdout
    if case == "current":
        _in_order(text, [HEAD, "Forge v1.2.45:", *_bullets("v1.2.45"), "Forge v1.2.46:", *_bullets("v1.2.46"),
                         *LIST[:-1], OPEN, ISSUE_TWO])
        assert "Forge v1.2.44:" not in text
    elif case == "stale-starting-checkout":
        # Sync starts at the remote's pin (v1.2.46), as the upgrade branch does.
        _in_order(text, ["Forge changed from v1.2.46 to v9.9.9.", *LIST[:-1], OPEN, ISSUE_TWO])
        assert "Forge v1.2.45:" not in text and "Forge v1.2.46:" not in text
    else:
        _in_order(text, ["Forge changed from v9.9.9-rc.1 to v9.9.9.", "Forge v9.9.9:", "- Test change nine.",
                         "- Fixed known issue: Test issue one", OPEN, ISSUE_TWO])
        assert "Forge v9.9.8:" not in text
    assert "Test issue one.** It fails" not in text.split(OPEN)[-1]


def _next(up, cwd, installed=True):
    if installed:
        done = subprocess.run([sys.executable, str(up.tmp / "uvbin" / "forge"), "next"], cwd=cwd,
                              capture_output=True, text=True, encoding="utf-8", timeout=120)
    else:
        done = up.repo.forge("next", cwd=cwd)
    assert done.returncode == 0, done.stdout + done.stderr
    return done


def _shows(done):
    return all(line in done.stdout for line in LIST)


def _repeats(first, second):
    """A line of the change list that the first run printed (header through the last open issue) shows again."""
    lines = first.stdout.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Forge changed from"))
    end = max(i for i, line in enumerate(lines) if "(Since v" in line)
    return bool(set(lines[start:end + 1]) & set(second.stdout.splitlines())) or "Forge could not read" in second.stdout


@pytest.mark.parametrize("case", ["starting-checkout", "stale-starting-checkout", "older-release-first",
                                  "new-clone", "new-repo", "stale-marker", "no-forge-toml",
                                  "unreadable-notes", "missing-notes"])
def test_3_next_shows_the_changes_once_after_an_upgrade(case, request, tmp_path):
    if case == "new-repo":
        repo, gh = request.getfixturevalue("repo"), request.getfixturevalue("gh")
        client, initialized = _fresh_client(repo, gh, tmp_path)
        assert initialized.returncode == 0, initialized.stdout + initialized.stderr
        for _ in range(2):
            done = repo.forge("next", cwd=client)
            assert done.returncode == 0 and "Forge changed from" not in done.stdout
        return
    up = request.getfixturevalue("up")
    _with_notes(up, stale=case == "stale-starting-checkout")
    assert up.run(RELEASE).returncode == 0
    if case in ("starting-checkout", "stale-starting-checkout"):
        done = _next(up, up.repo.path)
        assert _shows(done)
        assert ("Forge v1.2.45:" in done.stdout) == (case == "starting-checkout")
        assert f"Forge changed from v1.2.4{'4' if case == 'starting-checkout' else '6'} to" in done.stdout
        assert not _repeats(done, _next(up, up.repo.path))
    elif case == "older-release-first":
        assert "Forge changed from" not in _next(up, up.folder, installed=False).stdout
        done = _next(up, up.folder)
        assert _shows(done) and not _repeats(done, _next(up, up.folder))
    elif case == "new-clone":
        up.on_main("forge.toml", _pin("v9.9.9")(up.toml()))
        clone = tmp_path / "clone"
        subprocess.run(["git", "clone", "-q", up.repo.git("remote", "get-url", "origin"), str(clone)],
                       check=True)
        done = _next(up, clone)
        assert _shows(done) and not _repeats(done, _next(up, clone))
    elif case == "stale-marker":
        # This clone showed v9.9.7; the remote moved to v9.9.8; the upgrade goes from v9.9.8 to v9.9.9.
        up.on_main("forge.toml", _pin("v9.9.8")(up.toml()))
        marker = Path(up.repo.git("rev-parse", "--path-format=absolute", "--git-common-dir")) / "forge"
        (marker / "release-notes-shown").write_text("9.9.7\n", encoding="utf-8")
        done = _next(up, up.repo.path)
        assert "Forge v9.9.9:" in done.stdout and "Forge v9.9.8:" not in done.stdout
        assert "Forge changed from v9.9.8 to v9.9.9." in done.stdout
    elif case == "no-forge-toml":
        # A starting checkout that has no forge.toml yet, beside the upgrade's folder that has one.
        (up.repo.path / "forge.toml").unlink()
        assert "Forge could not read" not in _next(up, up.repo.path).stdout
    else:
        note = up.tmp / "releases" / RELEASE / "src/forge/release-notes" / f"{RELEASE}.md"
        good = note.read_bytes()
        if case == "unreadable-notes":
            note.write_bytes(b"\xff\xfe not utf-8")
        else:
            note.unlink()
        failed = _next(up, up.folder)
        assert failed.stdout.count("Forge could not read its release notes") == 1
        assert "Next:" in failed.stdout
        note.write_bytes(good)
        assert _shows(_next(up, up.folder))
