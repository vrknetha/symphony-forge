"""Recover a handback according to who holds the current round."""
import re

import pytest

from test_tools_session_hold import Session
from test_workers_leave_settings_to_coordinator import client  # noqa: F401

STORY = "abb-sol-handback"


@pytest.mark.parametrize("hold", ["same-session", "other-session", "ended-session"])
def test_1_wrong_handback_round_gives_recovery_commands(client, monkeypatch, tmp_path, hold):
    # A typo in one handout cannot expose an old subagent ID or a dead session's
    # pending record. Create both with real commands and process exits.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "without-claude-sdk"))
    made = client.forge("fix", "start", "Correct spelling", "--done", "Correct spelling", "--kind", "mechanical")
    assert made.returncode == 0, made.stdout + made.stderr
    host = Session(client, tmp_path / "host", "claude-session")
    other = None
    try:
        given = host.forge("work", "correct-spelling")
        assert given.returncode == 0, given.stdout + given.stderr
        number = re.search(r"forge handback correct-spelling --round (\d+)", given.stdout)[1]
        if hold != "same-session":
            other = Session(client, tmp_path / "other", "claude-session")
        if hold == "ended-session":
            host.close()
            wrong = other.forge("handback", "correct-spelling", "--round", str(int(number) + 1),
                                "--subagent", "old-builder", input="Old result.")
            assert wrong.returncode == 1, wrong.stdout + wrong.stderr
            assert "There is no open round for this target." in wrong.stderr
            assert "Next: forge next" in wrong.stderr
            assert "forge handback" not in wrong.stderr
            return

        stopped = host.forge("stop", "correct-spelling")
        assert stopped.returncode == 0, stopped.stdout + stopped.stderr
        assert "Stopped Forge's hold" in stopped.stdout
        replacement = (other or host).forge("work", "correct-spelling")
        assert replacement.returncode == 0, replacement.stdout + replacement.stderr
        current = re.search(r"forge handback correct-spelling --round (\d+)", replacement.stdout)[1]
        assert int(current) > int(number)

        wrong = host.forge("handback", "correct-spelling", "--round", number,
                           "--subagent", "old-builder", input="Old result.")
        assert wrong.returncode == 1, wrong.stdout + wrong.stderr
        if other:
            assert f"Round {current} is open in another session." in wrong.stderr
            assert "Hand it back from that session." in wrong.stderr
            assert "forge handback" not in wrong.stderr
            returned = other.forge("handback", "correct-spelling", "--round", current,
                                   "--subagent", "replacement-builder", input="Done.")
            assert returned.returncode == 0, returned.stdout + returned.stderr
            return

        assert f"Round {current} is open." in wrong.stderr
        assert "old-builder" not in wrong.stderr
        command = re.search(r'^Next: (forge handback .+) "<id>"$', wrong.stderr, re.M)[1]
        assert command == f"forge handback correct-spelling --round {current} --subagent"
        args = (*command.split()[1:], "replacement-builder")
        retry = host.forge(*args, input="Done.")
        assert retry.returncode == 0, retry.stdout + retry.stderr

        finished = host.forge(*args, input="Done.")
        assert finished.returncode == 1, finished.stdout + finished.stderr
        assert "Next: forge next" in finished.stderr
    finally:
        host.close()
        if other:
            other.close()
