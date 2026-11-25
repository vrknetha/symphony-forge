"""Finished worktree cleanup through the public commands in FORGE-TIDYUP-1."""
import json

import pytest

from test_doctor_fix import _client, _gone, _kept, _prs, _work
from test_tools_session_hold import Session

STORY = "FORGE-TIDYUP-1"


@pytest.mark.platform
@pytest.mark.parametrize("command", ["next", "land", "start", "next with an older pin"])
def test_1_commands_remove_finished_folders(repo, gh, tmp_path, monkeypatch, command):
    _client(repo)
    clean, head = _work(repo, tmp_path, "fix/clean")
    dirty, dirty_head = _work(repo, tmp_path, "fix/dirty")
    current, current_head = _work(repo, tmp_path, "fix/current")
    (dirty / "notes.txt").write_text("Keep these notes.\n", encoding="utf-8")
    _prs(gh, ("fix/clean", head, "MERGED"), ("fix/dirty", dirty_head, "MERGED"),
         ("fix/current", current_head, "MERGED"))

    if command == "next with an older pin":
        (current / "forge.toml").write_text('version = "v1.0.0"\n', encoding="utf-8")
        done = repo.forge("next", cwd=current)
        assert "Removed " not in done.stdout and not gh.calls("pr", "list", "--state", "all")
        assert _kept(repo, clean, "fix/clean")
        return
    if command == "start":
        monkeypatch.delenv("CLAUDECODE", raising=False)
        monkeypatch.setenv("CODEX_THREAD_ID", "tidy-coordinator")
        owner = Session(repo, tmp_path / "tidy-host", "codex-tidy")
        try:
            done = owner.forge("start", "Make the greeting shorter", cwd=current)
        finally:
            owner.close()
        assert done.returncode == 0, done.stdout + done.stderr
        assert json.loads(done.stdout)["role"] == "explorer"
        output = done.stderr
    else:
        args = ("land", "--all") if command == "land" else ("next",)
        done = repo.forge(*args, cwd=current)
        output = done.stdout

    assert "Removed 1 finished folders." in output, done.stdout + done.stderr
    assert _gone(repo, clean, "fix/clean")
    assert _kept(repo, dirty, "fix/dirty")
    assert _kept(repo, current, "fix/current")
    assert len(gh.calls("pr", "list", "--state", "all")) == 1


def test_2_closed_folders_need_the_same_remote_head(repo, gh, tmp_path):
    _client(repo)
    kept, kept_head = _work(repo, tmp_path, "fix/no-remote")
    clean, head = _work(repo, tmp_path, "fix/on-remote")
    different, different_head = _work(repo, tmp_path, "fix/different-remote")
    repo.git("push", "-q", "origin", "fix/on-remote", "fix/no-remote", "main:fix/different-remote")
    repo.git("push", "-q", "origin", "--delete", "fix/no-remote")
    _prs(gh, ("fix/no-remote", kept_head, "CLOSED"), ("fix/on-remote", head, "CLOSED"),
         ("fix/different-remote", different_head, "CLOSED"))

    done = repo.forge("next")

    assert "Removed 1 finished folders." in done.stdout, done.stdout + done.stderr
    assert _kept(repo, kept, "fix/no-remote")
    assert _kept(repo, different, "fix/different-remote")
    assert _gone(repo, clean, "fix/on-remote")
