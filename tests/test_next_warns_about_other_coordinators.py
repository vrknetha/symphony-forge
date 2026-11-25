"""Forge next names live coordinators for the same repository."""
import json
from contextlib import ExitStack

import pytest

from test_tools_session_hold import Session

STORY = "warn-second-coordinator"
pytestmark = pytest.mark.platform


@pytest.mark.parametrize("case", ["linked", "claude", "clones", "shared-daemon", "native-worker"])
def test_1_next_names_the_other_live_coordinator(repo, gh, monkeypatch, tmp_path, case):
    # Extend the same command proof with host lifecycle events and real Git checkouts.
    # The host supplies only the events and environment a real shell would receive.
    peer = tmp_path / "peer checkout"
    if case == "clones":
        repo.git("clone", "-q", repo.git("remote", "get-url", "origin"), str(peer))
    else:
        repo.git("worktree", "add", "-qb", "linked", str(peer))
    tool = "claude" if case == "claude" else "codex"

    def command(session, cwd, *args, **kwargs):
        result = session.forge(*args, cwd=cwd, **kwargs)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def chat(name):
        if tool == "claude":
            monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
            monkeypatch.setenv("CLAUDECODE", "1")
            monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
            monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", name)
        else:
            monkeypatch.setenv("CODEX_THREAD_ID", name)

    def host_hook(session, cwd, event, name):
        payload = {"session_id": name, "cwd": cwd.as_posix(), "hook_event_name": event}
        if event == "SessionStart":
            payload["source"] = "startup"
        command(session, cwd, "hook", "context", input=json.dumps(payload))

    with ExitStack() as sessions:
        first = Session(repo, tmp_path / "first", f"{tool}-first")
        sessions.callback(first.close)
        second = first
        if case not in ("shared-daemon", "native-worker"):
            second = Session(repo, tmp_path / "second", f"{tool}-second")
            sessions.callback(second.close)

        chat("first-chat")
        host_hook(first, repo.path, "SessionStart", "first-chat")
        assert "also coordinates this repo" not in command(first, repo.path, "next")
        if case == "native-worker":
            chat("worker-thread")
            # Codex sends its main-session start event only for a root thread.
            command(first, peer, "next")
            chat("first-chat")
            assert "also coordinates this repo" not in command(first, repo.path, "next")
            return

        chat("second-chat")
        host_hook(second, peer, "SessionStart", "second-chat")
        app = "Claude Code" if tool == "claude" else "Codex"
        warning = f"{app} session first-chat also coordinates this repo."
        assert warning in command(second, peer, "next")
        if case == "shared-daemon":
            host_hook(first, repo.path, "SessionEnd", "first-chat")
        else:
            first.close()
        assert "also coordinates this repo" not in command(second, peer, "next")
