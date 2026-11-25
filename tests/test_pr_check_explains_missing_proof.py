"""The pull request check tells workers how to record missing proof."""

from test_close import env  # noqa: F401
from test_done_when_tests import _ci_close, _greeting_files, _start_fix_without_proof

STORY = "FIX-PROOF-LIST-FAILURE-SAYS-WHY"


def test_1_pr_check_explains_missing_proof(env):
    # The closest case, test_3_ci_skips_do_not_hide_named_pytest_proof, checks the refusal
    # but misses guidance lost from it. Use the real check on a real merge with no test seam.
    _ci_close(env)
    _, where = _start_fix_without_proof(env, _greeting_files())
    repo = env.repo
    base = repo.git("rev-parse", "main")
    repo.git("commit", "--allow-empty", "-m", "Update main")
    repo.git("merge", "main", "-m", "Merge main", "-m",
             "Proof list:\n- Done when: `tests/test_greeting.py::test_1_greets` (reuse)", cwd=where)

    checked = repo.forge("hook", "pr-check", "--base", base, "--head",
                         repo.git("rev-parse", "HEAD", cwd=where), "--branch", "fix/tidy-readme")
    output = checked.stdout + checked.stderr
    assert checked.returncode == 1, output
    assert "Done-when proof: The fix's Done-when line names no test in the Proof list." in output
    assert "Put each test name in backticks." in output
    assert "Forge skips Proof lists on merge commits." in output
