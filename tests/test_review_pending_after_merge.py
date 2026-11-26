"""Post-merge proof shows as pending after merge, never blocks, and carries across rounds."""
from test_close import blocked, body, env, finding  # noqa: F401

STORY = "FORGE-REVIEWPROOF-1"


def _set_one_review_round(env):
    config = (env.repo.path / "forge.toml").read_text("utf-8")
    env.commit(env.repo.path, "forge.toml", "task_review_rounds = 1\n" + config,
               "Set one review round for this test")
    env.repo.git("push", "-q", "origin", "main")


def _pending_finding(title="After merge: Main's full CI run passes",
                     check="Run the full CI workflow on main",
                     owner="Release owner"):
    note = finding("P0", title)
    lines = ["Gain 5, Work 1, Harm 5", "Only exists after merge."]
    if check:
        lines.append(f"Check: {check}")
    if owner:
        lines.append(f"Owner: {owner}")
    note["body"] = "\n".join(lines)
    return note


def test_1_pending_after_merge_does_not_block_and_lists_check_and_owner(env):
    story_doc = (env.repo.path / "plans" / "SHOP.md").read_text("utf-8").replace(
        "| 1 | `app.py` |", "| 1, 2 | `app.py` |"
    )
    env.commit(env.repo.path, "plans/SHOP.md", story_doc, "Cover items 1 and 2 in T1")
    env.repo.git("push", "-q", "origin", "main")
    item, where = env.start_task()
    env.commit(where, "tests/test_app.py", "def test_ok():\n    assert True\n", "Add app test")
    env.commit(
        where, "app.py", "print('hello')\n",
        "Add greeting\n\nProof list:\n- 1: `tests/test_app.py` (new; closest none; proves greeting)\n"
        "- 2: check: Main's full CI run passes\n",
    )
    pending = _pending_finding()
    prefixed = _pending_finding(
        title="Not fixed: After merge: Nightly report is green",
        check="Read the nightly report after merge",
        owner="",
    )
    env.reviews(blocked(pending, prefixed))
    closed = env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    assert "names no test" not in closed.stdout + closed.stderr
    assert "Review: clean." in closed.stdout
    assert "Ready:" in closed.stdout
    assert "Pending after merge:" in closed.stdout
    assert "Run the full CI workflow on main" in closed.stdout
    assert "Owner: Release owner" in closed.stdout
    assert "Owner: owner not named" in closed.stdout
    assert "Follow-ups that do not block the merge" not in closed.stdout

    published = body(env.gh_calls("pr", "edit")[-1])
    before_fold = published.split("<details>", 1)[0]
    assert "Pending after merge:" in before_fold
    assert "Run the full CI workflow on main" in before_fold
    assert "Owner: Release owner" in before_fold
    assert "Owner: owner not named" in before_fold

    gate = env.repo.forge(
        "hook", "pr-check",
        "--base", env.repo.git("rev-parse", "HEAD"),
        "--head", env.repo.git("rev-parse", "HEAD", cwd=where),
        "--branch", env.repo.git("branch", "--show-current", cwd=where),
    )
    assert gate.returncode == 0, gate.stdout + gate.stderr
    assert "names no test" not in gate.stdout + gate.stderr
    assert "is not on this branch" not in gate.stdout + gate.stderr
    assert "blocked by serious findings" not in gate.stderr


def test_2_pending_after_merge_carries_across_rounds_and_stays_out_of_stop_accept_and_spotted(env):
    _set_one_review_round(env)
    item, where = env.start_fix()
    blocker = finding("P1", "Greeting is missing")
    pending = _pending_finding()
    env.reviews(blocked(blocker, pending))

    first = env.close(item)
    assert first.returncode == 1, first.stdout + first.stderr
    assert "Greeting is missing" in first.stdout + first.stderr
    # Stop question lists only the blocking finding, never the pending check.
    stop_section = first.stderr.split("Question:", 1)[-1] if "Question:" in first.stderr else first.stderr
    assert "After merge:" not in stop_section

    env.open_pr(body(env.gh_calls("pr", "edit")[-1]), draft=True)
    # Choosing accept dismisses only the blocker and leaves the pending check listed and undismissed.
    accepted = env.close(item, "--resolve", "accept", "--reason", "Ship with pending check")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    published = body(env.gh_calls("pr", "edit")[-1])
    before_fold, _, rest = published.partition("<details>")
    folded = rest.partition("</details>")[0]
    assert "Review: clean, 1 dismissed, 0 advice." in before_fold
    assert "Pending after merge:" in before_fold
    assert "Run the full CI workflow on main" in before_fold
    assert "dismissed because" not in before_fold
    assert "Greeting is missing" in folded and "dismissed because" in folded
    assert "After merge:" not in folded

    # A close on an unchanged commit reuses the saved review and makes no second review call.
    reused = env.close(item)
    assert reused.returncode == 0, reused.stdout + reused.stderr
    assert len(env.review_calls()) == 1

    # A repair commit whose review omits the pending check still carries it forward cleanly.
    env.reviews(blocked())
    env.commit(where, "app.py", "print('fixed')\n", "Fix greeting")
    second = env.close(item)
    assert second.returncode == 0, second.stdout + second.stderr
    assert len(env.review_calls()) == 2
    published2 = body(env.gh_calls("pr", "edit")[-1])
    before_fold2 = published2.split("<details>", 1)[0]
    assert "Pending after merge:" in before_fold2
    assert "Run the full CI workflow on main" in before_fold2

    # No spotted entry is created for the pending check.
    spotted_file = where / "plans" / "spotted.json"
    if spotted_file.exists():
        assert "After merge:" not in spotted_file.read_text("utf-8")
    spotted_dir = where / "plans" / "spotted"
    if spotted_dir.exists():
        for path in spotted_dir.glob("*.json"):
            assert "After merge:" not in path.read_text("utf-8")
