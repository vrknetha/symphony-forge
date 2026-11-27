"""Close counts failed reruns once and never calls cancellations retries."""
import pytest

from test_close import env  # noqa: F401
from test_ci_time_report import _at, _check, _graphql, _job, _jobs, _pull

STORY = "FIX-CI-TIMING-REAL-RETRIES"


@pytest.mark.parametrize("scenario,conclusion,retries,tests", [
    ("group", "cancelled", None, "11 min"),
    ("group", "success", None, "11 min"),
    ("group", "failure", "10 min", "1 min"),
    ("group", "timed_out", "10 min", "1 min"),
    ("single", "failure", "10 min", "1 min"),
    ("docs", "failure", None, "1 min"),
    ("queued", "failure", None, "10 min"),
    ("unstarted", "failure", None, "1 min"),
    ("retry-label", "success", None, "1 min"),
])
def test_1_close_reports_only_failed_attempts_as_retry_time(env, scenario, conclusion, retries, tests):
    item, where = env.start_fix()
    sha = env.commit(where, ".github/workflows/forge.yml",
                     "name: Forge\non: pull_request\njobs:\n  tests:\n"
                     "    timeout-minutes: 10\n    runs-on: ubuntu-latest\n"
                     "    steps:\n      - run: python -m pytest\n")
    name = "docs-check" if scenario == "docs" else "tests" if scenario == "single" else "test group 1 of 1"
    checks = [_check("test group 1 of 1" if scenario == "docs" else name, _at(10), _at(11))]
    if conclusion == "cancelled":
        checks.append(_check(name, _at(), _at(10), conclusion="CANCELLED"))
    pr = _pull(7, checks)
    pr["commits"]["nodes"][-1]["commit"]["oid"] = sha
    _graphql(env, [pr])
    earlier_steps = [] if scenario == "unstarted" else [
        ("Set up job" if scenario == "docs" else "Run tests", _at(), _at(10))]
    current_steps = [] if scenario == "queued" else [
        ("Set up job" if scenario == "docs" else
         "Run tests with retries" if scenario == "retry-label" else "Run tests", _at(10), _at(11))]
    earlier = dict(_job(name, _at(), _at(), _at(10), earlier_steps),
                   id=701, status="completed", conclusion=conclusion)
    current = dict(_job(name, _at(10), _at(10), _at(11), current_steps,
                        attempt=1 if scenario == "retry-label" else 2),
        id=702, status="completed", conclusion="success")
    if scenario == "queued":
        # GitHub can expose a queue timestamp as started_at before any step runs.
        current.update(status="queued", conclusion=None, completed_at=None)
    # filter=all can repeat a job; the same job id is one execution.
    jobs = [current, current] if scenario == "retry-label" else [earlier, current, earlier, current]
    if scenario == "docs":
        jobs.append(dict(_job("test group 1 of 1", _at(11), _at(11), _at(12), [
            ("Run tests", _at(11), _at(12))]), id=703, conclusion="success"))
    _jobs(env, 101, jobs)

    closed = env.repo.forge("close", item, cwd=where)

    assert closed.returncode == 0, closed.stdout + closed.stderr
    line = next(line for line in closed.stdout.splitlines() if line.startswith("CI:"))
    if retries:
        assert f"retries {retries}" in line
    else:
        assert "retries not reported separately" in line
    assert f"tests {tests};" in line
