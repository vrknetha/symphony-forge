"""Check that a wrong round gives a usable retry and a finished round gives a next step."""
import re

from test_tools_session_hold import Session
from test_workers_leave_settings_to_coordinator import client  # noqa: F401

STORY = "abb-sol-handback"


def test_1_wrong_handback_round_gives_recovery_commands(client, monkeypatch, tmp_path):
    # The closest message retry test covers empty input. It never sends the wrong
    # round or tries a finished one. Use the real commands with no new seam.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "without-claude-sdk"))
    made = client.forge("fix", "start", "Correct spelling", "--done", "Correct spelling", "--kind", "mechanical")
    assert made.returncode == 0, made.stdout + made.stderr
    host = Session(client, tmp_path / "host", "claude-session")
    try:
        given = host.forge("work", "correct-spelling")
        assert given.returncode == 0, given.stdout + given.stderr
        number = re.search(r"forge handback correct-spelling --round (\d+)", given.stdout)[1]
        wrong = host.forge("handback", "correct-spelling", "--round", str(int(number) + 1),
                           "--subagent", "builder", input="Done.")
        assert wrong.returncode == 1, wrong.stdout + wrong.stderr
        assert f"Round {number} is open." in wrong.stderr
        command = re.search(r"^Next: (forge handback .+)$", wrong.stderr, re.M)[1]
        assert command == f"forge handback correct-spelling --round {number} --subagent builder"
        retry = host.forge(*command.split()[1:], input="Done.")
        assert retry.returncode == 0, retry.stdout + retry.stderr

        finished = host.forge(*command.split()[1:], input="Done.")
        assert finished.returncode == 1, finished.stdout + finished.stderr
        assert "Next: forge next" in finished.stderr
    finally:
        host.close()
