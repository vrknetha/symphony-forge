"""Forge configures Codex shortening and resends the repair details each round."""
import json

from test_codex_resume import _resuming
from test_codex_worker import _sent, sdk_data  # noqa: F401

STORY = "FORGE-TOKENS-2"


def test_3_builder_compaction_keeps_repair_details_in_the_next_turn(repo, monkeypatch, sdk_data):
    folder, calls, _ = _resuming(repo, monkeypatch, sdk_data)
    first = repo.forge("work", "BOARD/PAGE")
    assert first.returncode == 0, first.stdout + first.stderr

    state_file = folder / ".factory" / "stories" / "BOARD" / "tasks" / "PAGE.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["review"] = {"status": "blocked", "findings": [
        {"priority": "P1", "title": "Archived stories are missing", "body": "Show them too.",
         "file": "web/board.py", "line": 12}]}
    state["tests"] = "FAILED tests/test_board.py::test_archived_stories"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    repair = repo.forge("work", "BOARD/PAGE")
    assert repair.returncode == 0, repair.stdout + repair.stderr
    [start] = _sent(calls, "thread/start")
    [resume] = _sent(calls, "thread/resume")
    first_turn, repair_turn = _sent(calls, "turn/start")
    assert first_turn["threadId"] == resume["threadId"] == repair_turn["threadId"]
    prompt = repair_turn["input"][0]["text"]
    assert "- P1 Archived stories are missing (web/board.py:12): Show them too." in prompt
    assert "FAILED tests/test_board.py::test_archived_stories" in prompt

    for request in (start, resume):
        config = request["config"]
        assert config.get("model_auto_compact_token_limit") == 120000
        assert config.get("model_auto_compact_token_limit_scope") == "total"
