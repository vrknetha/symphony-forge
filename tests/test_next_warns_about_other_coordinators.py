"""A second Forge coordinator sees the active session in a linked checkout."""
from contextlib import ExitStack

import pytest

from test_tools_session_hold import Session

STORY = "warn-second-coordinator"
pytestmark = pytest.mark.platform


def test_1_next_names_the_other_live_coordinator(repo, gh, monkeypatch, tmp_path):
    # Real host processes and linked Git worktrees own the warning. The native
    # session hold test checks worker admission, which needs no second-chat warning.
    monkeypatch.delenv("CLAUDECODE", raising=False)
    worktree = tmp_path / "linked checkout"
    repo.git("worktree", "add", "-qb", "linked", str(worktree))

    def next_output(session, cwd=None):
        result = session.forge("next", cwd=cwd)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    with ExitStack() as sessions:
        first = Session(repo, tmp_path / "first", "codex-first")
        sessions.callback(first.close)
        second = Session(repo, tmp_path / "second", "codex-second")
        sessions.callback(second.close)

        monkeypatch.setenv("CODEX_THREAD_ID", "first-chat")
        assert "also coordinates this repo" not in next_output(first)
        monkeypatch.setenv("CODEX_THREAD_ID", "second-chat")
        warning = "Codex session first-chat also coordinates this repo."
        assert warning in next_output(second, worktree)
        first.close()
        assert "also coordinates this repo" not in next_output(second, worktree)
