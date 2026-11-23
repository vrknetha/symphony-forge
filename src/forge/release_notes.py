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
    return tuple(int(number) for number in version.removeprefix("v").split("."))


def releases() -> list[tuple[str, dict[str, list[str]]]]:
    """Each notes file up to the running release, oldest first: (v1.2.46, {heading: bullets})."""
    found = []
    for path in NOTES.glob("v*.md"):
        if _key(path.stem) <= _key(forge.__version__):
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
