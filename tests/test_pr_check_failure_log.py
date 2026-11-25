"""The trusted review job puts a failed proof check's guidance in its report."""
import os
import subprocess

import pytest

from test_close import env  # noqa: F401
from test_done_when_tests import _proof, _start_fix_without_proof
from test_runner_without_gh import read_job
from test_testplace_workflow import _jobs
from test_two_round_limit import client

STORY = "FIX-ABB-SOL-PRCHECK"


@pytest.mark.platform
@pytest.mark.skipif(os.name == "nt", reason="The trusted review job runs in bash on Linux")
@pytest.mark.parametrize(("proof_name", "reason", "next_step"), [
    (None, "The fix's Done-when line names no test in the Proof list.",
     'Add a line "Done when: <test>" to the Proof list in your last commit message.'),
    ("tests/test_greeting.py::test_old_greeting",
     "tests/test_greeting.py::test_old_greeting is not on this branch.",
     "Correct the test name in the Proof list or commit the missing test."),
], ids=["missing-entry", "outdated-name"])
def test_1_review_report_prints_refusal_and_next_step(env, gh, tmp_path, proof_name, reason, next_step):
    client(env, adopted=False)
    repo = env.repo
    workflow = repo.git("show", "main:.github/workflows/forge.yml")
    _, steps = read_job(_jobs(workflow)["forge-pr-check"])
    check = next(step for step in steps if step.get("id") == "review")
    report = next(step for step in steps if step.get("name") == "Report review status")
    _, where = _start_fix_without_proof(env, {
        "app.py": "print('Hello')\n",
        "tests/test_greeting.py": "def test_new_greeting(capsys):\n"
        "    import app\n"
        "    assert capsys.readouterr().out == 'Hello\\n'\n",
    })
    if proof_name:
        _proof(env, where, f"- Done when: {proof_name}")

    head = repo.git("rev-parse", "HEAD", cwd=where)
    jobs = "repos/acme/shop/actions/runs/123/jobs"
    gh.respond("api", jobs, "--jq", '.jobs[] | select(.name == "Review pull request") | .html_url',
               stdout="https://github.com/acme/shop/actions/runs/123/job/456\n")
    gh.respond("api", "--method", "POST", f"repos/acme/shop/statuses/{head}")
    variables = {**os.environ, "HEAD_SHA": head, "BASE_SHA": repo.git("rev-parse", "main"),
                 "HEAD_REF": "fix/tidy-readme", "RUNNER_TEMP": str(tmp_path),
                 "GITHUB_OUTPUT": str(tmp_path / "outputs"), "GITHUB_REPOSITORY": "acme/shop",
                 "GITHUB_RUN_ID": "123"}
    checked = subprocess.run(["bash", "-e", "-c", check["run"]], cwd=repo.path, env=variables,
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert checked.returncode == 1, checked.stdout + checked.stderr
    variables.update(REVIEW_OUTCOME="failure", REVIEW_PENDING="")
    reported = subprocess.run(["bash", "-e", "-c", report["run"]], cwd=repo.path, env=variables,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert reported.returncode == 1, reported.stdout + reported.stderr
    log = reported.stdout + reported.stderr
    assert reason in log, log
    assert next_step in log, log
