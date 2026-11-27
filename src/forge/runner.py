"""Background runner: moves approved stories and started fixes to merge without an open chat."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge import __version__, board, codex, doctor, land, machine, nextstep, repo, stops, story, task

_SKIP_ENV = ("FORGE_NO_RUNNER", "FORGE_WORKER", "FORGE_RUNNER", "CI")
_POLL_INITIAL = 60.0
_POLL_CAP = 1800.0
_POLL_MAX_AGE = 86400.0
_TRANSIENT_HTTP = re.compile(
    r"The requested URL returned error: 5\d\d|\bHTTP 50[234]\b|"
    r"\b502 Bad Gateway\b|\b503 Service Unavailable\b|\b504 Gateway Timeout\b",
    re.I,
)


def _state_dir() -> Path:
    return machine._repos_file().parent


def _allowed_repo(top: Path) -> bool:
    """Under pytest, refuse any repo outside the test's temp folder."""
    test_root = os.environ.get("FORGE_TEST_ROOT")
    if os.environ.get("PYTEST_CURRENT_TEST") and not test_root:
        return False
    if not test_root:
        return True
    try:
        return top.resolve().is_relative_to(Path(test_root).resolve())
    except (OSError, ValueError):
        return False


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _installed_file() -> Path:
    return _state_dir() / "runner-installed-at"


def _installed_at() -> datetime:
    """Record the runner's install moment once on this machine and return it."""
    path = _installed_file()
    try:
        if path.is_file():
            existing = _parse_time(path.read_text(encoding="utf-8"))
            if existing is not None:
                return existing
    except OSError:
        pass
    stamp = repo.now()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(stamp + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass
    return _parse_time(stamp) or datetime.now(timezone.utc)


def record_install(cwd: Path) -> None:
    """Record the install moment before a command starts/approves new work."""
    if any(os.environ.get(name) for name in _SKIP_ENV):
        return
    try:
        top = machine.main_checkout(cwd)
    except Exception:
        return
    if not (top / "forge.toml").is_file() or not _allowed_repo(top):
        return
    _installed_at()


def _story_eligible(top: Path, key: str, cutoff: datetime) -> bool:
    record = story.state_of(top, key, story.plan_ref(top, key))
    approved_at = _parse_time((record.get("approval") or {}).get("at"))
    return approved_at is not None and approved_at >= cutoff


def _item_eligible(top: Path, item: str, state: dict[str, Any], cutoff: datetime) -> bool:
    if "/" in item:
        return _story_eligible(top, item.split("/", 1)[0], cutoff)
    started = next((step.get("at") for step in state.get("steps", [])
                    if isinstance(step, dict) and step.get("step") == "start"), None)
    started_at = _parse_time(started)
    return started_at is not None and started_at >= cutoff


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
    if not (top / "forge.toml").is_file() or not _allowed_repo(top):
        return
    _installed_at()
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


def _has_approved_unstarted(top: Path, cutoff: datetime) -> bool:
    """Local-only check: any story approved at or after `cutoff` with an unmerged task."""
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
        approved_at = _parse_time((record.get("approval") or {}).get("at"))
        if approved_at is None or approved_at < cutoff:
            continue
        doc = story._plan(top, key)
        if not doc:
            continue
        for tid in task.rows(task.sections(doc)):
            if repo.state_path(f"{key}/{tid}") not in paths:
                return True
    return False


def _safe_merged(top: Path, branch: str) -> bool | None:
    """Check whether GitHub reports `branch` merged; None on transient read failure."""
    try:
        return land._merged(top, branch)
    except Exception as exc:
        _log_append(top, f"[runner] GitHub read failed for {branch}: {exc}\n")
        return None


def _transient(text: str) -> bool:
    return (any(marker in text for marker in (*repo.NETWORK, repo.REFUSALS["no_github"][0], "cannot lock ref"))
            or bool(_TRANSIENT_HTTP.search(text)))


def _retry_wait(count: int) -> float:
    return float(os.environ.get("FORGE_NETWORK_RETRY_WAIT", "10")) * (3 ** count)


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
    retries: dict[tuple[Path, str], float] = {}
    attempts: dict[tuple[Path, str], int] = {}
    repo_retries: dict[Path, float] = {}
    repo_attempts: dict[Path, int] = {}
    polling: dict[tuple[Path, str], dict[str, Any]] = {}
    seen_repos: set[Path] = set()
    pass_needed: set[Path] = set()
    worked_repos: set[Path] = set()
    merged_by_repo: dict[Path, list[str]] = {}
    cutoff = _installed_at()
    last_wake = _wake_mtime(wake_path)

    def clear_item_retry(key: tuple[Path, str]) -> None:
        retries.pop(key, None)
        attempts.pop(key, None)

    def schedule_item_retry(key: tuple[Path, str], code: int, lines: list[str], now: float) -> None:
        top, item = key
        count = attempts.get(key, 0)
        if count < 2:
            attempts[key] = count + 1
            retries[key] = now + _retry_wait(count)
        else:
            clear_item_retry(key)
            stops.ended(top, item, code, lines)
            quiet.add(key)

    def schedule_repo_retry(top: Path, now: float) -> None:
        count = repo_attempts.get(top, 0)
        if count < 2:
            repo_attempts[top] = count + 1
            repo_retries[top] = now + _retry_wait(count)
        else:
            repo_retries.pop(top, None)
            repo_attempts.pop(top, None)

    def record_merge(top: Path, item: str) -> None:
        nonlocal quiet
        key = (top, item)
        clear_item_retry(key)
        polling.pop(key, None)
        quiet = {k for k in quiet if k[0] != top}
        worked_repos.add(top)
        merged = merged_by_repo.setdefault(top, [])
        if item not in merged:
            merged.append(item)
        pass_needed.add(top)

    while True:
        now = time.monotonic()
        merge_happened = False

        remembered = [top for top in machine.remembered() if _allowed_repo(top)]
        for top in remembered:
            if top not in seen_repos:
                seen_repos.add(top)
                pass_needed.add(top)

        current_wake = _wake_mtime(wake_path)
        if current_wake != last_wake:
            last_wake = current_wake
            quiet.clear()
            pass_needed.update(remembered)

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
                    clear_item_retry(key)
                    polling[key] = {"branch": branch, "delay": _POLL_INITIAL,
                                    "next": now + _POLL_INITIAL, "deadline": now + _POLL_MAX_AGE}
                    stops.ended(top, item, 0, lines)
                else:
                    merged = _safe_merged(top, branch)
                    if merged is True:
                        record_merge(top, item)
                        merge_happened = True
                    elif merged is None:
                        schedule_item_retry(key, 0, lines, now)
                    else:
                        clear_item_retry(key)
                        quiet.add(key)
            else:
                lock_refused = any(f"Another land run is working on {item}." in line for line in lines)
                net = any(_transient(line) for line in lines)
                needs_you = any("needs you" in line for line in lines)
                if lock_refused:
                    clear_item_retry(key)
                    quiet.add(key)
                elif net:
                    schedule_item_retry(key, proc.returncode, lines, now)
                elif _safe_merged(top, branch) is True:
                    record_merge(top, item)
                    merge_happened = True
                elif not needs_you:
                    schedule_item_retry(key, proc.returncode, lines, now)
                else:
                    clear_item_retry(key)
                    stops.ended(top, item, proc.returncode, lines)
                    quiet.add(key)

        # 2. Poll pull requests waiting for a human merge.
        for key in list(polling):
            top, item = key
            info = polling[key]
            if now >= info["deadline"]:
                polling.pop(key, None)
                clear_item_retry(key)
                quiet.add(key)
                continue
            if now >= info["next"]:
                if _safe_merged(top, info["branch"]) is True:
                    record_merge(top, item)
                    merge_happened = True
                else:
                    info["delay"] = min(info["delay"] * 2, _POLL_CAP)
                    info["next"] = now + info["delay"]

        # 3. Trigger passes only for due retries or explicitly needed repos.
        for key, due in list(retries.items()):
            if now >= due:
                retries.pop(key, None)
                pass_needed.add(key[0])
        for top, due in list(repo_retries.items()):
            if now >= due:
                repo_retries.pop(top, None)
                pass_needed.add(top)

        if pass_needed:
            live_entries = machine.entries()
            for top in remembered:
                if top not in pass_needed:
                    continue
                pass_needed.discard(top)
                try:
                    if repo._pin((top / "forge.toml").read_text(encoding="utf-8")) != __version__:
                        continue
                except OSError:
                    continue
                started = [(item, branch, tree, state) for item, branch, tree, state in _local_started(top)
                           if _item_eligible(top, item, state, cutoff)]
                if not started and not _has_approved_unstarted(top, cutoff):
                    for key in [k for k in set(retries) | set(attempts) if k[0] == top]:
                        clear_item_retry(key)
                    for key in [k for k in polling if k[0] == top]:
                        polling.pop(key, None)
                    repo_retries.pop(top, None)
                    repo_attempts.pop(top, None)
                    continue
                fetched = repo.run("git", "fetch", "-q", "origin", cwd=top)
                if fetched.returncode != 0:
                    _log_append(top, f"[runner] git fetch failed: {fetched.stderr}{fetched.stdout}\n")
                    schedule_repo_retry(top, now)
                    continue
                try:
                    doctor.tidy_finished(top)
                except Exception as exc:
                    _log_append(top, f"[runner] tidy_finished failed: {exc}\n")
                try:
                    to_start = [part for part in nextstep.startable(top)
                                if _story_eligible(top, part.split("/", 1)[0], cutoff)]
                except Exception as exc:
                    _log_append(top, f"[runner] startable failed: {exc}\n")
                    schedule_repo_retry(top, now)
                    continue
                start_retry = False
                for part in to_start:
                    done = subprocess.run(
                        _child_cmd(["task", "start", part]), cwd=top,
                        env=_runner_env({"FORGE_RUNNER": "1"}),
                        stdin=subprocess.DEVNULL, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
                    combined = f"{done.stdout}{done.stderr}"
                    if combined:
                        _log_append(top, f"[task start {part}] {combined}")
                    if done.returncode == 0:
                        worked_repos.add(top)
                    elif _transient(combined):
                        start_retry = True
                if start_retry:
                    schedule_repo_retry(top, now)
                else:
                    repo_retries.pop(top, None)
                    repo_attempts.pop(top, None)
                default = repo.default_branch(top)
                live = {run.get("item") for run in live_entries if run.get("repo_root") == top.as_posix()}
                current_items = [(item, branch, tree, state) for item, branch, tree, state in _local_started(top)
                                 if _item_eligible(top, item, state, cutoff)]
                active_keys = {(top, item) for item, *_ in current_items}
                for key in [k for k in set(retries) | set(attempts) if k[0] == top and k not in active_keys]:
                    clear_item_retry(key)
                for key in [k for k in polling if k[0] == top and k not in active_keys]:
                    polling.pop(key, None)
                for item, branch, tree, state in current_items:
                    key = (top, item)
                    if task._merged(f"origin/{default}", item, top):
                        clear_item_retry(key)
                        polling.pop(key, None)
                        continue
                    if key in running or key in quiet or key in polling:
                        continue
                    if key in retries and now < retries[key]:
                        continue
                    if stops.stopped(top, item) or stops.parked(top, item, tree):
                        continue
                    if land._pending(top, item):
                        continue
                    if item in live or any(run.get("process") and codex._alive(run["process"]) is not False
                                           for run in board.active_runs(tree, item)):
                        continue
                    if not _lock_free(top, item):
                        continue
                    retries.pop(key, None)
                    proc, reader, lines = _spawn_land(top, item)
                    running[key] = (proc, reader, lines, branch)
                    worked_repos.add(top)

        if merge_happened:
            continue
        if not running and not polling and not retries and not repo_retries and not pass_needed:
            if _wake_mtime(wake_path) != last_wake:
                continue
            for top in sorted(worked_repos):
                stops.summary(top, merged_by_repo.get(top, []))
            return 0
        time.sleep(float(os.environ.get("FORGE_RUNNER_TICK", "2")))
