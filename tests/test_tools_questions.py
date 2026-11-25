"""Code questions use the session's explorer instead of a separate Forge command."""
import shutil

import pytest

from conftest import ROOT, patient
from test_read_only_model_selection import MODELS
from test_subagent_roles import _settings, _synced

STORY = "FORGE-TOOLS-1"


@pytest.mark.parametrize("adopted", [False, True], ids=["new", "earlier-adopted"])
def test_2_questions_use_the_session_explorer_in_new_and_earlier_adopted_repos(repo, adopted):
    # forge ask came back by the owner's decision of 22 Nov 2026, so the old removal no longer holds.
    commands = repo.forge("--help").stdout.split("commands:\n", 1)[1]
    assert "    handback " in commands and "    ask " in commands

    if adopted:
        patient(lambda: shutil.copytree(ROOT / "tests/fixtures/adopted-v1.2.2/client",
                                         repo.path, dirs_exist_ok=True))
        repo.git("add", "-A")
        repo.git("commit", "-qm", "Adopt earlier Forge files")
    synced = _synced(repo, MODELS)
    assert synced.returncode == 0, synced.stdout + synced.stderr
    for host in (".codex", ".claude"):
        skill = (repo.path / host / "skills/forge/SKILL.md").read_text("utf-8")
        row = next(line for line in skill.splitlines() if '"Ask about this code"' in line)
        assert "explorer" in row
    assert _settings(repo.path, "explorer") == (
        ("gpt-6-luna", "high"), ("claude-haiku-5-5", "high"))
