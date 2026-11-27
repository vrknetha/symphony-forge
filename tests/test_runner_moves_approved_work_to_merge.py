from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 1: after one approval, the background runner starts, builds and merges every
# unblocked part in order (or polls for a human merge), handles one-tool repos, retries short
# GitHub outages, skips CI and other-release repos, and enforces the per-item land lock.

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import GH_STUB, _install
from test_land import COMMITS, URL, _agent, land  # noqa: F401
from test_close import env  # noqa: F401
from test_worker import calls

TWO_PART_PLAN = """# Two-part story

## What changes for you

- First part lands, then second part lands.

Design: none (no screen)

## Why

Need both parts in order.

## Done when

1. First part is done.
2. Second part is done.

## For the builders

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ONE | First part | First change | 1 | `one.txt` | none | | no | |
| TWO | Second part | Second change | 2 | `two.txt` | none | ONE | no | |

New moving parts: none

## Risks

Risks: none.
"""

MULTI_GH = '''#!{python}
import json, pathlib, subprocess, sys
here = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
remote = {remote!r}


def answer(out, code=0, err=""):
    with open(here / "gh-calls.jsonl", "a", encoding="utf-8") as log:
        log.write(json.dumps(args) + "\\n")
    sys.stdout.write(out)
    sys.stderr.write(err)
    sys.exit(code)


def heads():
    listed = subprocess.run(["git", "ls-remote", "--heads", remote], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL, timeout=60).stdout.split()
    return dict(zip(listed[1::2], listed[0::2]))


def merged_file(branch):
    return here / ("merged-" + branch.replace("/", "-"))


fail_once = here / "gh-fail-once"
if fail_once.exists() and args[:2] in (["pr", "view"], ["pr", "list"], ["pr", "create"]):
    n = int(fail_once.read_text("utf-8").strip())
    if n > 0:
        fail_once.write_text(str(n - 1), "utf-8")
        answer("", 1, "error connecting to api.github.com\\n")

if args[:2] == ["pr", "list"] and "--head" in args:
    branch = args[args.index("--head") + 1]
    mf = merged_file(branch)
    if mf.exists():
        answer(json.dumps([{{"number": 7, "state": "MERGED", "body": "", "isDraft": False}}]))
if args[:2] == ["pr", "view"]:
    ref = args[2]
    if ref.isdigit():
        last = here / "last-merged"
        state = "MERGED" if last.exists() else "OPEN"
        if "--jq" in args:
            answer(state + "\\n")
        answer(json.dumps({{"number": int(ref), "state": state, "baseRefName": "main",
                           "headRefName": last.read_text("utf-8") if last.exists() else "",
                           "headRefOid": "", "title": ref, "isDraft": False, "url": {url!r}}}))
    branch = ref
    mf = merged_file(branch)
    state = "MERGED" if mf.exists() else "OPEN"
    oid = mf.read_text("utf-8") if mf.exists() else heads().get("refs/heads/" + branch, "")
    if "--jq" in args:
        answer(state + "\\n")
    answer(json.dumps({{"number": 7, "state": state, "baseRefName": "main", "headRefName": branch,
                       "headRefOid": oid, "title": branch, "isDraft": False, "url": {url!r}}}))
if args[:2] == ["pr", "merge"]:
    head = args[args.index("--match-head-commit") + 1]
    branch = next((ref for ref, oid in heads().items() if oid == head), None)
    if branch is None:
        answer("", 1)
    short = branch.removeprefix("refs/heads/")
    checkout = here / ("github-merge-" + short.replace("/", "-"))
    subprocess.run(["git", "clone", "-q", remote, str(checkout)], check=True,
                   stdin=subprocess.DEVNULL, timeout=60)
    for step in (["fetch", "-q", "origin", branch], ["merge", "-q", "--squash", "FETCH_HEAD"],
                 ["commit", "-q", "-m", args[args.index("--subject") + 1]],
                 ["push", "-q", "origin", "main"]):
        subprocess.run(["git", *step], cwd=checkout, check=True, capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    merged_file(short).write_text(head, "utf-8")
    (here / "last-merged").write_text(short, "utf-8")
    with open(here / "merge-order.jsonl", "a", encoding="utf-8") as log:
        log.write(json.dumps(short) + "\\n")
    answer("")
'''


def _install_multi_gh(env, tmp_path: Path) -> None:
    _install(env.repo.bin, "gh", MULTI_GH.format(
        python=sys.executable, remote=str(tmp_path / "remote.git"), url=URL)
        + GH_STUB.format(python=sys.executable).split("\n", 1)[1])


def _wait_for(predicate, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError("Timed out waiting for background runner condition")


def _runner_gone(tmp_path: Path) -> bool:
    return not (tmp_path / "config" / "forge" / "runner.json").exists()


def _setup_two_part_story(env, key: str = "SHOP-1", plan: str = TWO_PART_PLAN) -> Path:
    env.approve_working_build()
    env.commit(env.repo.path, "plans/roadmap.json", json.dumps({"items": [{"key": key, "title": "Two-part story"}]}),
               "Add story to roadmap")
    env.repo.git("push", "-q", "origin", "main")
    folder = env.tmp / f"repo-story-{key}"
    env.repo.git("worktree", "add", "-q", "-b", f"story/{key}", str(folder))
    env.commit(folder, f".factory/stories/{key}/story.json",
               json.dumps({"key": key, "title": "Two-part story", "status": "planning", "branch": f"story/{key}"}),
               f"Start {key}")
    env.commit(folder, f"plans/{key}.md", plan, f"Write {key} plan")
    doc_hash = env.repo.git("hash-object", f"plans/{key}.md", cwd=folder)
    env.commit(folder, f"plans/{key}.read.md",
               f"---\nround: 1\nread_hash: {doc_hash}\n---\n\n## Round 1\n\nNo findings.\n", "Clean cold read")
    env.repo.git("push", "-q", "-u", "origin", f"story/{key}", cwd=folder)
    return folder


@pytest.mark.parametrize("case", [
    "two_part_agent_merge",
    "one_tool_no_session",
    "ci_skips_runner",
    "other_pin_skipped",
    "land_lock_refuses_second_run",
    "network_retry_merges",
])
def test_1_runner_moves_approved_work_to_merge(case, land, tmp_path, monkeypatch, claude_payload):
    _install_multi_gh(land, tmp_path)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.setenv("FORGE_NETWORK_RETRY_WAIT", "0")

    if case == "ci_skips_runner":
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        monkeypatch.setenv("CI", "true")
        assert land.repo.forge("lanes").returncode == 0
        time.sleep(0.2)
        assert _runner_gone(tmp_path)
        return

    if case == "other_pin_skipped":
        _agent(land)
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        assert land.repo.forge("fix", "start", "Small tweak", "--done", "Tweak done", "--slug", "other-pin").returncode == 0
        toml = land.repo.path / "forge.toml"
        toml.write_text(toml.read_text("utf-8").replace(
            toml.read_text("utf-8").splitlines()[0], 'version = "v0.0.1"'), "utf-8")
        # Runner skips repos pinned to another release and exits idle.
        _wait_for(lambda: _runner_gone(tmp_path))
        return

    if case == "land_lock_refuses_second_run":
        _agent(land)
        assert land.repo.forge("fix", "start", "Lock check", "--done", "Lock tested", "--slug", "lock-check").returncode == 0
        # Hold the item's land lock from a child process and verify hand-run `forge land` refuses.
        lock_file = land.repo.path / ".git" / "forge" / "land-lock-check.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        holder_code = (
            f"import fcntl, pathlib, sys, time\n"
            f"p = pathlib.Path({str(lock_file)!r})\n"
            f"f = p.open('ab')\n"
            f"fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            f"print('LOCKED', flush=True)\n"
            f"time.sleep(10)\n"
        )
        if os.name == "nt":
            pytest.skip("fcntl lock holder test runs on POSIX")
        holder = subprocess.Popen([sys.executable, "-c", holder_code], stdout=subprocess.PIPE, text=True)
        try:
            assert holder.stdout.readline().strip() == "LOCKED"
            refused = land.repo.forge("land", "lock-check")
            assert refused.returncode != 0
            assert "Another land run is working on lock-check." in refused.stderr
            assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        finally:
            holder.terminate()
            holder.wait(timeout=5)
        return

    if case == "one_tool_no_session":
        _agent(land, 'merge = "agent"\ntools = "claude"\n')
        monkeypatch.delenv("CLAUDECODE", raising=False)
        monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        done = land.repo.forge("fix", "start", "One tool fix", "--done", "One tool merged", "--slug", "one-tool")
        assert done.returncode == 0, done.stderr
        _wait_for(lambda: (land.repo.bin / "merged-fix-one-tool").exists() and _runner_gone(tmp_path))
        assert not (tmp_path / "repo-fix-one-tool").exists()
        return

    if case == "network_retry_merges":
        _agent(land)
        (land.repo.bin / "gh-fail-once").write_text("4", "utf-8")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        done = land.repo.forge("fix", "start", "Retry fix", "--done", "Merged after outage", "--slug", "retry-fix")
        assert done.returncode == 0, done.stderr
        _wait_for(lambda: (land.repo.bin / "merged-fix-retry-fix").exists() and _runner_gone(tmp_path))
        return

    # two_part_agent_merge: approve via forge hook approval, runner starts & merges both in order
    _agent(land)
    folder = _setup_two_part_story(land)
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    plan_text = TWO_PART_PLAN.split("## For the builders")[0].strip()
    payload = claude_payload("PostToolUse", "ExitPlanMode", {"plan": plan_text},
                             {"plan": plan_text, "isAgent": False}, cwd=folder)
    approved = land.repo.forge("hook", "approval", input=json.dumps(payload), cwd=folder)
    assert approved.returncode == 0, approved.stderr
    _wait_for(lambda: (land.repo.bin / "merged-task-SHOP-1-TWO").exists() and _runner_gone(tmp_path), timeout=45.0)
    order = [json.loads(line) for line in (land.repo.bin / "merge-order.jsonl").read_text("utf-8").splitlines()]
    assert order == ["task/SHOP-1-ONE", "task/SHOP-1-TWO"]
    assert not (tmp_path / "repo-SHOP-1-ONE").exists()
    assert not (tmp_path / "repo-SHOP-1-TWO").exists()
