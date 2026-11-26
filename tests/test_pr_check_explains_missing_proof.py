"""The pull request check tells workers how to record missing proof."""

import pytest

from test_close import env  # noqa: F401
from test_done_when_tests import _ci_close, _greeting_files, _proof, _start_fix_without_proof

STORY = "FIX-PROOF-LIST-FAILURE-SAYS-WHY"


@pytest.mark.parametrize("earlier_proof", [False, True], ids=["no-earlier-proof", "renamed-test"])
def test_1_pr_check_explains_missing_proof(env, earlier_proof):
    # A merge-only Proof list can leave the gate with no test name or with an older name
    # that no longer exists. Both refusals need the same guidance. Use real Git and Forge.
    _ci_close(env)
    _, where = _start_fix_without_proof(env, _greeting_files())
    repo = env.repo
    base = repo.git("rev-parse", "main")
    test_file = "tests/test_greeting.py"
    expected = "The fix's Done-when line names no test in the Proof list."
    if earlier_proof:
        _proof(env, where, f"- Done when: `{test_file}::test_1_greets` (reuse)")
        expected = f"{test_file}::test_1_greets is not on this branch."
    repo.git("commit", "--allow-empty", "-m", "Update main")
    repo.git("merge", "--no-commit", "main", cwd=where)
    if earlier_proof:
        renamed = "tests/test_welcome.py"
        repo.git("mv", test_file, renamed, cwd=where)
        test_file = renamed
    repo.git("commit", "-m", "Merge main", "-m",
             f"Proof list:\n- Done when: `{test_file}::test_1_greets` (reuse)", cwd=where)

    checked = repo.forge("hook", "pr-check", "--base", base, "--head",
                         repo.git("rev-parse", "HEAD", cwd=where), "--branch", "fix/tidy-readme")
    output = checked.stdout + checked.stderr
    assert checked.returncode == 1, output
    assert f"Done-when proof: {expected}" in output
    assert "Put each test name in backticks." in output
    assert "Forge skips Proof lists on merge commits." in output
