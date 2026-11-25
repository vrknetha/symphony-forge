"""Finished worktree cleanup through the public commands in FORGE-TIDYUP-1."""
import json
import os
import shutil
import sys

import pytest

from conftest import _install
from test_doctor_fix import FINISHED_PR_QUERY, _client, _gone, _kept, _pr_page, _prs, _work
from test_tools_session_hold import Session

STORY = "FORGE-TIDYUP-1"


@pytest.mark.platform
@pytest.mark.parametrize("command", ["next", "land", "start", "next with an older pin"])
def test_1_commands_remove_finished_folders(repo, gh, tmp_path, monkeypatch, command):
    _client(repo)
    clean, head = _work(repo, tmp_path, "fix/clean")
    dirty, dirty_head = _work(repo, tmp_path, "fix/dirty")
    current, current_head = _work(repo, tmp_path, "fix/current")
    (dirty / "notes.txt").write_text("Keep these notes.\n", encoding="utf-8")
    _prs(gh, ("fix/clean", head, "MERGED"), ("fix/dirty", dirty_head, "MERGED"),
         ("fix/current", current_head, "MERGED"))

    if command == "next with an older pin":
        (current / "forge.toml").write_text('version = "v1.0.0"\n', encoding="utf-8")
        done = repo.forge("next", cwd=current)
        assert "Removed " not in done.stdout and not gh.calls(*FINISHED_PR_QUERY)
        assert _kept(repo, clean, "fix/clean")
        return
    if command == "start":
        monkeypatch.delenv("CLAUDECODE", raising=False)
        monkeypatch.setenv("CODEX_THREAD_ID", "tidy-coordinator")
        owner = Session(repo, tmp_path / "tidy-host", "codex-tidy")
        try:
            done = owner.forge("start", "Make the greeting shorter", cwd=current)
        finally:
            owner.close()
        assert done.returncode == 0, done.stdout + done.stderr
        assert json.loads(done.stdout)["role"] == "explorer"
        output = done.stderr
    else:
        args = ("land", "--all") if command == "land" else ("next",)
        done = repo.forge(*args, cwd=current)
        output = done.stdout

    assert "Removed 1 finished folders." in output, done.stdout + done.stderr
    assert _gone(repo, clean, "fix/clean")
    assert _kept(repo, dirty, "fix/dirty")
    assert _kept(repo, current, "fix/current")
    assert len(gh.calls(*FINISHED_PR_QUERY)) == 1


def test_2_closed_folders_need_the_same_remote_head(repo, gh, tmp_path):
    _client(repo)
    kept, kept_head = _work(repo, tmp_path, "fix/no-remote")
    clean, head = _work(repo, tmp_path, "fix/on-remote")
    different, different_head = _work(repo, tmp_path, "fix/different-remote")
    repo.git("push", "-q", "origin", "fix/on-remote", "fix/no-remote", "main:fix/different-remote")
    repo.git("push", "-q", "origin", "--delete", "fix/no-remote")
    _prs(gh, ("fix/no-remote", kept_head, "CLOSED"), ("fix/on-remote", head, "CLOSED"),
         ("fix/different-remote", different_head, "CLOSED"))

    done = repo.forge("next")

    assert "Removed 1 finished folders." in done.stdout, done.stdout + done.stderr
    assert _kept(repo, kept, "fix/no-remote")
    assert _kept(repo, different, "fix/different-remote")
    assert _gone(repo, clean, "fix/on-remote")


def test_3_cleanup_preserves_an_edit_during_the_sweep(repo, gh, tmp_path):
    _client(repo)
    first, first_head = _work(repo, tmp_path, "fix/a-first")
    second, second_head = _work(repo, tmp_path, "fix/b-second")
    _prs(gh, ("fix/a-first", first_head, "MERGED"), ("fix/b-second", second_head, "MERGED"))
    notes = first / "notes.txt"
    # Run real Git. An editor writes just before Git tries the first removal.
    _install(repo.bin, "git", f"""#!{sys.executable}
import pathlib, subprocess, sys
if "remove" in sys.argv[1:-1] and pathlib.Path(sys.argv[-1]).resolve() == pathlib.Path({first.as_posix()!r}).resolve():
    pathlib.Path({notes.as_posix()!r}).write_text("New work", encoding="utf-8")
sys.exit(subprocess.call([{shutil.which("git")!r}, *sys.argv[1:]]))
""")

    done = repo.forge("next")

    assert _gone(repo, second, "fix/b-second"), done.stdout + done.stderr
    assert _kept(repo, first, "fix/a-first"), done.stdout + done.stderr
    assert notes.read_text(encoding="utf-8") == "New work"


def test_4_cleanup_keeps_a_legacy_worker_waiting_for_a_slot(repo, gh, tmp_path):
    _client(repo)
    queued, queued_head = _work(repo, tmp_path, "fix/queued")
    clean, head = _work(repo, tmp_path, "fix/clean")
    _prs(gh, ("fix/queued", queued_head, "MERGED"), ("fix/clean", head, "MERGED"))
    registry = tmp_path / "config" / "forge" / "agent-runs.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps([{"repo": queued.as_posix(), "kind": "work",
                                    "forge": {"pid": os.getpid()}, "agent": None}]), encoding="utf-8")

    done = repo.forge("next")

    assert _kept(repo, queued, "fix/queued"), done.stdout + done.stderr
    assert _gone(repo, clean, "fix/clean")


def test_5_cleanup_only_requests_pull_requests_for_local_folders(repo, gh, tmp_path):
    _client(repo)
    folder, head = _work(repo, tmp_path, "fix/cleanup")
    reopened, reopened_head = _work(repo, tmp_path, "fix/reopened")
    # Whole-history queries cannot finish within the cleanup deadline on this repo.
    gh.respond("pr", "list", "--state", "all", exit=1)
    first = json.loads(_pr_page(("fix/cleanup", head, "MERGED")))
    first["data"]["repository"].update(json.loads(_pr_page(
        ("fix/reopened", reopened_head, "MERGED"), more="reopened-page"))["data"]["repository"])
    _prs(gh, stdout=json.dumps(first))
    rules = json.loads(gh.responses.read_text(encoding="utf-8"))
    rules[-1]["then"] = [json.dumps(first), _pr_page(("fix/reopened", reopened_head, "OPEN"))]
    gh.responses.write_text(json.dumps(rules), encoding="utf-8")

    done = repo.forge("next")

    assert _gone(repo, folder, "fix/cleanup"), done.stdout + done.stderr
    assert _kept(repo, reopened, "fix/reopened")
    assert not gh.calls("pr", "list", "--state", "all")
    first_query, second_query = map(json.loads, (repo.bin / "gh-queries.jsonl")
                                   .read_text(encoding="utf-8").splitlines())
    assert 'headRefName: "fix/cleanup"' in first_query and 'headRefName: "fix/reopened"' in first_query
    assert 'headRefName: "fix/cleanup"' not in second_query
    assert 'headRefName: "fix/reopened", after: "reopened-page"' in second_query
