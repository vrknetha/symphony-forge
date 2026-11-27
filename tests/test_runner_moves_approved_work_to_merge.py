from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 1: after one approval, the background runner starts, builds and merges every
# unblocked part in order (or polls for a human merge), handles one-tool repos, retries short
# GitHub outages, skips CI and other-release repos, and enforces the per-item land lock.

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import GH_STUB, _install
from test_close import env  # noqa: F401
from test_land import COMMITS, URL, _agent, land  # noqa: F401
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

OVERLAP_ONE = TWO_PART_PLAN.replace(
    "| ONE | First part | First change | 1 | `one.txt` | none | | no | |\n"
    "| TWO | Second part | Second change | 2 | `two.txt` | none | ONE | no | |",
    "| ONE | First part | First change | 1, 2 | `shared.txt` | none | | no | |",
)

MULTI_GH = '''#!{python}
import json, pathlib, re, subprocess, sys
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


if args[:2] == ["api", "graphql"] and "query=@-" in args:
    query = sys.stdin.read()
    if "FinishedFolders" in query:
        repo_heads = heads()
        pages = {{}}
        for alias, branch in re.findall(r'(\\w+): pullRequests\\(first: 25, headRefName: "([^"]+)"', query):
            mf = merged_file(branch)
            if mf.exists():
                nodes = [{{"headRefOid": mf.read_text("utf-8"), "state": "MERGED"}}]
            elif "refs/heads/" + branch in repo_heads:
                nodes = [{{"headRefOid": repo_heads["refs/heads/" + branch], "state": "OPEN"}}]
            else:
                nodes = []
            pages[alias] = {{"nodes": nodes, "pageInfo": {{"hasNextPage": False, "endCursor": None}}}}
        answer(json.dumps({{"data": {{"repository": pages}}}}))
    sys.exit(1)

fail_view = here / "gh-fail-pr-view"
if fail_view.exists() and args[:2] == ["pr", "view"] and len(args) > 2 and args[2] == "fix/retry-fix":
    raw = fail_view.read_text("utf-8").strip().split("|", 1)
    n = int(raw[0])
    msg = raw[1] if len(raw) > 1 else "error connecting to api.github.com"
    if n > 0:
        fail_view.write_text(f"{{n - 1}}|{{msg}}", "utf-8")
        answer("", 1, msg + "\\n")

fail_list = here / "gh-fail-pr-list"
if fail_list.exists() and args[:2] == ["pr", "list"] and "--head" in args and args[args.index("--head") + 1] == "fix/retry-fix":
    raw = fail_list.read_text("utf-8").strip().split("|", 1)
    n = int(raw[0])
    msg = raw[1] if len(raw) > 1 else "error connecting to api.github.com"
    if n > 0:
        fail_list.write_text(f"{{n - 1}}|{{msg}}", "utf-8")
        answer("", 1, msg + "\\n")

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
    # Ensure every runner test keeps machine-wide config inside tmp_path.
    assert Path(os.environ.get("APPDATA" if os.name == "nt" else "XDG_CONFIG_HOME", "")).resolve() == (
        tmp_path / "config").resolve()
    _install(env.repo.bin, "gh", MULTI_GH.format(
        python=sys.executable, remote=str(tmp_path / "remote.git"), url=URL)
        + GH_STUB.format(python=sys.executable).split("\n", 1)[1])
    _install_process_tracker(env, tmp_path)


def _mark_installed_before(tmp_path: Path, stamp: str = "2020-01-01T00:00:00+00:00") -> None:
    path = tmp_path / "config" / "forge" / "runner-installed-at"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stamp + "\n", encoding="utf-8")


def _install_process_tracker(env, tmp_path: Path) -> None:
    """Record every detached runner and runner child in *.owned-process.json for crash cleanup,
    and log every Popen call launching forge.runner so CI-skip tests are deterministic."""
    snippet = (
        "\nimport json as _j, os as _o, pathlib as _p, subprocess as _sp, sys as _s, time as _t\n"
        f"_runner_tmp = _p.Path({tmp_path.as_posix()!r})\n"
        "if _s.argv[:1] == ['-c'] or _o.environ.get('FORGE_RUNNER') == '1':\n"
        "    _runner_tmp.joinpath(f'runner-{_o.getpid()}.owned-process.json').write_text(\n"
        "        _j.dumps({'pid': _o.getpid(), 'at_ns': _t.time_ns()}), encoding='utf-8')\n"
        "_orig_popen = _sp.Popen\n"
        "class _TrackedPopen(_orig_popen):\n"
        "    def __init__(self, args, *a, **kw):\n"
        "        super().__init__(args, *a, **kw)\n"
        "        text = ' '.join(map(str, args)) if isinstance(args, (list, tuple)) else str(args)\n"
        "        env_map = kw.get('env') or {}\n"
        "        if 'forge.runner' in text or env_map.get('FORGE_RUNNER') == '1':\n"
        "            _runner_tmp.joinpath(f'runner-{self.pid}.owned-process.json').write_text(\n"
        "                _j.dumps({'pid': self.pid, 'at_ns': _t.time_ns()}), encoding='utf-8')\n"
        "        if 'forge.runner' in text:\n"
        "            with _runner_tmp.joinpath('runner-spawns.jsonl').open('a', encoding='utf-8') as _f:\n"
        "                _f.write(_j.dumps({'pid': self.pid}) + '\\n')\n"
        "_sp.Popen = _TrackedPopen\n"
    )
    for target in (env.repo.bin / "sitecustomize.py", tmp_path / "clock" / "sitecustomize.py"):
        if target.parent.is_dir():
            existing = target.read_text("utf-8") if target.exists() else ""
            if "_TrackedPopen" not in existing:
                target.write_text(existing + snippet, encoding="utf-8")


@pytest.fixture(autouse=True)
def runner_cleanup(tmp_path: Path):
    """Ensure any detached runner or child spawned in a test is terminated on teardown."""
    yield
    pids: set[int] = set()
    info = tmp_path / "config" / "forge" / "runner.json"
    if info.exists():
        try:
            pid = json.loads(info.read_text("utf-8")).get("pid")
            if isinstance(pid, int):
                pids.add(pid)
        except (OSError, ValueError):
            pass
    for marker in tmp_path.glob("runner-*.owned-process.json"):
        try:
            pid = json.loads(marker.read_text("utf-8")).get("pid")
            if isinstance(pid, int):
                pids.add(pid)
        except (OSError, ValueError):
            pass
    for pid in pids:
        if pid == os.getpid():
            continue
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True, timeout=10)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not _lock_is_free(_runner_lock(tmp_path)):
        time.sleep(0.05)


def _runner_lock(tmp_path: Path) -> Path:
    return tmp_path / "config" / "forge" / "runner.lock"


def _runner_started(tmp_path: Path) -> bool:
    return _runner_lock(tmp_path).exists()


def _lock_is_free(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        with path.open("ab") as handle:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    return False
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                return True
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            fcntl.flock(handle, fcntl.LOCK_UN)
            return True
    except OSError:
        return False


def _runner_exited(tmp_path: Path) -> bool:
    """True only once the detached runner actually started, removed runner.json, and freed its lock."""
    return (
        _runner_started(tmp_path)
        and not (tmp_path / "config" / "forge" / "runner.json").exists()
        and _lock_is_free(_runner_lock(tmp_path))
    )


def _wait_for(predicate, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for background runner condition")


def _runner_log(env) -> str:
    log = env.repo.path / ".git" / "forge" / "runner.log"
    return log.read_text("utf-8") if log.exists() else ""


def _human_merge(env, tmp_path: Path, branch: str) -> None:
    """Simulate a person merging a pull request on GitHub (squash into origin/main + stub state)."""
    remote = tmp_path / "remote.git"
    checkout = tmp_path / ("human-merge-" + branch.replace("/", "-"))
    if checkout.exists():
        import shutil
        shutil.rmtree(checkout)
    subprocess.run(["git", "clone", "-q", str(remote), str(checkout)], check=True,
                   stdin=subprocess.DEVNULL, timeout=60)
    listed = subprocess.run(["git", "ls-remote", "--heads", str(remote), f"refs/heads/{branch}"],
                            capture_output=True, text=True, check=True,
                            stdin=subprocess.DEVNULL, timeout=60).stdout.split()
    head = listed[0]
    for step in (["fetch", "-q", "origin", f"refs/heads/{branch}"],
                 ["merge", "-q", "--squash", "FETCH_HEAD"],
                 ["commit", "-q", "-m", f"Merge {branch}"],
                 ["push", "-q", "origin", "main"]):
        subprocess.run(["git", *step], cwd=checkout, check=True, capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    (env.repo.bin / ("merged-" + branch.replace("/", "-"))).write_text(head, "utf-8")
    (env.repo.bin / "last-merged").write_text(branch, "utf-8")


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


def _approve(env, folder: Path, plan: str, claude_payload, monkeypatch) -> None:
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    plan_text = plan.split("## For the builders")[0].strip()
    payload = claude_payload("PostToolUse", "ExitPlanMode", {"plan": plan_text},
                             {"plan": plan_text, "isAgent": False}, cwd=folder)
    approved = env.repo.forge("hook", "approval", input=json.dumps(payload), cwd=folder)
    assert approved.returncode == 0, approved.stderr


@pytest.mark.platform
@pytest.mark.parametrize("case", [
    "two_part_agent_merge",
    "two_part_human_merge",
    "human_merge_stops_after_24h",
    "overlapping_scope",
    "coordinator_task_start",
    "one_tool_no_session",
    "ci_skips_runner",
    "worker_env_skips_runner",
    "older_started_fix_left_alone",
    "never_acts_outside_temp_folder",
    "other_pin_skipped",
    "land_lock_refuses_second_run",
    "network_retry_merges",
    "failed_land_no_restart_loop",
])
def test_1_runner_moves_approved_work_to_merge(case, land, tmp_path, monkeypatch, claude_payload, request):
    if case in ("two_part_human_merge", "human_merge_stops_after_24h"):
        request.getfixturevalue("fake_clock")
        # Keep the runner's fake_clock tick advances from timing out checks.wait inside a child land run.
        monkeypatch.setenv("FORGE_CHECKS_WAIT", "999999999")
    _install_multi_gh(land, tmp_path)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "30" if case == "two_part_human_merge"
                       else "300" if case == "human_merge_stops_after_24h" else "0.05")
    monkeypatch.setenv("FORGE_NETWORK_RETRY_WAIT", "0")

    if case == "never_acts_outside_temp_folder":
        # A runner started under pytest must refuse to act on any repo outside FORGE_TEST_ROOT.
        _agent(land)
        _mark_installed_before(tmp_path)
        assert land.repo.forge("fix", "start", "Outside fix", "--done", "Never touched", "--slug", "outside-fix").returncode == 0
        # Narrow FORGE_TEST_ROOT to a separate subfolder so land.repo.path sits outside it,
        # and also list land.repo.path in the test's repos file.
        inner = tmp_path / "inner-only"
        inner.mkdir()
        inner_repo = inner / "empty"
        inner_repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(inner_repo)], check=True, stdin=subprocess.DEVNULL)
        version = land.repo.forge("--version").stdout.split()[-1]
        (inner_repo / "forge.toml").write_text(f'version = "{version}"\n', encoding="utf-8")
        repos_file = tmp_path / "config" / "forge" / "repos"
        repos_file.parent.mkdir(parents=True, exist_ok=True)
        repos_file.write_text(f"{land.repo.path.resolve()}\n{inner_repo.resolve()}\n", encoding="utf-8")
        monkeypatch.setenv("FORGE_TEST_ROOT", str(inner.resolve()))
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        assert land.repo.forge("lanes", cwd=inner_repo).returncode == 0
        _wait_for(lambda: _runner_exited(tmp_path))
        assert not (land.repo.path / ".git" / "forge" / "runner.log").exists()
        assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        assert not (land.repo.bin / "merged-fix-outside-fix").exists()
        return

    if case == "older_started_fix_left_alone":
        # A fix started before the runner was installed on this machine is left alone.
        _agent(land)
        monkeypatch.setenv("FORGE_NOW", "2025-01-01T00:00:00+00:00")
        assert land.repo.forge("fix", "start", "Old fix", "--done", "Stays untouched", "--slug", "old-fix").returncode == 0
        monkeypatch.delenv("FORGE_NOW", raising=False)
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        assert land.repo.forge("lanes").returncode == 0
        _wait_for(lambda: _runner_exited(tmp_path))
        assert (tmp_path / "config" / "forge" / "runner-installed-at").exists()
        assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        assert (tmp_path / "repo-fix-old-fix").exists()
        assert not (land.repo.bin / "merged-fix-old-fix").exists()
        return

    if case == "worker_env_skips_runner":
        _agent(land)
        _mark_installed_before(tmp_path)
        assert land.repo.forge("fix", "start", "Worker check", "--done", "Not built from worker", "--slug", "worker-fix").returncode == 0
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        monkeypatch.setenv("FORGE_WORKER", "1")
        assert land.repo.forge("lanes").returncode == 0
        assert not (tmp_path / "runner-spawns.jsonl").exists()
        assert not _runner_started(tmp_path)
        assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        assert not (land.repo.bin / "merged-fix-worker-fix").exists()
        return

    if case == "ci_skips_runner":
        _agent(land)
        _mark_installed_before(tmp_path)
        # Start a fix while runner is disabled, then wake under CI=true: wake() must never spawn a runner.
        assert land.repo.forge("fix", "start", "CI check", "--done", "Not built in CI", "--slug", "ci-fix").returncode == 0
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        monkeypatch.setenv("CI", "true")
        assert land.repo.forge("lanes").returncode == 0
        # Deterministic check: Popen for forge.runner was never called inside forge lanes.
        assert not (tmp_path / "runner-spawns.jsonl").exists()
        assert not _runner_started(tmp_path)
        assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        assert not (land.repo.bin / "merged-fix-ci-fix").exists()
        # Removing CI proves the exact same command now spawns and tracks a runner that merges the fix.
        monkeypatch.delenv("CI", raising=False)
        assert land.repo.forge("lanes").returncode == 0
        _wait_for(lambda: (land.repo.bin / "merged-fix-ci-fix").exists() and _runner_exited(tmp_path))
        assert (tmp_path / "runner-spawns.jsonl").exists()
        assert list(tmp_path.glob("runner-*.owned-process.json"))
        return

    if case == "other_pin_skipped":
        _agent(land)
        _mark_installed_before(tmp_path)
        assert land.repo.forge("fix", "start", "Old pin fix", "--done", "Left alone", "--slug", "other-pin").returncode == 0
        toml = land.repo.path / "forge.toml"
        lines = toml.read_text("utf-8").splitlines()
        toml.write_text("\n".join(['version = "v0.0.1"', *lines[1:]]) + "\n", "utf-8")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        assert land.repo.forge("lanes").returncode == 0
        # Wait for the runner to actually start, skip the older-pin repo, and exit idle.
        _wait_for(lambda: _runner_exited(tmp_path))
        assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
        assert (tmp_path / "repo-fix-other-pin").exists()
        assert not (land.repo.bin / "merged-fix-other-pin").exists()
        return

    if case == "land_lock_refuses_second_run":
        _agent(land)
        assert land.repo.forge("fix", "start", "Lock check", "--done", "Lock tested", "--slug", "lock-check").returncode == 0
        lock_file = land.repo.path / ".git" / "forge" / "land-lock-check.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        holder_code = (
            f"import pathlib, sys, time\n"
            f"p = pathlib.Path({lock_file.as_posix()!r})\n"
            f"f = p.open('ab')\n"
            "if sys.platform == 'win32':\n"
            "    import msvcrt; f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)\n"
            "else:\n"
            "    import fcntl; fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "print('LOCKED', flush=True)\n"
            "time.sleep(10)\n"
        )
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
        _wait_for(lambda: (land.repo.bin / "merged-fix-one-tool").exists() and _runner_exited(tmp_path))
        assert not (tmp_path / "repo-fix-one-tool").exists()
        return

    if case == "network_retry_merges":
        _agent(land)
        # Fail `pr view fix/retry-fix` 4 times (past github.py's built-in retries for one land run),
        # so land exits non-zero with "GitHub did not answer" + "needs you", and runner retries and merges.
        (land.repo.bin / "gh-fail-pr-view").write_text("4", "utf-8")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        done = land.repo.forge("fix", "start", "Retry fix", "--done", "Merged after outage", "--slug", "retry-fix")
        assert done.returncode == 0, done.stderr
        _wait_for(lambda: (land.repo.bin / "merged-fix-retry-fix").exists() and _runner_exited(tmp_path))
        log = _runner_log(land)
        # Prove the first land run failed with GitHub unavailable and a second land run succeeded.
        assert log.count("Building retry-fix.") >= 2 or log.count("Closing retry-fix.") >= 2, log
        assert "GitHub did not answer" in log or "error connecting to" in log, log
        return

    if case == "failed_land_no_restart_loop":
        # Shared seam crossing test: non-zero land exits pass with no crash and no restart loop.
        _agent(land)
        monkeypatch.setenv("STUB_CLAUDE_EXIT", "3")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        done = land.repo.forge("fix", "start", "Failing fix", "--done", "Stops cleanly", "--slug", "fail-once")
        assert done.returncode == 0, done.stderr
        _wait_for(lambda: _runner_exited(tmp_path))
        assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == 1
        return

    if case == "coordinator_task_start":
        _agent(land)
        _mark_installed_before(tmp_path)
        folder = _setup_two_part_story(land)
        _approve(land, folder, TWO_PART_PLAN, claude_payload, monkeypatch)
        # Coordinator starts ONE by hand before runner wakes: must cause no stop.
        assert land.repo.forge("task", "start", "SHOP-1/ONE").returncode == 0
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        assert land.repo.forge("lanes").returncode == 0
        _wait_for(lambda: (land.repo.bin / "merged-task-SHOP-1-TWO").exists() and _runner_exited(tmp_path), timeout=45.0)
        assert not (tmp_path / "repo-SHOP-1-ONE").exists()
        assert not (tmp_path / "repo-SHOP-1-TWO").exists()
        return

    if case == "overlapping_scope":
        _agent(land)
        _mark_installed_before(tmp_path)
        land.approve_working_build()
        land.commit(land.repo.path, "plans/roadmap.json", json.dumps({"items": [
            {"key": "SHOP-1", "title": "First story"},
            {"key": "SHOP-2", "title": "Second story"},
        ]}), "Add two stories to roadmap")
        land.repo.git("push", "-q", "origin", "main")
        folders = []
        for key in ("SHOP-1", "SHOP-2"):
            plan = OVERLAP_ONE.replace("First part lands", f"{key} lands")
            folder = land.tmp / f"repo-story-{key}"
            land.repo.git("worktree", "add", "-q", "-b", f"story/{key}", str(folder))
            land.commit(folder, f".factory/stories/{key}/story.json",
                        json.dumps({"key": key, "title": key, "status": "planning", "branch": f"story/{key}"}),
                        f"Start {key}")
            land.commit(folder, f"plans/{key}.md", plan, f"Write {key} plan")
            doc_hash = land.repo.git("hash-object", f"plans/{key}.md", cwd=folder)
            land.commit(folder, f"plans/{key}.read.md",
                        f"---\nround: 1\nread_hash: {doc_hash}\n---\n\n## Round 1\n\nNo findings.\n", "Clean cold read")
            land.repo.git("push", "-q", "-u", "origin", f"story/{key}", cwd=folder)
            folders.append((folder, plan))
        _approve(land, folders[0][0], folders[0][1], claude_payload, monkeypatch)
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        _approve(land, folders[1][0], folders[1][1], claude_payload, monkeypatch)
        _wait_for(lambda: (land.repo.bin / "merged-task-SHOP-1-ONE").exists()
                  and (land.repo.bin / "merged-task-SHOP-2-ONE").exists()
                  and _runner_exited(tmp_path), timeout=60.0)
        log = _runner_log(land)
        # Overlapping parts from two stories never run together: the second starts only after the first merges.
        first, second = (("SHOP-1/ONE", "SHOP-2/ONE")
                         if log.index("Started SHOP-1/ONE") < log.index("Started SHOP-2/ONE")
                         else ("SHOP-2/ONE", "SHOP-1/ONE"))
        assert log.index(f"Merged {first}") < log.index(f"Started {second}"), log
        return

    if case == "human_merge_stops_after_24h":
        # Default merge = "human": even after recovering from a transient 503 failure, an unmerged PR
        # stops polling after 24h, clears its retry entry, never re-lands, and exits cleanly.
        (land.repo.bin / "gh-fail-pr-list").write_text("1|The requested URL returned error: 503", "utf-8")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        done = land.repo.forge("fix", "start", "Stale PR", "--done", "Stops after 24h", "--slug", "retry-fix")
        assert done.returncode == 0, done.stderr
        _wait_for(lambda: _runner_exited(tmp_path), timeout=45.0)
        log = _runner_log(land)
        assert "The requested URL returned error: 503" in log, log
        assert log.count("retry-fix is ready; a human merges") == 1, log
        return

    if case == "two_part_human_merge":
        # Default merge = "human" with stack = "on": ONE becomes ready, TWO never stacks on ONE,
        # polling stays quiet between intervals, and TWO starts only after the human merges ONE.
        _agent(land, 'merge = "human"\nstack = "on"\n')
        folder = _setup_two_part_story(land)
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
        _approve(land, folder, TWO_PART_PLAN, claude_payload, monkeypatch)
        _wait_for(lambda: "SHOP-1/ONE is ready; a human merges" in _runner_log(land), timeout=45.0)
        assert not (tmp_path / "repo-SHOP-1-TWO").exists()
        # Human merges ONE; runner polls, removes ONE's folder, starts TWO unstacked, and makes TWO ready.
        _human_merge(land, tmp_path, "task/SHOP-1-ONE")
        _wait_for(lambda: "SHOP-1/TWO is ready; a human merges" in _runner_log(land), timeout=45.0)
        assert not (tmp_path / "repo-SHOP-1-ONE").exists()
        two_state = json.loads((tmp_path / "repo-SHOP-1-TWO" / ".factory/stories/SHOP-1/tasks/TWO.json").read_text("utf-8"))
        assert "stacked_on" not in two_state
        # Human merges TWO; runner polls, removes TWO's folder, and exits idle.
        _human_merge(land, tmp_path, "task/SHOP-1-TWO")
        _wait_for(lambda: not (tmp_path / "repo-SHOP-1-TWO").exists() and _runner_exited(tmp_path), timeout=45.0)
        return

    # two_part_agent_merge: approve via forge hook approval, runner starts & merges both in order.
    _agent(land)
    folder = _setup_two_part_story(land)
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)
    _approve(land, folder, TWO_PART_PLAN, claude_payload, monkeypatch)
    _wait_for(lambda: (land.repo.bin / "merged-task-SHOP-1-TWO").exists() and _runner_exited(tmp_path), timeout=45.0)
    order = [json.loads(line) for line in (land.repo.bin / "merge-order.jsonl").read_text("utf-8").splitlines()]
    assert order == ["task/SHOP-1-ONE", "task/SHOP-1-TWO"]
    assert not (tmp_path / "repo-SHOP-1-ONE").exists()
    assert not (tmp_path / "repo-SHOP-1-TWO").exists()
