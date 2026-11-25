"""A failed forge-pr-check prints its refusal reasons and next step in the GitHub job log."""
import os
import re
import shutil
import subprocess

import pytest

from test_close import env  # noqa: F401
from test_runner_without_gh import github, logged_python, no_gh_path  # noqa: F401
from test_two_round_limit import client

STORY = "FIX-PR-CHECK-REFUSAL-LOG"

pytestmark = [pytest.mark.platform,
              pytest.mark.skipif(os.name == "nt", reason="The trusted workflow runs in bash on Linux")]


@pytest.mark.parametrize(
    ("proof_block", "expected_reasons"),
    [
        (
            "Proof list:\n"
            "- Done when: tests/test_missing_one.py::test_1_first (new; closest none; proves first)\n"
            "- Done when: tests/test_missing_two.py::test_2_second (new; closest none; proves second)",
            [
                "Done-when proof: tests/test_missing_one.py::test_1_first is not on this branch.",
                "Done-when proof: tests/test_missing_two.py::test_2_second is not on this branch.",
            ],
        ),
        (
            "Proof list:\n- Done when:",
            [
                "Done-when proof: The fix's Done-when line names no test in the Proof list.",
                'Done-when proof: Add a line "Done when: <test>" to the Proof list in your last commit message.',
            ],
        ),
    ],
    ids=["multiple-missing-tests", "missing-test-mapping"],
)
def test_1_failed_pr_check_prints_refusal_and_next_step_in_job_log(
    env, github, tmp_path, proof_block, expected_reasons
):
    server, calls, answers = github
    client(env, False)
    repo = env.repo
    config = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", config + 'test_place = "ci"\n', "Use CI tests")
    item, where = env.start_fix()
    env.commit(where, "app.py", "print('changed with invalid proof')\n", f"Change app\n\n{proof_block}")

    job_url = "https://github.com/acme/shop/actions/runs/123/job/456"
    answers["/repos/acme/shop/actions/runs/123/jobs"] = {
        "jobs": [{"name": "Review pull request", "html_url": job_url}]}
    job = repo.git("show", "main:.github/workflows/forge.yml").split("\n  forge-pr-check:\n", 1)[1]
    steps = re.split(r"^      - ", job, flags=re.M)
    command = re.search(r"^        run: (.+)$", next(s for s in steps if "run: forge hook pr-check" in s), re.M)[1]
    reporter = next(s for s in steps if "Report review status" in s).split("        run: |\n", 1)[1]
    reporter = "\n".join(line.removeprefix("          ") for line in reporter.splitlines())

    path = no_gh_path(tmp_path, "git", "forge", "cat")
    logged_python(tmp_path / "no-gh-bin", tmp_path / "python-arguments.jsonl")
    head = repo.git("rev-parse", "HEAD", cwd=where)
    variables = {**os.environ, "PATH": path, "GITHUB_API_URL": server, "GH_TOKEN": "test-token",
                 "GITHUB_REPOSITORY": "acme/shop", "GITHUB_RUN_ID": "123", "HEAD_SHA": head,
                 "BASE_SHA": repo.git("rev-parse", "main"), "HEAD_REF": f"fix/{item}",
                 "RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(tmp_path / "outputs")}
    bash = shutil.which("bash")
    checked = subprocess.run([bash, "-e", "-c", command], cwd=repo.path, env=variables,
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
    variables["REVIEW_OUTCOME"] = "success" if checked.returncode == 0 else "failure"
    variables["REVIEW_PENDING"] = ""
    reported = subprocess.run([bash, "-e", "-c", reporter], cwd=repo.path, env=variables,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)

    assert (checked.returncode, reported.returncode) == (1, 1), (checked.stderr, reported.stderr)
    assert reported.stdout.splitlines() == [*expected_reasons, f"Next: forge work {item}"]
