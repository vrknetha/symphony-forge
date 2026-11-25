"""A stale required review gets one retry through close, then close waits for CI."""
import json

from test_close import GREEN, env  # noqa: F401
from test_land import _queue, land  # noqa: F401

STORY = "FIX-CLOSE-RERUNS-STALE-REVIEW-CHECK"


def test_1_close_retries_the_only_failed_review_from_an_older_commit(land, monkeypatch):
    # The cancellation retry test covers test jobs on the current commit. This
    # case follows the required review status to an earlier commit through GitHub.
    monkeypatch.setenv("FORGE_CHECKS_WAIT", "20")
    env = land
    item, where = env.start_fix()
    older = env.repo.git("rev-parse", "HEAD", cwd=where)
    env.commit(where, ".github/workflows/forge.yml", "name: Fixed CI\n")
    url = "https://github.com/acme/shop/actions/runs/77/job/701"
    red = json.dumps({"context": "forge-pr-check", "state": "failure", "target_url": url})
    green = json.dumps({"context": "forge-pr-check", "state": "success"})
    env.checks([row for row in GREEN if row["name"] != "forge-pr-check"])
    _queue(env, ["api", "--paginate", "--jq", ".statuses[]"], red, red, green)
    endpoint = ["api", "--paginate", "--jq", "[.][]", "repos/{owner}/{repo}/actions/runs/77"]
    workflow = {"head_sha": older, "path": ".github/workflows/forge.yml", "event": "pull_request_target"}
    _queue(env, endpoint,
           json.dumps({**workflow, "run_attempt": 1, "status": "completed", "conclusion": "failure"}),
           json.dumps({**workflow, "run_attempt": 2, "status": "in_progress"}))
    env.gh.respond("run", "rerun", "77", "--failed")

    done = env.close(item)

    assert env.gh_calls("run", "rerun") == [["run", "rerun", "77", "--failed"]], done.stderr
    assert "Waiting: forge-pr-check is still running." in done.stdout
    assert done.returncode == 0, done.stdout + done.stderr
