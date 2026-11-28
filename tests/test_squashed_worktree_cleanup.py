"""Forge removes work folders whose changes are already in the default branch."""
import json

import pytest

from test_doctor_fix import _client, _gone, _kept, _prs, _work

STORY = "FIX-BUG-52"


@pytest.mark.parametrize("command", [("lanes", "--json"), ("land", "--all"), ("doctor",)])
def test_1_commands_sweep_squashed_worktrees_and_list_retained_folders(repo, gh, tmp_path, command):
    _client(repo)
    finished = {}
    for branch in ("fix/shipped", "task/SHIP-1-CODE", "story/SHIP-1"):
        folder, _ = _work(repo, tmp_path, branch, commit=False)
        finished[branch] = folder
        change = branch.replace("/", "-") + ".txt"
        (folder / change).write_text(branch + "\n", encoding="utf-8")
        repo.git("add", change, cwd=folder)
        repo.git("commit", "-qm", "Change the file", cwd=folder)
        head = repo.git("rev-parse", "HEAD", cwd=folder)
        repo.git("merge", "--squash", branch)
        repo.write("main.txt", "Only on main\n")
        repo.git("add", ".")
        repo.git("commit", "-qm", f"Squash {branch}")
        assert repo.git("merge-base", "main", head) != head
    dirty, _ = _work(repo, tmp_path, "fix/with-notes", commit=False)
    (dirty / "notes.txt").write_text("Keep local notes\n", encoding="utf-8")
    unfinished, _ = _work(repo, tmp_path, "fix/unfinished", commit=False)
    (unfinished / "new.txt").write_text("Unmerged change\n", encoding="utf-8")
    repo.git("add", "new.txt", cwd=unfinished)
    repo.git("commit", "-qm", "Still in progress", cwd=unfinished)
    repo.git("push", "-q", "origin", "main")
    _prs(gh, exit=1)

    result = repo.forge(*command)

    assert all(_gone(repo, folder, branch) for branch, folder in finished.items()), result.stdout + result.stderr
    assert _kept(repo, dirty, "fix/with-notes")
    assert _kept(repo, unfinished, "fix/unfinished")
    output = result.stdout if command[0] == "doctor" else result.stderr
    assert dirty.as_posix() in output.replace("\\", "/")
    if command[0] == "lanes":
        assert result.returncode == 0, result.stderr
        json.loads(result.stdout)
