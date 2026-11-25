"""forge merge finishes when the task folder is removed during the check wait.

Test audit: extend the merge-time command test with a running check and real
worktree removal. Only GitHub is faked. The old scenario returned green on the
first poll and missed failures in later polls, shared Git reads and CI history.
Direct deletion also leaves the Git worktree record in place.
"""
import json

import pytest

from test_close import body, env  # noqa: F401
from test_last_task_records_story_outcome import github_merge
from test_start_to_merge_time import line, merge_time, prepare
from test_queue_land_all import client  # noqa: F401
from test_train_land_all import train  # noqa: F401

STORY = "FIX-MERGE-PY-PASSES-THE-TASK-WORKTREE-AS-THE"


@pytest.mark.parametrize("default_moves,direct", [
    (False, False), (True, False), (True, True),
], ids=["same-default", "new-default", "new-default-hand-deleted"])
def test_1_merge_prints_its_line_after_the_task_folder_is_removed_during_checks(env, monkeypatch, default_moves, direct):
    item, where, start = prepare(env)
    head = env.repo.git("rev-parse", "HEAD", cwd=where)
    published = body(env.gh_calls("pr", "edit")[-1])
    github_merge(env, f"fix/{item}")
    other = env.tmp / "late-main"
    if default_moves:
        env.repo.git("clone", "-q", env.repo.git("remote", "get-url", "origin"), str(other))
        env.commit(other, "unrelated.txt", "Another change lands during the wait.\n")
    monkeypatch.setenv("FORGE_CHECKS_WAIT", "60")
    gh = env.repo.bin / "gh"
    hook = f'''\
if args[:4] == ["api", "--paginate", "--jq", ".check_runs[]"] and "/commits/{head}/" in args[-1]:
    task = pathlib.Path({json.dumps(where.as_posix())})
    main = {json.dumps(env.repo.path.as_posix())}
    pending, removed = here / "pending", here / "removed"
    check = {{"name": "tests", "status": "in_progress", "conclusion": None}}
    if not pending.exists():
        pending.touch()
    elif not removed.exists():
        if {direct!r}:
            import shutil
            shutil.rmtree(task)
        else:
            subprocess.run(["git", "worktree", "remove", "--force", str(task)], cwd=main, check=True)
        if {default_moves!r}:
            subprocess.run(["git", "push", "-q", "origin", "main"],
                           cwd={json.dumps(other.as_posix())}, check=True)
        removed.touch()
    else:
        assert not task.exists()
        check.update(status="completed", conclusion="success")
        (here / "green-after-removal").touch()
    print(json.dumps(check))
    print(json.dumps({{"name": "forge-pr-check", "status": "completed", "conclusion": "success"}}))
    sys.exit(0)
'''
    script = gh.read_text("utf-8").replace("args = sys.argv[1:]\n", "args = sys.argv[1:]\n" + hook, 1)
    gh.write_text(script.replace('"isDraft": False', f'"isDraft": False, "body": {published!r}'), "utf-8")

    result = env.repo.forge("merge", item, cwd=where)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Waiting:" in result.stdout and (env.repo.bin / "green-after-removal").exists()
    end = merge_time(env.repo, f".factory/fixes/{item}.json")
    assert line(item, start, end, "waiting for the owner") in result.stdout.splitlines()
    history = env.repo.git("log", "-1", "--format=%B", "origin/main").splitlines()
    assert any(row.startswith("Round 1:") and "CI passed, then passed" in row for row in history), history
    assert not any(row.startswith("Round unknown:") and "CI passed" in row for row in history), history
    if default_moves:
        assert env.repo.git("show", "origin/main:unrelated.txt") == "Another change lands during the wait."
