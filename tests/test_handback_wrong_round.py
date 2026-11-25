"""Wrong-round handback names the open round safely; abandoned or closed rounds give the next step."""
import json
import shlex

import pytest

from conftest import machine_cores
from test_codex_reader import GRILL
from test_codex_worker import _toml
from test_fix_agent_runs_wait_in_line import _until
from test_lanes_agents import person  # noqa: F401
from test_story import DOC, new_story, setup
from test_tools_session_hold import Session

STORY = "FIX-HANDBACK-ROUND"


@pytest.mark.platform
def test_1_handback_wrong_round_names_open_round_and_no_open_round_gives_next_step(
        repo, gh, monkeypatch, tmp_path, person):
    # Test-audit: protects native handback recovery for a replaced round, a live
    # round held by another session, a completed round and an abandoned round
    # whose owning session exited.
    setup(repo, keys=("SHOP",))
    machine_cores(repo, 2)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "wrong-round-session")
    version = repo.forge("--version").stdout.split()[-1]
    config = _toml(version, "split", GRILL).replace(
        'workers = "split"', 'workers = "split"\ntools = "claude"')
    shop = new_story(repo, "SHOP")
    (shop / "plans/SHOP.md").write_text(DOC, "utf-8")
    (shop / "forge.toml").write_text(config, "utf-8")

    sessions = []

    def open_session():
        owner = Session(repo, tmp_path / f"owner-{len(sessions)}", "claude-session")
        sessions.append(owner)
        return owner

    def lanes():
        result = repo.forge("lanes", "--json")
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)["agents"]["entries"]

    def offer(owner):
        result = owner.forge("read", "SHOP")
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    try:
        first = open_session()
        other = open_session()

        # 1. A stopped reader returns after a replacement read has started.
        stopped_round = offer(first)
        ended = first.forge("stop", "SHOP")
        assert ended.returncode == 0, ended.stdout + ended.stderr
        replacement = offer(first)
        assert replacement["round"] > stopped_round["round"]

        stale = first.forge("handback", "SHOP", "--round", str(stopped_round["round"]),
                            "--subagent", "stopped-reader", "--text", "No findings.")
        assert stale.returncode == 1, stale.stdout + stale.stderr
        assert (f"Round {stopped_round['round']} is not the open round for SHOP; "
                f"round {replacement['round']} is open, so Forge recorded nothing.") in stale.stderr
        assert "not a stopped round's" in stale.stderr
        expected_cmd = (f"forge handback SHOP --round {replacement['round']} "
                        '--subagent <id> --text "<message>"')
        assert f"Next: {expected_cmd}" in stale.stderr
        # Never copy the rejected stopped subagent's id into the replacement command.
        assert "stopped-reader" not in stale.stderr

        # Another session cannot execute a handback for a live round it does not own.
        foreign = other.forge("handback", "SHOP", "--round", str(stopped_round["round"]),
                              "--subagent", "stopped-reader", "--text", "No findings.")
        assert foreign.returncode == 1, foreign.stdout + foreign.stderr
        assert f"open round {replacement['round']}" in foreign.stderr
        assert "another session holds" in foreign.stderr
        assert "forge handback" not in foreign.stderr
        assert "Next: forge next" in foreign.stderr

        # Filling in the replacement subagent's own id and message in the printed command succeeds.
        next_line = next(line[len("Next: "):] for line in stale.stderr.splitlines()
                         if line.startswith("Next: "))
        filled = (next_line.replace("<id>", "replacement-reader")
                           .replace("<message>", "No findings."))
        recovered = first.forge(*shlex.split(filled)[1:])
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        assert lanes() == []

        # 2. With no open round left, handback prints the next step.
        closed = first.forge("handback", "SHOP", "--round", str(replacement["round"]),
                             "--subagent", "replacement-reader", "--text", "No findings.")
        assert closed.returncode == 1, closed.stdout + closed.stderr
        assert "That round was stopped or replaced" in closed.stderr
        assert "Next: forge next" in closed.stderr
        assert first.forge("next").returncode == 0

        # 3. An abandoned pending round (owning session exited) is not treated as open.
        doc = shop / "plans/SHOP.md"
        doc.write_text(doc.read_text("utf-8") + "\nSaved baskets expire after thirty days.\n", "utf-8")
        abandoned = offer(first)
        first.close()
        _until(lambda: lanes() == [], "the closed session's read to leave")

        after_crash = other.forge("handback", "SHOP", "--round", str(abandoned["round"] + 1),
                                  "--subagent", "old-reader", "--text", "No findings.")
        assert after_crash.returncode == 1, after_crash.stdout + after_crash.stderr
        assert "That round was stopped or replaced" in after_crash.stderr
        assert "forge handback" not in after_crash.stderr
        assert "Next: forge next" in after_crash.stderr
        follow = other.forge("next")
        assert follow.returncode == 0, follow.stdout + follow.stderr
        assert "Next: forge read SHOP" in follow.stdout
    finally:
        for owner in reversed(sessions):
            owner.close()
