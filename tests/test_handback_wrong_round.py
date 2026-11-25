"""Handback with a wrong round names the open round and command; with no open round it gives the next step."""
import json

import pytest

from test_lanes_agents import person  # noqa: F401
from test_setup import _fresh_client
from test_tools_session_hold import Session

STORY = "FIX-HANDBACK-ROUND"


@pytest.mark.platform
def test_1_handback_wrong_round_names_open_round_and_no_open_round_gives_next_step(
        repo, gh, monkeypatch, tmp_path, person):
    # Test-audit: protects native handback refusal guidance for both wrong-round
    # and no-open-round cases through the real forge handback command.
    folder, made = _fresh_client(repo, gh, tmp_path)
    assert made.returncode == 0, made.stdout + made.stderr
    repo.path = folder
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "wrong-round-session")
    owner = Session(repo, tmp_path / "host", "claude-wrong-round")
    try:
        started = owner.forge("start", "Save a basket")
        assert started.returncode == 0, started.stdout + started.stderr
        offered = json.loads(started.stdout)
        target, number = offered["target"], offered["round"]
        wrong = number + 1

        refused = owner.forge("handback", target, "--round", str(wrong),
                              "--subagent", "explorer", "--text", "No findings.")
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert f"round {number} is open" in refused.stderr.lower()
        assert (f"Next: forge handback {target} --round {number} "
                '--subagent explorer --text "<its last message>"') in refused.stderr

        # The open round is still intact in the agent lane.
        lanes = owner.forge("lanes", "--json")
        assert lanes.returncode == 0, lanes.stderr
        [run] = json.loads(lanes.stdout)["agents"]["entries"]
        assert run["item"] == target and run["round"] == number

        # Once the round is stopped (no open round), handback prints the next step.
        stopped = owner.forge("stop", "--id", run["id"])
        assert stopped.returncode == 0, stopped.stdout + stopped.stderr
        closed = owner.forge("handback", target, "--round", str(number),
                             "--subagent", "explorer", "--text", "No findings.")
        assert closed.returncode == 1, closed.stdout + closed.stderr
        assert "That round was stopped or replaced" in closed.stderr
        assert "Next: forge next" in closed.stderr
    finally:
        owner.close()
