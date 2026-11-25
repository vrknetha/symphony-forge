"""A stale required review gets one retry through close, then close waits for CI."""
import json

import pytest

from test_close import GREEN, env, run  # noqa: F401
from test_land import _queue, land  # noqa: F401

STORY = "FIX-CLOSE-RERUNS-STALE-REVIEW-CHECK"


@pytest.mark.parametrize("case", ["head-recovers", "head-stays-red", "optional-red", "base-sha",
                                  "older-review-run-reports-base-sha"])
def test_1_close_retries_the_only_failed_review_from_an_older_commit(land, monkeypatch, case):
    # Prove both the retry lifecycle and the current-head gate through close.
    # A rerun reports against its original commit. A separate job can finish on
    # the new head before that rerun ends. No production test seam is needed.
    monkeypatch.setenv("FORGE_CHECKS_WAIT", "20")
    env = land
    item, where = env.start_fix()
    base = env.repo.git("rev-parse", "origin/main", cwd=where)
    older = env.repo.git("rev-parse", "HEAD", cwd=where)
    env.commit(where, ".github/workflows/forge.yml", "name: Fixed CI\n")
    reviewed = older
    if case == "base-sha":
        closed = env.close(item)
        assert closed.returncode == 0, closed.stdout + closed.stderr
        env.open_pr("")
        reviewed = env.repo.git("rev-parse", "HEAD", cwd=where)
    url = "https://github.com/acme/shop/actions/runs/77/job/701"
    red = json.dumps({"context": "forge-pr-check", "state": "failure", "target_url": url,
                      "url": f"https://api.github.com/repos/acme/shop/statuses/{reviewed}"})
    green = json.dumps({"context": "forge-pr-check", "state": "success",
                        "target_url": "https://github.com/acme/shop/actions/runs/78/job/702"})
    checks = [row for row in GREEN if row["name"] not in ("forge-pr-check", "lint")]
    env.checks(checks + [run("lint", "failure" if case == "optional-red" else "success")])
    status_api = ["api", "--paginate", "--jq", ".statuses[]"]
    _queue(env, [*status_api, f"repos/{{owner}}/{{repo}}/commits/{base}/status?per_page=100"], "")
    if reviewed == older:
        _queue(env, [*status_api, f"repos/{{owner}}/{{repo}}/commits/{older}/status?per_page=100"], red)
    _queue(env, status_api, red, green if case in ("head-recovers", "optional-red") else red)
    endpoint = ["api", "--paginate", "--jq", "[.][]", "repos/{owner}/{repo}/actions/runs/77"]
    reported_sha = base if case in ("base-sha", "older-review-run-reports-base-sha") else older
    workflow = {"head_sha": reported_sha, "path": ".github/workflows/forge.yml", "event": "pull_request_target"}
    _queue(env, endpoint,
           json.dumps({**workflow, "run_attempt": 1, "status": "completed", "conclusion": "failure"}),
           json.dumps({**workflow, "run_attempt": 2, "status": "in_progress"}),
           json.dumps({**workflow, "run_attempt": 2, "status": "completed", "conclusion": "failure"}))
    env.gh.respond("run", "rerun", "77", "--failed")

    done = env.close(item)

    if case == "base-sha":
        assert not env.gh_calls("run", "rerun"), done.stdout
        assert done.returncode == 1 and "forge-pr-check." in done.stderr
        return

    assert env.gh_calls("run", "rerun") == [["run", "rerun", "77", "--failed"]], done.stderr
    # The three answers are the original failure, an active retry, and its
    # completion. A green status on the new head must not end the active wait.
    assert len(env.gh_calls(*endpoint)) >= 3, done.stdout + done.stderr
    assert "Waiting: forge-pr-check is still running." in done.stdout
    if case == "head-recovers":
        assert done.returncode == 0, done.stdout + done.stderr
    else:
        failure = "lint" if case == "optional-red" else "forge-pr-check"
        assert done.returncode == 1 and f"Checks failed on the pull request: {failure}." in done.stderr
