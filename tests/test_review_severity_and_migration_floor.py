"""Close reports reviewer severity and applies the migration floor to the whole change."""

import pytest

from test_close import blocked, body, env  # noqa: F401
from test_review_bar import _prepare_client, _set_main_setting
from test_score_notes import _scored

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


@pytest.mark.parametrize("change", ["no-migration", "migration", "repair", "added-work", "alembic-edit"])
def test_4_close_floors_harm_only_when_the_change_includes_a_migration(env, tmp_path, change):
    _prepare_client(env, tmp_path, "new-client")
    old = ("alembic/versions/0001_preferences.py" if change == "alembic-edit"
           else "migrations/0001_preferences.sql")
    env.commit(env.repo.path, old, "# Create preferences\n" if change == "alembic-edit"
               else "-- Create preferences\n")
    if change == "added-work":
        _set_main_setting(env, "added_work_min_gain", "5", "Set the added-work minimum")
    else:
        env.repo.git("push", "-q", "origin", "main")
    changes = {"app.py": "print('preferences')\n"}
    if change in ("migration", "repair"):
        changes["migrations/0002_duration.sql"] = "-- Add preference duration\n"
    if change == "alembic-edit":
        changes[old] = "# Create preferences with duration\n"
    item, where = env.start_fix(changes=changes)
    note = _scored("P1", "The preference duration is stored wrongly",
                   f"Gain 4, Work {2 if change == 'added-work' else 3}, Harm 1\n"
                   f"The old migration {old} stores it in seconds.")
    if change == "added-work":
        note["body"] += "\nAdds work: check the unit before saving"
    env.reviews(blocked(note))

    if change == "repair":
        initial = env.close(item)
        assert initial.returncode == 1, initial.stdout + initial.stderr
        env.commit(where, "app.py", "print('duration')\n", "Repair preference duration")

    closed = env.close(item)
    has_migration = change in ("migration", "repair", "alembic-edit")
    assert closed.returncode == int(has_migration), closed.stdout + closed.stderr
    assert note["title"] in closed.stdout
    if has_migration:
        assert "Harm 4 (floor: migration)" in closed.stdout
    else:
        assert "Harm 1" in closed.stdout
        assert "(floor: migration)" not in closed.stdout
    if change == "repair":
        assert len(env.review_calls()) == 2
    if change == "added-work":
        assert "Does not block: Adds work below this repo's minimum Gain 5." in closed.stdout
