"""Background runner: moves approved stories and started fixes to merge without an open chat."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from forge import __version__, board, codex, doctor, land, machine, nextstep, repo, stops, story, task

_SKIP_ENV = ("FORGE_NO_RUNNER", "FORGE_WORKER", "FORGE_RUNNER", "CI")
_POLL_INITIAL = 60.0
_POLL_CAP = 1800.0
_POLL_MAX_AGE = 86400.0


def _state_dir() -> Path:
    return machine._repos_file().parent


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def _child_cmd(args: list[str]) -> list[str]:
    src = str(Path(__file__).resolve().parents[1])
    code = (f"import sys; sys.path.insert(0, {src!r}); "
            "from forge.cli import main; raise SystemExit(main())")
    return [sys.executable, "-c", code, *args]


def _runner_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CODEX_THREAD_ID")}
    if extra:
        env.update(extra)
    return env


def wake(cwd: Path) -> None:
    """Start the background runner, or nudge it if one is already alive."""
    if any(os.environ.get(name) for name in _SKIP_ENV):
        return
    try:
        top = machine.main_checkout(cwd)
    except Exception:
        return
    if not (top / "forge.toml").is_file():
        return
    machine.remember(top)
    state_dir = _state_dir()
    info = _read_json(state_dir / "runner.json")
    if info.get("pid") and codex._alive(info) is not False:
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "runner.wake").touch()
        except OSError:
            pass
        return
    src = str(Path(__file__).resolve().parents[1])
    code = (f"import sys; sys.path.insert(0, {src!r}); "
            "from forge.runner import main; raise SystemExit(main())")
    kwargs: dict[str, Any] = (
        {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt" else {"start_new_session": True})
    try:
        subprocess.Popen([sys.executable, "-c", code], cwd=top, env=_runner_env(),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **kwargs)
    except OSError:
        pass


def _local_started(top: Path) -> list[tuple[str, str, Path, dict[str, Any]]]:
    """Started, non-dropped task/fix worktrees in this repo: (item, branch, tree, state)."""
    found = []
    for branch, tree in story.worktrees(top).items():
        if branch.startswith("story/"):
            continue
        entry = task.branch_item(branch, tree)
        if not entry:
            continue
        item, state = entry
        if state.get("status") != "dropped":
            found.append((item, branch, tree, state))
    return found


def _has_approved_unstarted(top: Path) -> bool:
    """Local-only check: any approved story with a task not yet merged on the default branch."""
    landed = story.landed_ref(top)
    keys = set(story.stories_here(top))
    refs = repo.run("git", "for-each-ref", "--format=%(refname)",
                    "refs/heads/story/", "refs/remotes/origin/story/", cwd=top).stdout.splitlines()
    keys.update(ref.split("/story/", 1)[1] for ref in refs)
    ls = repo.run("git", "ls-tree", "-r", "--name-only", landed, "--", ".factory/stories", cwd=top)
    paths = set(ls.stdout.splitlines()) if ls.returncode == 0 else set()
    keys.update(p.split("/")[2] for p in paths if p.endswith("/story.json"))
    for key in keys:
        ref = story.plan_ref(top, key)
        record = story.state_of(top, key, ref)
        if record.get("status") in ("done", "dropped") or not (record.get("approval") or {}).get("hash"):
            continue
        doc = story._plan(top, key)
        if not doc:
            continue
        for tid in task.rows(task.sections(doc)):
            if repo.state_path(f"{key}/{tid}") not in paths:
                return True
    return False


def _lock_free(top: Path, item: str) -> bool:
    lock_path = repo.forge_dir(top) / f"land-{item.replace('/', '-')}.lock"
    try:
        with lock_path.open("ab") as handle:
            if not codex._try_lock(handle):
                return False
            codex._unlock(handle)
            return True
    except OSError:
        return False


def _log_append(top: Path, text: str) -> None:
    try:
        with (repo.forge_dir(top) / "runner.log").open("a", encoding="utf-8") as out:
            out.write(text)
    except OSError:
        pass


def _spawn_land(top: Path, item: str) -> tuple[subprocess.Popen[str], threading.Thread, list[str]]:
    env = _runner_env({"FORGE_RUNNER": "1"})
    proc = subprocess.Popen(
        _child_cmd(["land", item]), cwd=top, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    lines: list[str] = []

    def relay() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            _log_append(top, f"[{item}] {line}")

    reader = threading.Thread(target=relay, daemon=True)
    reader.start()
    return proc, reader, lines


def _reason(item: str, lines: list[str], code: int | None) -> str:
    at = max((n for n, line in enumerate(lines) if line.startswith("Next: ")), default=0)
    said = max((n for n, line in enumerate(lines[:at]) if line == f"Stopped: {item} needs you."),
               default=max(at - 2, -1)) + 1
    if at and said < at:
        return "\n".join(lines[said:at])
    return lines[-1] if lines else f"its land run ended with exit code {code}."


def _wake_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def main() -> int:
    state_dir = _state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "runner.lock"
    with lock_path.open("ab") as lock:
        if not codex._try_lock(lock):
            return 0
        os.environ["FORGE_RUNNER"] = "1"
        info_path = state_dir / "runner.json"
        wake_path = state_dir / "runner.wake"
        _write_json(info_path, codex.identity(os.getpid()) or {"pid": os.getpid()})
        try:
            return _loop(wake_path)
        finally:
            try:
                info_path.unlink(missing_ok=True)
            except OSError:
                pass
            codex._unlock(lock)


def _loop(wake_path: Path) -> int:
    running: dict[tuple[Path, str], tuple[subprocess.Popen[str], threading.Thread, list[str], str]] = {}
    quiet: set[tuple[Path, str]] = set()
    retries: dict[tuple[Path, str], tuple[int, float]] = {}
    polling: dict[tuple[Path, str], dict[str, Any]] = {}
    last_wake = _wake_mtime(wake_path)

    while True:
        now = time.monotonic()
        merge_happened = False

        current_wake = _wake_mtime(wake_path)
        if current_wake != last_wake:
            last_wake = current_wake
            quiet.clear()

        # 1. Collect finished land runs.
        for key in list(running):
            proc, reader, lines, branch = running[key]
            if proc.poll() is None:
                continue
            running.pop(key)
            reader.join()
            top, item = key
            if proc.returncode == 0:
                ready_line = next((line for line in lines
                                   if line.startswith(f"{item} is ready; a human merges")), None)
                if ready_line:
                    url = ready_line.rsplit(": ", 1)[-1]
                    polling[key] = {"branch": branch, "delay": _POLL_INITIAL,
                                    "next": now + _POLL_INITIAL, "deadline": now + _POLL_MAX_AGE}
                    stops.ended(top, item, "ready for a human merge", url=url)
                elif land._merged(top, branch):
                    retries.pop(key, None)
                    polling.pop(key, None)
                    quiet = {k for k in quiet if k[0] != top}
                    merge_happened = True
                else:
                    quiet.add(key)
            else:
                lock_refused = any(f"Another land run is working on {item}." in line for line in lines)
                net = any(m in line for line in lines for m in (*repo.NETWORK, repo.REFUSALS["no_github"][0]))
                needs_you = any("needs you" in line for line in lines)
                if lock_refused:
                    quiet.add(key)
                elif land._merged(top, branch):
                    retries.pop(key, None)
                    polling.pop(key, None)
                    quiet = {k for k in quiet if k[0] != top}
                    merge_happened = True
                elif net or not needs_you:
                    count = retries.get(key, (0, 0.0))[0]
                    if count < 2:
                        base_wait = float(os.environ.get("FORGE_NETWORK_RETRY_WAIT", "10"))
                        retries[key] = (count + 1, now + base_wait * (3 ** count))
                    else:
                        retries.pop(key, None)
                        stops.ended(top, item, _reason(item, lines, proc.returncode))
                        quiet.add(key)
                else:
                    retries.pop(key, None)
                    stops.ended(top, item, _reason(item, lines, proc.returncode))
                    quiet.add(key)

        # 2. Poll pull requests waiting for a human merge.
        for key in list(polling):
            top, item = key
            info = polling[key]
            if now >= info["deadline"]:
                polling.pop(key, None)
                continue
            if now >= info["next"]:
                if land._merged(top, info["branch"]):
                    polling.pop(key, None)
                    quiet = {k for k in quiet if k[0] != top}
                    merge_happened = True
                else:
                    info["delay"] = min(info["delay"] * 2, _POLL_CAP)
                    info["next"] = now + info["delay"]

        # 3. Pass over each remembered repo.
        live_entries = machine.entries()
        for top in machine.remembered():
            try:
                if repo._pin((top / "forge.toml").read_text(encoding="utf-8")) != __version__:
                    continue
            except OSError:
                continue
            started = _local_started(top)
            if not started and not _has_approved_unstarted(top):
                continue
            repo.run("git", "fetch", "-q", "origin", cwd=top)
            try:
                doctor.tidy_finished(top)
            except Exception:
                pass
            try:
                to_start = nextstep.startable(top)
            except Exception:
                to_start = []
            for part in to_start:
                done = subprocess.run(
                    _child_cmd(["task", "start", part]), cwd=top,
                    env=_runner_env({"FORGE_RUNNER": "1"}),
                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
                if done.stdout or done.stderr:
                    _log_append(top, f"[task start {part}] {done.stdout}{done.stderr}")
            default = repo.default_branch(top)
            live = {run.get("item") for run in live_entries if run.get("repo_root") == top.as_posix()}
            current_items = _local_started(top)
            active_keys = {(top, item) for item, *_ in current_items}
            for key in [k for k in retries if k[0] == top and k not in active_keys]:
                retries.pop(key, None)
            for item, branch, tree, state in current_items:
                key = (top, item)
                if task._merged(f"origin/{default}", item, top):
                    retries.pop(key, None)
                    polling.pop(key, None)
                    continue
                if key in running or key in quiet or key in polling:
                    continue
                if key in retries and now < retries[key][1]:
                    continue
                if stops.stopped(top, item):
                    continue
                if land._pending(top, item):
                    continue
                if item in live or any(run.get("process") and codex._alive(run["process"]) is not False
                                       for run in board.active_runs(tree, item)):
                    continue
                if not _lock_free(top, item):
                    continue
                proc, reader, lines = _spawn_land(top, item)
                running[key] = (proc, reader, lines, branch)

        if merge_happened:
            continue
        if not running and not polling and not retries:
            if _wake_mtime(wake_path) != last_wake:
                continue
            return 0
        time.sleep(float(os.environ.get("FORGE_RUNNER_TICK", "2")))
