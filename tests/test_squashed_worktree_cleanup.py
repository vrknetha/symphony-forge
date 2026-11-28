"""Forge removes work folders whose changes are already in the default branch."""
import json
from pathlib import Path

import pytest

from test_close import env  # noqa: F401
from test_doctor_fix import _client, _gone, _kept, _pr_page, _prs, _work
from test_merge_command import _ready

pytestmark = pytest.mark.platform
STORY = "FIX-BUG-52"


@pytest.mark.parametrize("command", [("lanes", "--json"), ("land", "--all"), ("doctor",)])
def test_1_commands_sweep_squashed_worktrees_and_list_retained_folders(repo, gh, tmp_path, command):
    _client(repo)
    finished = {}
    for branch in ("fix/shipped", "task/SHIP-1-CODE", "story/SHIP-1", "fix/with-notes", "fix/open"):
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
    dirty = finished.pop("fix/with-notes")
    open_pr = finished.pop("fix/open")
    (dirty / "notes.txt").write_text("Keep local notes\n", encoding="utf-8")
    unstarted, _ = _work(repo, tmp_path, "fix/unstarted", commit=False)
    unfinished, _ = _work(repo, tmp_path, "fix/unfinished", commit=False)
    (unfinished / "new.txt").write_text("Unmerged change\n", encoding="utf-8")
    repo.git("add", "new.txt", cwd=unfinished)
    repo.git("commit", "-qm", "Still in progress", cwd=unfinished)
    repo.git("push", "-q", "origin", "main")
    _sweep_prs(gh, (*finished, "fix/with-notes", "fix/unstarted", "fix/unfinished"),
               ("fix/open", repo.git("rev-parse", "fix/open"), "OPEN"))

    result = repo.forge(*command)

    assert all(_gone(repo, folder, branch) for branch, folder in finished.items()), result.stdout + result.stderr
    assert _kept(repo, dirty, "fix/with-notes")
    assert _kept(repo, open_pr, "fix/open")
    assert _kept(repo, unstarted, "fix/unstarted")
    assert _kept(repo, unfinished, "fix/unfinished")
    output = result.stdout if command[0] == "doctor" else result.stderr
    for folder in (dirty, open_pr):
        assert f"Forge kept the finished worktree at {folder.resolve().as_posix()}." in output.replace("\\", "/").splitlines()
    if command[0] == "lanes":
        assert result.returncode == 0, result.stderr
        json.loads(result.stdout)


def test_2_commands_list_finished_folders_kept_for_safety(repo, gh, tmp_path):
    _client(repo)
    deleted, deleted_head = _work(repo, tmp_path, "fix/deleted")
    advanced, advanced_head = _work(repo, tmp_path, "fix/advanced")
    dependency, _ = _work(repo, tmp_path, "fix/dependency", commit=False)
    remote = Path(repo.git("remote", "get-url", "origin"))
    repo.git("-c", "protocol.file.allow=always", "submodule", "add", remote.as_posix(),
             "dependency", cwd=dependency)
    repo.git("commit", "-qm", "Add a dependency", cwd=dependency)
    repo.git("merge", "--squash", "fix/dependency")
    repo.git("commit", "-qm", "Squash the dependency")
    repo.git("push", "-q", "origin", "main", "fix/deleted", "fix/advanced")
    repo.git("switch", "-qc", "fix/primary", advanced_head)
    repo.write("primary.txt", "A change in the primary checkout\n")
    repo.git("add", "primary.txt")
    repo.git("commit", "-qm", "Change the primary checkout")
    primary_head = repo.git("rev-parse", "HEAD")
    repo.git("push", "-q", "origin", ":refs/heads/fix/deleted", "HEAD:refs/heads/fix/advanced")
    _sweep_prs(gh, ("fix/dependency",), ("fix/deleted", deleted_head, "CLOSED"),
               ("fix/advanced", advanced_head, "CLOSED"), ("fix/primary", primary_head, "MERGED"))

    result = repo.forge("doctor")
    output = result.stdout.replace("\\", "/").splitlines()

    for branch, folder in (("fix/deleted", deleted), ("fix/advanced", advanced),
                           ("fix/dependency", dependency), ("fix/primary", repo.path)):
        assert _kept(repo, folder, branch)
        assert f"Forge kept the finished worktree at {folder.resolve().as_posix()}." in output, result.stdout
    assert (dependency / "dependency" / ".git").exists()


def _sweep_prs(gh, without_pr, *prs):
    response = json.loads(_pr_page(*prs))
    for branch in without_pr:
        response["data"]["repository"]["head_" + branch.encode().hex()] = {
            "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
    _prs(gh, stdout=json.dumps(response))


@pytest.mark.parametrize("command", ["close", "land", "merge"])
def test_3_named_commands_can_finish_an_already_merged_fix(env, command):
    item, folder = _ready(env)
    repo = env.repo
    branch = f"fix/{item}"
    head = repo.git("rev-parse", branch)
    repo.git("merge", "--squash", branch)
    repo.git("commit", "-qm", "Squash the fix")
    repo.git("push", "-q", "origin", "main", f":refs/heads/{branch}")
    if command == "land":
        repo.git("commit", "--allow-empty", "-qm", "Record local work", cwd=folder)
    _prs(env.gh, (branch, head, "MERGED"))
    env.open_pr("", state="MERGED")
    env.gh.respond("pr", "view", branch, stdout=json.dumps({
        "number": 7, "state": "MERGED", "baseRefName": "main", "headRefName": branch,
        "headRefOid": head, "title": "Tidy readme"}))

    result = repo.forge(command, item)

    assert result.returncode == 0, result.stdout + result.stderr
    if command == "merge":
        assert f"Merged {item}" in result.stdout
        assert _gone(repo, folder, branch)
    else:
        assert f"The pull request for {item} is merged." in result.stdout
