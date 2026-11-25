"""Release notes shipped inside Forge, and the guide's list of open known issues."""
import re
import tomllib
from pathlib import Path
from typing import Any

import forge
from forge import repo

NOTES = Path(__file__).parent / "release-notes"
TITLE = re.compile(r"^- \*\*(.+?)\*\*")
PART = ("## Known Forge issues\n\nOpen known issues in this Forge release, from its release notes. "
        "When one affects the work, tell the owner and use its workaround. An upgrade to a release "
        "that fixes an issue removes it from this list.\n\n")


def _key(version: str) -> tuple[int, ...]:
    """Numbers of vX.Y.Z; a prerelease such as v1.2.3-rc.1 comes before its release."""
    found = re.match(r"(\d+)\.(\d+)\.(\d+)(.*)", version.removeprefix("v"))
    if not found:
        raise ValueError(f"unreadable version {version!r}")
    return (*map(int, found.groups()[:3]), 0 if found[4] else 1)


def releases() -> list[tuple[str, dict[str, list[str]]]]:
    """Each notes file up to the running release, oldest first: (v1.2.46, {heading: bullets})."""
    found = []
    for path in NOTES.iterdir():  # a folder that cannot be listed raises, instead of looking empty
        if re.fullmatch(r"v\d+\.\d+\.\d+\.md", path.name) and _key(path.stem) <= _key(forge.__version__):
            sections: dict[str, list[str]] = {}
            heading = ""
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("## "):
                    heading = line[3:]
                    sections[heading] = []
                elif line.startswith("- ") and heading:
                    sections[heading].append(line)
            found.append((path.stem, sections))
    return sorted(found, key=lambda release: _key(release[0]))


def open_issues(upto: str) -> list[str]:
    """The known-issue bullets up to a release that no later release up to it fixes."""
    notes = [(version, sections) for version, sections in releases() if _key(version) <= _key(upto)]
    fixed = {TITLE.match(bullet)[1]  # pyright: ignore[reportOptionalSubscript]
             for _, sections in notes for bullet in sections.get("Fixed known issues", [])}
    return [f"{bullet} (Since {version}.)" for version, sections in notes
            for bullet in sections.get("Known issues", [])
            if TITLE.match(bullet)[1] not in fixed]  # pyright: ignore[reportOptionalSubscript]


def ships(top: Path, cfg: dict[str, Any]) -> dict[str, str]:
    """Both guide copies: the template, then the open known issues of this release."""
    skill = (Path(__file__).parent / "templates/skill.md").read_text(encoding="utf-8")
    issues = "\n".join(open_issues(forge.__version__)) or "This Forge release has no open known issues."
    text = skill.rstrip("\n") + "\n\n" + PART + issues + "\n"
    return {".claude/skills/forge/SKILL.md": text, ".codex/skills/forge/SKILL.md": text}


def check(top: Path, tag: str, commit: str) -> str:
    """Why a release cut at commit cannot be tagged, or "" when its notes cover the shipped files."""
    notes = f"src/forge/release-notes/{tag}.md"
    if repo.run("git", "cat-file", "-e", f"{commit}:{notes}", cwd=top).returncode:
        return f"Release {tag} has no notes file {notes}."
    shown = repo.run("git", "show", f"{commit}:pyproject.toml", cwd=top)
    wheel = (tomllib.loads(shown.stdout)["tool"]["hatch"]["build"]["targets"]["wheel"]
             if shown.returncode == 0 else {})
    shipped = ["src/forge", "pyproject.toml", "scripts/install-mac.sh", "scripts/install-windows.ps1",
               *wheel.get("force-include", {})]
    last = repo.git("log", "-1", "--format=%H", commit, "--", *shipped, cwd=top)
    if last and repo.git("log", "-1", "--format=%H", last, "--", notes, cwd=top) != last:
        return (f"Shipped Forge files changed after the notes of {tag}: {last[:7]} "
                f"{repo.git('log', '-1', '--format=%s', last, cwd=top)}. "
                "Add it to the notes, then run this check again.")
    return ""


def changes(old: str, new: str) -> list[str]:
    """What each release after old, up to new, changed, then the issues still open in new."""
    found = [(version, sections) for version, sections in releases() if _key(old) < _key(version) <= _key(new)]
    if not found:
        return []
    lines = [f"Forge changed from v{old.removeprefix('v')} to v{new.removeprefix('v')}. Tell the owner what "
             "changed, in plain words, and work the new way:"]
    for version, sections in found:
        lines += [f"Forge {version}:", *sections.get("What changes for client repos", []),
                  *(f"- Fixed known issue: {TITLE.match(bullet)[1]}"  # pyright: ignore[reportOptionalSubscript]
                    for bullet in sections.get("Fixed known issues", []))]
    issues = open_issues(new)
    return lines + ([f"Open known Forge issues in v{new.removeprefix('v')}, with what to do:", *issues]
                    if issues else [])


def upgrade_notice(top: Path, cfg: dict[str, Any]) -> None:
    """Print the changes between the default branch's pin and this release's pin. Writes nothing."""
    try:
        old = repo._pin(repo.read_blob(top, f"origin/{repo.default_branch(top)}:forge.toml") or "")
        new = str(cfg["version"])
        if old and _key(new) > _key(old) and (lines := changes(old, new)):
            print("\n".join(lines))
    except (OSError, ValueError):
        pass


def _marker(top: Path) -> Path:
    return repo.forge_dir(top) / "release-notes-shown"


def once(top: Path) -> tuple[list[str], str | None]:
    """The change list this clone has not shown yet, and the version to mark once it is printed."""
    from forge import story

    try:
        pins = [repo._pin((path / "forge.toml").read_text(encoding="utf-8"))
                for path in {top, *story.worktrees(top).values()} if (path / "forge.toml").is_file()]
        known = [pin for pin in pins if pin and _key(pin) <= _key(forge.__version__)]
        if not known:
            return [], None
        target = max(known, key=_key)
        remote = repo._pin(repo.read_blob(top, f"origin/{repo.default_branch(top)}:forge.toml") or "")
        shown = _marker(top).read_text(encoding="utf-8").strip() if _marker(top).is_file() else ""
        if remote and _key(remote) < _key(target) and (not shown or _key(remote) > _key(shown)):
            base = remote  # the range that sync prints for a pending upgrade
        elif shown:
            base = shown
        else:
            current = top / "forge.toml"
            texts = [current.read_text(encoding="utf-8") if current.is_file() else "", *(
                repo.read_blob(top, f"{sha}:forge.toml") or "" for sha in repo.git(
                    "log", "-n", "200", "--format=%H", "--", "forge.toml", cwd=top).split())]
            older = [pin for pin in map(repo._pin, texts) if pin and _key(pin) < _key(target)]
            if not older:
                return [], target
            base = max(older, key=_key)
        if _key(target) <= _key(base):
            return [], None
        if _key(target) >= _key("1.2.40") and not (NOTES / f"v{target}.md").is_file():
            raise FileNotFoundError(f"no notes file for v{target}")
        return changes(base, target), target
    except (OSError, ValueError, repo.Refused) as error:
        first = (str(error).splitlines() or [type(error).__name__])[0]
        return [f"Forge could not read its release notes ({first})."], None


def mark(top: Path, version: str) -> None:
    try:
        _marker(top).write_text(version + "\n", encoding="utf-8")
    except OSError:
        pass
