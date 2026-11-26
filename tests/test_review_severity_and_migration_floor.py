"""Close reports reviewer severity and applies the migration floor to the whole change."""

import pytest

from test_close import blocked, body, env  # noqa: F401
from test_review_bar import _prepare_client, _set_main_setting
from test_score_notes import _scored
from test_score_upgrade import _move_to, _on_release

STORY = "FORGE-REVIEWPROOF-1"


@pytest.mark.parametrize("priority,scores", [("P1", "Gain 4, Work 2, Harm 4"),
                                              ("P0", "Gain 1, Work 5, Harm 1")])
def test_3_close_shows_reviewer_severity_and_merge_status(env, tmp_path, priority, scores):
    _prepare_client(env, tmp_path, "new-client")
    title = "Saving drops the basket"
    item, where = env.start_fix(steps=[])
    env.reviews(blocked(_scored(priority, title, scores)))

    closed = env.close(item)
    assert closed.returncode == 1, closed.stdout + closed.stderr
    assert f"1. {priority}, blocks the merge. {title} (app.py:1)" in closed.stdout
    published = body((env.gh_calls("pr", "edit") or env.gh_calls("pr", "create"))[-1])
    review, history = published.split("## How it went", 1)
    assert f"Finding 1 ({priority}): {title} (app.py:1): blocks the merge" in review
    assert f"{priority} {title} (app.py)" in history
    shown = env.repo.forge("close", item, "--show", cwd=where)
    assert shown.returncode == 0, shown.stdout + shown.stderr
    assert f"1. {priority} {title} (app.py:1)\nOpen: blocks the merge." in shown.stdout
    if priority == "P1":
        assert "P0" not in closed.stdout
        assert f"(P0): {title}" not in review
        assert f"P0 {title}" not in history


@pytest.mark.parametrize("change", ["no-migration", "migration", "repair", "added-work", "alembic-edit",
                                    "delete"])
def test_4_close_floors_harm_only_when_the_change_includes_a_migration(env, tmp_path, change):
    _prepare_client(env, tmp_path, "new-client")
    old = ("alembic/versions/0001_preferences.py" if change == "alembic-edit"
           else "migrations/0001_preferences.sql")
    original = "# Create preferences\n" if change == "alembic-edit" else "-- Create preferences\n"
    env.commit(env.repo.path, old, original)
    if change == "added-work":
        _set_main_setting(env, "added_work_min_gain", "5", "Set the added-work minimum")
    else:
        env.repo.git("push", "-q", "origin", "main")
    changes = {"app.py": "print('preferences')\n"}
    if change in ("migration", "repair"):
        changes["migrations/0002_duration.sql"] = "-- Add preference duration\n"
    if change == "alembic-edit":
        changes[old] = "# Create preferences with duration\n"
    if change == "delete":
        changes = {old: original}
    item, where = env.start_fix(changes=changes)
    if change == "delete":
        env.repo.git("rm", "--", old, cwd=where)
        env.repo.git("commit", "-qm", "Remove the obsolete migration", cwd=where)
    note = _scored("P1", "The preference duration is stored wrongly",
                   f"Gain 4, Work {2 if change == 'added-work' else 3}, Harm 1\n"
                   f"The old migration {old} stores it in seconds.")
    if change == "added-work":
        note["body"] += "\nAdds work: check the unit before saving"
    other = _scored("P1", "The timeout is stored wrongly",
                    "Gain 4, Work 3, Harm 1\nAn earlier migration stores it in minutes.")
    env.reviews(blocked(note, other) if change == "migration" else blocked(note))

    if change == "repair":
        initial = env.close(item)
        assert initial.returncode == 1, initial.stdout + initial.stderr
        env.commit(where, "app.py", "print('duration')\n", "Repair preference duration")

    closed = env.close(item)
    has_migration = change in ("migration", "repair", "alembic-edit")
    assert closed.returncode == int(has_migration), closed.stdout + closed.stderr
    assert note["title"] in closed.stdout
    if has_migration:
        assert closed.stdout.count("Harm 4 (floor: migration)") == (2 if change == "migration" else 1)
    else:
        assert "Harm 1" in closed.stdout
        assert "(floor: migration)" not in closed.stdout
    if change == "repair":
        assert len(env.review_calls()) == 2
    if change == "added-work":
        assert "Does not block: Adds work below this repo's minimum Gain 5." in closed.stdout


def test_5_close_rechecks_an_old_migration_floor_and_shows_saved_severity(env, tmp_path):
    _prepare_client(env, tmp_path, "new-client")
    config = (env.repo.path / "forge.toml").read_text("utf-8")
    current = config.split('"')[1]
    old = "migrations/0001_preferences.sql"
    env.commit(env.repo.path, old, "-- Create preferences\n")
    _on_release(env.repo, tmp_path, "v1.2.49")
    _move_to(env.repo, tmp_path, config, "v1.2.49", "fix/earlier")
    env.repo.git("config", "core.hooksPath", (tmp_path / "fixture-hooks").as_posix())
    item, where = env.start_fix(steps=[])
    title = "The preference duration is stored wrongly"
    note = _scored("P1", title, f"Gain 4, Work 3, Harm 1\nThe old migration {old} stores it in seconds.")
    env.reviews(blocked(note))
    before = env.close(item)
    assert before.returncode == 1 and "Harm 4 (floor: migration)" in before.stdout, before.stdout + before.stderr
    published = body(env.gh_calls("pr", "edit")[-1])
    assert f"P0 {title} (app.py)" in published.split("## How it went", 1)[1]
    env.open_pr(published)

    # Use the new executable on the same branch and the same published review.
    _on_release(env.repo, tmp_path, None)
    _move_to(env.repo, tmp_path, config, current, "fix/upgrade")
    env.repo.git("merge", "-q", "--no-edit", "origin/main", cwd=where)
    after = env.close(item)
    assert after.returncode == 0, after.stdout + after.stderr
    assert "Harm 1" in after.stdout
    assert "(floor: migration)" not in after.stdout
    assert len(env.review_calls()) == 2
    published = body(env.gh_calls("pr", "edit")[-1])
    history = published.split("## How it went", 1)[1].split("<!--", 1)[0]
    assert f"P0 {title}" not in history
    assert history.count(f"P1 {title} (app.py)") == 2

    env.open_pr(published)
    repeated = env.close(item)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert len(env.review_calls()) == 2
