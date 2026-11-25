"""The first worker brief points to shared guidance and keeps screen design inline."""
import re
from pathlib import Path

import pytest

from test_story import DESIGN_IMAGE, DESIGN_TREE
from test_task import DOC, story
from test_worker import calls, install_claude, referenced_standards

STORY = "FORGE-TOKENS-1"


@pytest.mark.parametrize("item,screen,command", [
    ("correct-the-retry-count", False, ("fix", "start", "Correct the retry count",
                                      "--done", "Count retries once", "--kind", "backend")),
    ("fix-the-queue-screen", True, ("fix", "start", "Fix the queue screen",
                                    "--done", "The queue screen shows the active filter")),
    ("remove-a-typo", False, ("fix", "start", "Remove a typo",
                              "--done", "The changelog uses the correct spelling", "--kind", "mechanical")),
    ("BOARD/PAGE", True, ("task", "start", "BOARD/PAGE")),
    ("BOARD/HELP", False, ("task", "start", "BOARD/HELP")),
])
def test_1_first_brief_names_reference_files(repo, gh, item, screen, command):
    log = install_claude(repo)
    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
                             'workers = "claude"\ntest = "pytest -q"\n'
                             'models.build = { model = "sonnet", effort = "medium" }\n'
                             'models.design.claude = { model = "sonnet", effort = "medium" }\n')
    design = {"PRODUCT.md": "## Board users\n\nManagers check the queue daily.",
              "DESIGN.md": "## Board colours\n\nUse navy for active work.",
              "docs/design/baskets/SCREENS.md": "## Queue\n\nShow active items first."}
    for name, content in design.items():
        repo.write(name, content + "\n")
    repo.write("docs/design/baskets/screen.svg", DESIGN_IMAGE)
    repo.git("add", "forge.toml", *design, "docs/design/baskets/screen.svg")
    repo.git("commit", "-qm", "Save the board design and settings")
    repo.git("push", "-q", "origin", "main")
    doc = DOC.replace(DESIGN_TREE, repo.git("rev-parse", "HEAD:docs/design/baskets"))
    story(repo, doc=doc, approved=doc)
    started = repo.forge(*command)
    assert started.returncode == 0, started.stdout + started.stderr
    worked = repo.forge("work", item)
    assert worked.returncode == 0, worked.stdout + worked.stderr
    brief = calls(log)[-1]["brief"]
    rules = referenced_standards(brief).read_text(encoding="utf-8")
    assert "## The 11 client-app principles" not in brief
    assert "## The 11 client-app principles" in rules
    history = Path(re.search(r"`([^`\n]*release-notes)/`", brief)[1])
    assert any(history.glob("v*.md"))
    assert "Time history keeps the first recorded start" not in brief
    for name, content in design.items():
        if not name.endswith("SCREENS.md") or item.startswith("BOARD/"):
            assert name in brief, (item, name)
            assert (content in brief) == screen, (item, name)
    assert "forge test" in brief
    if item == "BOARD/PAGE":
        assert "`web/board.py`, `web/templates/`" in brief
