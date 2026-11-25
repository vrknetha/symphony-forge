"""Capacity recovery through commands, faking only provider responses and backoff.

Test audit: rejected starts and Autoreview errors bypass existing terminal-turn
coverage. A long failure can hide capacity from a last-line reader. A shared trace
of provider attempts and the fake clock proves waits precede retries, so removing
either sleep fails the test. Only provider responses and backoff are replaced;
no production seam is added.
"""
import json
import os
from pathlib import Path

import pytest

from conftest import _install
from test_close import CLEAN, env  # noqa: F401
from test_codex_worker import ROOT, _codex_repo, _sent, sdk_data  # noqa: F401

STORY = "codex-capacity-retry"


@pytest.mark.parametrize("failures", [2, 99], ids=["recovers", "exhausted"])
@pytest.mark.parametrize("command", ["work", "close"])
def test_1_commands_retry_capacity_before_failing(request, monkeypatch, command, failures):
    if command == "work":
        request.getfixturevalue("claude_session")
        _work(request.getfixturevalue("repo"), monkeypatch,
              request.getfixturevalue("sdk_data"), failures)
    else:
        _close(request.getfixturevalue("env"), failures)


def _clock(repo):
    trace = repo.bin / "capacity-trace.jsonl"
    startup = repo.bin / "sitecustomize.py"
    startup.write_text((startup.read_text("utf-8") if startup.exists() else "") + f'''
import time
from pathlib import Path
from json_log import append_json
def capacity_event(event):
    append_json(Path({json.dumps(trace.as_posix())}), event)
capacity_real_sleep = time.sleep
def capacity_sleep(seconds):
    if seconds in (30, 60, 120):
        capacity_event(["wait", seconds])
    else:
        capacity_real_sleep(seconds)
time.sleep = capacity_sleep
''', encoding="utf-8")
    return trace


def _expected(failures):
    trace = [["attempt"]]
    for wait in ([30, 60] if failures == 2 else [30, 60, 120]):
        trace.extend([["wait", wait], ["attempt"]])
    return trace


def _events(trace):
    return [json.loads(line) for line in trace.read_text("utf-8").splitlines()]


def _work(repo, monkeypatch, sdk_data, failures):
    _, calls = _codex_repo(repo, monkeypatch, sdk_data)
    trace = _clock(repo)
    program = (ROOT / "tests/stubs/codex-app-server").read_text("utf-8").replace(
        '            log(turn_started=time.time())', '''            log(turn_started=time.time())
            from sitecustomize import capacity_event
            capacity_event(["attempt"])
            if turns <= ''' + str(failures) + ''':
                send(id=message["id"], error={"code": -32603,
                     "message": "Selected model is at capacity. Please try again."})
                continue''')
    _install(repo.bin, "codex-app-server", program)
    done = repo.forge("work", "BOARD/PAGE")
    assert (done.returncode == 0) == (failures == 2), done.stdout + done.stderr
    turns = _sent(calls, "turn/start")
    assert len(turns) == (3 if failures == 2 else 4)
    assert all(turn == turns[0] for turn in turns)
    assert done.stdout.count("Codex is at capacity") == (2 if failures == 2 else 3)
    assert _events(trace) == _expected(failures)


def _close(env, failures):
    item, _ = env.start_fix()
    trace = _clock(env.repo)
    helper = Path(os.environ["AUTOREVIEW"])
    helper.write_text(helper.read_text("utf-8").replace("args = sys.argv[1:]", '''
from sitecustomize import capacity_event
capacity_event(["attempt"])
args = sys.argv[1:]
'''), encoding="utf-8")
    # The helper streams the terminal event, then prints a failure trailer containing
    # only the first 4,000 characters of accumulated output. Capacity is not last.
    prefix = (json.dumps({"type": "item.completed", "text": "review progress " * 50}) + "\n") * 8
    capacity = json.dumps({"type": "turn.failed", "error": {"message": "Codex model is at capacity"}})
    busy = {"exit": 3, "report": None,
            "say": prefix + capacity + "\ncodex engine failed (1)\n" + prefix[:4000]}
    env.reviews(*([busy] * failures), CLEAN)
    done = env.close(item)
    assert (done.returncode == 0) == (failures == 2), done.stdout + done.stderr
    calls = env.review_calls()
    # Close's existing second attempt stays available after the first bounded batch.
    assert len(calls) == (3 if failures == 2 else 8)
    assert all(call["head"] == calls[0]["head"] for call in calls)
    assert all(call["args"] == calls[0]["args"] for call in calls)
    assert done.stderr.count("Codex is at capacity") == (2 if failures == 2 else 6)
    assert _events(trace) == _expected(failures) * (1 if failures == 2 else 2)
    if failures == 2:
        assert "Autoreview run 1 did not finish" not in done.stderr
