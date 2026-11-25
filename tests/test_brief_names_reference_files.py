"""The first worker brief points to shared guidance and keeps screen design inline."""
import re
from pathlib import Path

from test_task import story
from test_worker import calls, install_claude

STORY = "FORGE-TOKENS-1"


def test_1_first_brief_names_reference_files(repo, gh):
    log = install_claude(repo)
    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
                             'workers = "claude"\ntest = "pytest -q"\n'
                             'models.build = { model = "sonnet", effort = "medium" }\n'
                             'models.design.claude = { model = "sonnet", effort = "medium" }\n')
    design = {"PRODUCT.md": "## Board users\n\nManagers check the queue daily.",
              "DESIGN.md": "## Board colours\n\nUse navy for active work."}
    for name, content in design.items():
        repo.write(name, content + "\n")
    repo.git("add", "forge.toml", *design)
    repo.git("commit", "-qm", "Save the board design and settings")
    repo.git("push", "-q", "origin", "main")
    story(repo)
    started = repo.forge("task", "start", "BOARD/PAGE")
    assert started.returncode == 0, started.stdout + started.stderr
    started = repo.forge("fix", "start", "Correct the retry count", "--done", "Count retries once")
    assert started.returncode == 0, started.stdout + started.stderr

    for item, screen in (("correct-the-retry-count", False), ("BOARD/PAGE", True)):
        worked = repo.forge("work", item)
        assert worked.returncode == 0, worked.stdout + worked.stderr
        brief = calls(log)[-1]["brief"]
        standards = Path(re.search(r"`([^`\n]*standards\.md)`", brief)[1])
        if not standards.is_absolute():
            standards = Path(calls(log)[-1]["cwd"]) / standards
        rules = standards.read_text(encoding="utf-8")
        assert "## The 11 client-app principles" not in brief
        assert "## The 11 client-app principles" in rules
        history = Path(re.search(r"`([^`\n]*release-notes)/`", brief)[1])
        assert any(history.glob("v*.md"))
        assert "Time history keeps the first recorded start" not in brief
        for name, content in design.items():
            assert name in brief
            assert (content in brief) == screen
        assert "forge test" in brief
        if screen:
            assert "`web/board.py`, `web/templates/`" in brief
