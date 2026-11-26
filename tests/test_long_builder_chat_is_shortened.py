"""Forge configures Codex shortening and resends the repair details each round."""
import json
from pathlib import Path

from test_close import blocked, env, finding, run  # noqa: F401
from test_codex_resume import _resuming
from test_codex_worker import _sent, sdk_data  # noqa: F401
from test_task import story

STORY = "FORGE-TOKENS-2"


def test_3_builder_compaction_keeps_repair_details_in_the_next_turn(env, monkeypatch, sdk_data):
    repo = env.repo
    _, calls, _ = _resuming(repo, monkeypatch, sdk_data, start_task=False)
    settings = (repo.path / "forge.toml").read_text(encoding="utf-8")
    env.commit(repo.path, "forge.toml", 'checks = ["tests", "forge-pr-check"]\n' + settings,
               "Run tests in CI")
    repo.git("push", "-q", "origin", "main")
    story(repo)
    started = repo.forge("task", "start", "BOARD/PAGE")
    assert started.returncode == 0, started.stderr
    folder = Path(started.stdout.splitlines()[0].rsplit(" in ", 1)[1])
    first = repo.forge("work", "BOARD/PAGE")
    assert first.returncode == 0, first.stdout + first.stderr
    env.commit(folder, "web/board.py", "def stories():\n    return []\n",
               "Build the board\n\nProof list:\n- 1: check: The board lists stories")

    title = "Archived stories are missing"
    env.reviews(blocked(finding("P1", title, "web/board.py", 2)))
    env.checks([run("tests", "failure"), run("lint", None, "in_progress")])
    closed = env.close("BOARD/PAGE")
    assert closed.returncode == 1 and f"P1 {title}" in closed.stdout, closed.stdout + closed.stderr

    failed = "FAILED tests/test_board.py::test_archived_stories"
    env.gh.respond("pr", "checks", exit=1, stdout=json.dumps([
        {"name": "tests", "bucket": "fail", "link": "https://github.com/acme/shop/actions/runs/1/job/22"},
        {"name": "lint", "bucket": "pending", "link": "https://github.com/acme/shop/actions/runs/1/job/23"},
    ]))
    env.gh.respond("run", "view", "--job", "22", "--log-failed", exit=1,
                   stderr="run 1 is still in progress; logs will be available when it is complete\n")
    env.gh.respond("api", "repos/{owner}/{repo}/actions/jobs/22/logs",
                   stdout=f"Failed tests:\n{failed}\nFull test log: output.txt\n" + "Cleanup output\n" * 31)

    repair = repo.forge("work", "BOARD/PAGE")
    assert repair.returncode == 0, repair.stdout + repair.stderr
    [start] = _sent(calls, "thread/start")
    [resume] = _sent(calls, "thread/resume")
    first_turn, repair_turn = _sent(calls, "turn/start")
    assert first_turn["threadId"] == resume["threadId"] == repair_turn["threadId"]
    prompt = repair_turn["input"][0]["text"]
    assert f"- P1 {title} (web/board.py:2):" in prompt
    assert f"Evidence for: {title}" in prompt
    assert failed in prompt

    for request in (start, resume):
        config = request["config"]
        assert config.get("model_auto_compact_token_limit") == 120000
        assert config.get("model_auto_compact_token_limit_scope") == "total"
