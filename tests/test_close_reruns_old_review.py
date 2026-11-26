"""Close retries the only failed required review once and waits for CI."""
import json

import pytest

from test_close import GREEN, env, run  # noqa: F401
from test_land import _queue, land  # noqa: F401

STORY = "FIX-CLOSE-RERUNS-STALE-REVIEW-CHECK"


@pytest.mark.parametrize("case", ["head-recovers", "head-stays-red", "optional-red"])
def test_1_close_retries_the_only_failed_required_review(land, monkeypatch, case):
    monkeypatch.setenv("FORGE_CHECKS_WAIT", "20")
    env = land
    item, where = env.start_fix()
    # Publish the review record first so the stub can attach both statuses to
    # the exact commit close queries. Only the GitHub boundary is scripted.
    closed = env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    env.open_pr("")
    head = env.repo.git("rev-parse", "HEAD", cwd=where)
    status = {"context": "forge-pr-check", "url": f"https://api.github.com/repos/acme/shop/statuses/{head}"}
    red = json.dumps({**status, "state": "failure",
                      "target_url": "https://github.com/acme/shop/actions/runs/77/job/701"})
    green = json.dumps({**status, "state": "success",
                        "target_url": "https://github.com/acme/shop/actions/runs/77/job/702"})
    checks = [row for row in GREEN if row["name"] not in ("forge-pr-check", "lint")]
    env.checks(checks + [run("lint", "failure" if case == "optional-red" else "success")])
    status_api = ["api", "--paginate", "--jq", ".statuses[]",
                  f"repos/{{owner}}/{{repo}}/commits/{head}/status?per_page=100"]
    _queue(env, status_api, red, red if case == "head-stays-red" else green)
    endpoint = ["api", "--paginate", "--jq", "[.][]", "repos/{owner}/{repo}/actions/runs/77"]
    workflow = {"path": ".github/workflows/forge.yml", "event": "pull_request_target"}
    _queue(env, endpoint,
           json.dumps({**workflow, "run_attempt": 1, "status": "completed", "conclusion": "failure"}),
           json.dumps({**workflow, "run_attempt": 2, "status": "in_progress"}),
           json.dumps({**workflow, "run_attempt": 2, "status": "completed",
                       "conclusion": "failure" if case == "head-stays-red" else "success"}))
    env.gh.respond("run", "rerun", "77", "--failed")

    done = env.close(item)

    assert env.gh_calls("run", "rerun") == [["run", "rerun", "77", "--failed"]], done.stderr
    # The three answers are the original failure, an active retry, and its
    # completion. GitHub can post a green job status while the run still reports
    # in progress. Close must wait for the retry to finish.
    assert len(env.gh_calls(*endpoint)) >= 3, done.stdout + done.stderr
    assert "Waiting: forge-pr-check is still running." in done.stdout
    if case == "head-recovers":
        assert done.returncode == 0, done.stdout + done.stderr
    else:
        failure = "lint" if case == "optional-red" else "forge-pr-check"
        assert done.returncode == 1 and f"Checks failed on the pull request: {failure}." in done.stderr
