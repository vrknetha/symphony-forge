"""Fresh coordinator chats find the shared note through the session context command."""

STORY = "FORGE-CHATHANDOVER-1"


def test_3_context_hook_names_handoff_note(repo, tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_NOW", "2026-11-26T12:00:00+00:00")
    monkeypatch.delenv("FORGE_WORKER", raising=False)
    worktree = tmp_path / "task"
    repo.git("worktree", "add", "-b", "task/CHAT-1-HANDOVER", str(worktree))

    def context():
        result = repo.forge("hook", "context", cwd=worktree)
        assert result.returncode == 0, result.stderr
        return result.stdout

    assert "Read the handoff note" not in context()
    handoff = repo.forge("hook", "handoff")
    assert handoff.returncode == 0, handoff.stderr
    note = (repo.path / ".git" / "forge" / "handoff.md").resolve().as_posix()
    assert f"Read the handoff note {note} from 2026-11-26 first, then run forge next." in context()
    monkeypatch.setenv("FORGE_WORKER", "1")
    assert "Read the handoff note" not in context()
