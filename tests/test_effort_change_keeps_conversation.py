"""Codex repair effort goes on the turn and is recorded for token measurements."""
import json

from test_codex_resume import MODELS, _resuming
from test_codex_worker import _lines, _sent, _toml, sdk_data  # noqa: F401

STORY = "FORGE-TOKENS-2"
ITEM = "BOARD/PAGE"


def test_1_a_repair_records_the_effort_used_in_the_same_conversation(repo, monkeypatch, sdk_data):
    folder, calls, _ = _resuming(repo, monkeypatch, sdk_data)
    models = {**MODELS, "build": {**MODELS["build"], "effort": "low"}}
    version = repo.forge("--version").stdout.split()[-1]
    (folder / "forge.toml").write_text(_toml(version, "codex", models), encoding="utf-8")
    repo.git("commit", "-qam", "Start at low effort", cwd=folder)

    for _ in range(3):
        work = repo.forge("work", ITEM)
        assert work.returncode == 0, work.stdout + work.stderr

    [start] = _sent(calls, "thread/start")
    assert start["config"]["model_reasoning_effort"] == "low"
    first, raised, unchanged = _sent(calls, "turn/start")
    first_resume, second_resume = _sent(calls, "thread/resume")
    for resume in (first_resume, second_resume):
        assert resume["threadId"] == first["threadId"]
        assert "model_reasoning_effort" not in resume["config"]
    assert raised["threadId"] == unchanged["threadId"] == first["threadId"]
    assert [turn["effort"] for turn in (first, raised, unchanged)] == ["low", "high", "high"]

    ends = [event for event in _lines(repo.path / ".git/forge/events.jsonl")
            if event.get("event") == "run end" and event.get("item") == ITEM]
    assert [(event["round"], event["effort"]) for event in ends] == [
        (1, "low"), (2, "high"), (3, "high")]


def test_2_a_replacement_conversation_gets_effort_on_start_and_turn(repo, monkeypatch, sdk_data):
    _, calls, _ = _resuming(repo, monkeypatch, sdk_data)
    first = repo.forge("work", ITEM)
    assert first.returncode == 0, first.stdout + first.stderr
    [turn] = _sent(calls, "turn/start")
    store = repo.bin / "threads.json"
    threads = json.loads(store.read_text(encoding="utf-8"))
    del threads[turn["threadId"]]
    store.write_text(json.dumps(threads), encoding="utf-8")

    repair = repo.forge("work", ITEM)
    assert repair.returncode == 0, repair.stdout + repair.stderr
    assert "Starting a new Codex conversation" in repair.stdout
    [resume] = _sent(calls, "thread/resume")
    assert resume["threadId"] == turn["threadId"]
    assert "model_reasoning_effort" not in resume["config"]
    _, replacement = _sent(calls, "thread/start")
    assert replacement["config"]["model_reasoning_effort"] == "high"
    assert _sent(calls, "turn/start")[-1]["effort"] == "high"
