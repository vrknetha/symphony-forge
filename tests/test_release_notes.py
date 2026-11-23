"""Release notes ship inside Forge: the tag push needs them, and the guide lists open issues.

Test-audit: the pre-push hook and `forge init` / `forge sync` are the real entry points. Only
GitHub is faked. The guide case installs a copy of Forge with its own notes files.
"""
import shutil
import sys

import pytest

from conftest import FORGE_SHIM, ROOT, _install
from test_setup import _fresh_client
from test_testplace_fullrun import _set_status

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
