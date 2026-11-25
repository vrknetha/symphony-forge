"""Accepting a stopped review reaches checks across stacked replay, merge repairs and retries."""
import subprocess
import sys

import pytest

from conftest import GH_STUB, _install
from test_close import CLEAN, GREEN, blocked, body, env, finding, run  # noqa: F401
from test_last_task_records_story_outcome import github_merge
from test_stack_start import configured, reviewed, start

STORY = "abb-neon-accept"


@pytest.mark.parametrize("case", ["replay", "repair-retry"])
def test_1_accept_reaches_checks_across_stacked_replay_repairs_and_retry(env, case):
    repo = configured(env)
    config = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", "task_review_rounds = 1\n" + config)
    repo.git("push", "-q", "origin", "main")
    repo.git("switch", "-q", "story/STACK")
    repo.git("merge", "-q", "--no-edit", "origin/main")
    repo.git("push", "-q", "origin", "story/STACK")
    repo.git("switch", "-q", "main")

    env.reviews(CLEAN)
    reviewed(env, "A")
    where, _ = start(repo, "C")
    env.commit(where, "app.py", "A_VALUE = 1\nC_VALUE = 1\n",
               "Extend the saved value\n\nProof list:\n- 1: tests/test_work.py (reuse)")
    defect = {**finding("P1", "Remaining defect", "app.py", line=2),
              "body": "Gain 4, Work 1, Harm 2\nNormal runs lose the value."}
    env.reviews(blocked(defect))
    stopped = env.close("STACK/C")
    assert stopped.returncode == 1, stopped.stdout + stopped.stderr
    assert "One more round, split or accept?" in stopped.stderr
    assert ('Next: forge close STACK/C --resolve <more|split|accept> '
            '--reason "<human\'s choice>"') in stopped.stderr

    # Merge the parent task through Forge so STACK/C's next close targets main.
    github_merge(env, "task/STACK-A")
    merged = repo.forge("merge", "STACK/A")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    _install(repo.bin, "gh", GH_STUB.format(python=sys.executable))
    repo.git("fetch", "-q", "origin")
    repo.git("merge", "-q", "--ff-only", "origin/main")

    if case == "replay":
        env.commit(repo.path, "app.py", "# Parent landed\nA_VALUE = 1\n",
                   "Non-conflicting main update on reviewed file")
        repo.git("push", "-q", "origin", "main")
    else:
        env.commit(repo.path, "app.py", "A_VALUE = 1\nMAIN_VALUE = 1\n",
                   "Conflicting main update on reviewed file")
        repo.git("push", "-q", "origin", "main")
        repo.git("fetch", "-q", "origin", cwd=where)
        conflict = subprocess.run(["git", "merge", "--no-edit", "origin/main"],
                                  cwd=where, capture_output=True, text=True)
        assert conflict.returncode != 0, "expected a merge conflict to exercise merge_review.repairs"
        (where / "app.py").write_text("A_VALUE = 1\nMAIN_VALUE = 1\nC_VALUE = 1\n", encoding="utf-8")
        repo.git("add", "app.py", cwd=where)
        repo.git("commit", "-q", "--no-edit", cwd=where)

    reason = "Owner accepts the remaining risk"
    before = len(env.review_calls())
    later_defect = {**finding("P1", "Post-accept defect", "app.py", line=3),
                    "body": "Gain 4, Work 1, Harm 2\nNormal runs lose the value."}
    env.reviews(blocked(later_defect))
    env.checks([run("tests", "failure"), run("forge-pr-check")])
    accepted = env.close("STACK/C", "--resolve", "accept", "--reason", reason)
    assert accepted.returncode == 1, accepted.stdout + accepted.stderr
    assert "Recorded the human's choice." in accepted.stdout
    assert "One more round, split or accept?" not in accepted.stderr
    assert "tests" in accepted.stderr
    assert len(env.review_calls()) == before
    published = body(env.gh_calls("pr", "edit")[-1])
    assert "Review: clean" in published
    assert f"Human accepted the remaining finding: {reason}" in published

    # Retrying checks without --resolve keeps the accepted review and reaches Ready.
    env.checks(GREEN)
    retried = env.close("STACK/C")
    assert retried.returncode == 0, retried.stdout + retried.stderr
    assert "Ready:" in retried.stdout
    assert "One more round, split or accept?" not in retried.stderr
    assert len(env.review_calls()) == before
    pushed = repo.git("rev-parse", "HEAD", cwd=where)
    assert env.gh_calls("api", path=f"/commits/{pushed}/check-runs?")
    checked = repo.forge("hook", "pr-check", "--base", "origin/main", "--head", "HEAD",
                         "--branch", "task/STACK-C", cwd=where)
    assert checked.returncode == 0, checked.stdout + checked.stderr
