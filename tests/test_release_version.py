"""The v1.2.46 release replaces v1.2.39 in current install and sync contracts."""

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


STORY = "FIX-RELEASE-1216"
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.platform
def test_1_forge_version_is_1_2_27_everywhere_it_is_recorded(repo):
    assert repo.forge("--version").stdout.split()[-1] == "v1.2.46"
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" in pyproject["project"]["dynamic"]  # pyproject reads the version from __init__
    assert tomllib.loads((ROOT / "forge.toml").read_text(encoding="utf-8"))["version"] == "v1.2.46"
    assert "FORGE_VERSION=1.2.46\n" in (ROOT / "scripts/install-mac.sh").read_text(encoding="utf-8")
    assert "$ForgeVersion = '1.2.46'" in (ROOT / "scripts/install-windows.ps1").read_text(encoding="utf-8")
    assert "symphony-forge@v1.2.46\"" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "symphony-forge@v1.2.46" in (ROOT / "docs/guide.md").read_text(encoding="utf-8")
    plugin = json.loads((ROOT / "src/forge/mod/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert plugin["version"] == "1.2.46"
    marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    entry = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == "forge")
    assert entry["version"] == "1.2.46"
    assert entry["source"]["ref"] == "v1.2.46"
    assert "symphony-forge@v1.2.46" in (ROOT / ".forge/hooks.sh").read_text(encoding="utf-8")
    assert "Forge v1.2.46" in (ROOT / ".github/workflows/forge.yml").read_text(encoding="utf-8")
    # Check the shipped lock: newer uv drops dynamic versions from its working copy.
    lock = tomllib.loads(repo.git("show", "HEAD:uv.lock", cwd=ROOT))
    assert next(package for package in lock["package"] if package["name"] == "symphony-forge")["version"] == "1.2.46"
    repo.git("checkout", "-b", "fix/release")
    repo.write("forge.toml", 'version = "v1.2.46"\ntest = "echo ok"\n')
    synced = repo.forge("sync")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    assert "symphony-forge@v1.2.46" in (repo.path / ".forge/hooks.sh").read_text(encoding="utf-8")
    assert "Forge v1.2.46" in (repo.path / ".github/workflows/forge.yml").read_text(encoding="utf-8")
    synced = repo.forge("sync")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    assert "already match Forge v1.2.46" in synced.stdout


@pytest.mark.platform
def test_2_release_checkout_generated_files_match_sync(repo):
    # Version text misses stale guidance and renderer code. Compare real sync output
    # in an isolated copy; no production seam or developer checkout mutation is needed.
    paths = repo.git("ls-files", cwd=ROOT).splitlines()
    before = {}
    for name in paths:
        source = ROOT / name
        if source.is_file():
            target = repo.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            before[name] = source.read_bytes()
    repo.git("checkout", "-qb", "fix/release-sync")
    synced = repo.forge("sync")
    assert synced.returncode == 0, synced.stdout + synced.stderr
    written = [line.removeprefix("Wrote ") for line in synced.stdout.splitlines()
               if line.startswith("Wrote ")]
    stale = [name for name in written if before.get(name) != (repo.path / name).read_bytes()]
    assert not stale, f"Run forge sync and commit its generated files: {stale}"


CHECK = ROOT / ".github/release-notes-check.py"
NOTE = "# Forge v9.9.9\n\n## What changes for client repos\n\n- A change. Nothing to do.\n"


def _check(folder, tag, commit):
    return subprocess.run([sys.executable, str(CHECK), tag, commit], cwd=folder, capture_output=True,
                          text=True, encoding="utf-8")


def test_3_the_release_ships_notes_an_agent_can_act_on(repo, tmp_path):
    version = repo.forge("--version").stdout.split()[-1].removeprefix("v")
    folder = ROOT / "src/forge/release-notes"
    assert (folder / f"v{version}.md").is_file(), f"Release v{version} has no notes file"
    earlier: set[str] = set()
    for path in sorted(folder.glob("v*.md"), key=lambda p: tuple(map(int, p.stem[1:].split(".")))):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == f"# Forge {path.stem}", path.name
        headings = [line for line in lines if line.startswith("#")][1:]
        names = ["## What changes for client repos", "## Known issues", "## Fixed known issues"]
        assert headings == [name for name in names if name in headings], (path.name, headings)
        assert headings[0] == names[0], path.name
        sections: dict[str, list[str]] = {}
        for line in lines[1:]:
            if line.startswith("##"):
                sections[line] = []
            elif line.startswith("- "):
                sections[next(reversed(sections))].append(line)
        assert sections[names[0]], f"{path.name} has no change"
        titles = [re.match(r"- \*\*(.+?)\*\*", line) for line in sections.get(names[1], [])]
        for line, title in zip(sections.get(names[1], []), titles):
            assert title and "Workaround:" in line, f"{path.name}: {line[:60]}"
        found = {title[1] for title in titles if title}
        assert not found & earlier and len(found) == len(titles), f"{path.name}: duplicate title"
        for line in sections.get(names[2], []):
            assert re.match(r"- \*\*(.+?)\*\*", line)[1] in earlier, f"{path.name}: {line[:60]}"
        earlier |= found

    # The release check, in a temporary repo whose force-include names an agent skill.
    work = tmp_path / "release"
    work.mkdir()
    for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@example.com"),
                 ("config", "user.name", "T")):
        repo.git(*args, cwd=work)

    def commit(message, files):
        for name, text in files.items():
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        repo.git("add", "-A", cwd=work)
        repo.git("commit", "-q", "-m", message, cwd=work)
        return repo.git("rev-parse", "HEAD", cwd=work)

    commit("Start", {"pyproject.toml": '[tool.hatch.build.targets.wheel.force-include]\n'
                                       '".codex/skills/x/SKILL.md" = "forge/x.md"\n',
                     "src/forge/app.py": "a\n", ".codex/skills/x/SKILL.md": "s\n"})
    notes = commit("Notes", {"src/forge/__init__.py": "v\n", "src/forge/release-notes/v9.9.9.md": NOTE})
    passed = _check(work, "v9.9.9", notes)
    assert passed.returncode == 0 and f"Release v9.9.9 notes cover {notes[:7]}." in passed.stdout, passed.stderr
    missing = _check(work, "v9.9.8", notes)
    assert missing.returncode == 1
    assert "Release v9.9.8 has no notes file src/forge/release-notes/v9.9.8.md." in missing.stdout + missing.stderr
    late = commit("Change the app", {"src/forge/app.py": "b\n"})
    refused = _check(work, "v9.9.9", late)
    assert refused.returncode == 1
    assert f"Shipped Forge files changed after the notes of v9.9.9: {late[:7]} Change the app." in (
        refused.stdout + refused.stderr)
    repo.git("reset", "-q", "--hard", notes, cwd=work)
    skill = commit("Change the skill", {".codex/skills/x/SKILL.md": "t\n"})
    skilled = _check(work, "v9.9.9", skill)
    assert skilled.returncode == 1 and "changed after the notes" in skilled.stdout + skilled.stderr
