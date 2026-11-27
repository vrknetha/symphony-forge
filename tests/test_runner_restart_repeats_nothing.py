from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 5: a restart repeats no finished build and undoes no stop that the owner set;
# forge stop ends a running build or check wait and frees the land lock; forge merge and
# forge land --all respect the stop; single-item forge land lifts it; restarting restores
# human-merge polling without re-landing or duplicating notices.

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_close import env  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_lanes_agents import alive
from test_runner_moves_approved_work_to_merge import (  # noqa: F401
    _human_merge,
    _install_multi_gh,
    _lock_is_free,
    _runner_exited,
    _runner_lock,
    _runner_log,
    _wait_for,
    runner_cleanup,
)
from test_runner_stops_one_item_and_tells_the_owner import _install_notifier, _notices
from test_worker import calls


def _runner_pid(tmp_path: Path) -> int | None:
    info = tmp_path / "config" / "forge" / "runner.json"
    if not info.exists():
        return None
    try:
        pid = json.loads(info.read_text(encoding="utf-8")).get("pid")
        return pid if isinstance(pid, int) else None
    except (OSError, ValueError):
        return None


def _kill_runner(tmp_path: Path) -> int:
    """Assert a live runner exists under tmp_path/config, terminate it abruptly, and wait for exit."""
    _wait_for(lambda: _runner_pid(tmp_path) is not None and not _lock_is_free(_runner_lock(tmp_path)), timeout=20.0)
    pid = _runner_pid(tmp_path)
    assert pid is not None
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)
    else:
        os.kill(pid, signal.SIGKILL)
    _wait_for(lambda: not alive(pid) and _lock_is_free(_runner_lock(tmp_path)), timeout=15.0)
    return pid


def _spawns(tmp_path: Path) -> list[int]:
    log = tmp_path / "runner-spawns.jsonl"
    if not log.exists():
        return []
    return [json.loads(line)["pid"] for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _all_runners_done(tmp_path: Path) -> bool:
    return all(not alive(pid) for pid in _spawns(tmp_path)) and _runner_exited(tmp_path)


@pytest.mark.platform
@pytest.mark.parametrize("case", [
    "owner_stop_survives_restart_and_land_lifts_it",
    "stop_during_check_wait",
    "sigkill_restart_at_build_and_merge_boundaries",
    "restart_restores_human_merge_polling",
])
def test_5_runner_restart_repeats_nothing(case, land, tmp_path, monkeypatch, request):
    if case == "restart_restores_human_merge_polling":
        request.getfixturevalue("fake_clock")
        _install_multi_gh(land, tmp_path)
        notice_log = _install_notifier(land)
        monkeypatch.setenv("FORGE_RUNNER_TICK", "2")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

        started = land.repo.forge("fix", "start", "Poll fix", "--done", "Poll fix done", "--slug", "poll-fix")
        assert started.returncode == 0, started.stderr
        runner_state = land.repo.path / ".git" / "forge" / "runner.json"
        _wait_for(lambda: "poll-fix is ready; a human merges" in _runner_log(land) and runner_state.exists(), timeout=45.0)
        if os.name != "nt":
            _wait_for(lambda: len(_notices(notice_log)) >= 1, timeout=15.0)
        notices_before = len(_notices(notice_log))
        calls_before = len(calls(land.repo.bin / "claude-sdk-calls.jsonl"))

        # Abruptly kill the runner while it polls for the human merge.
        old_pid = _kill_runner(tmp_path)

        def _poll_checks() -> int:
            log = land.repo.bin / "gh-calls.jsonl"
            if not log.exists():
                return 0
            return sum(
                1 for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip() and (args := json.loads(line))[:2] == ["pr", "list"]
                and "--head" in args and "fix/poll-fix" in args
            )

        polls_before = _poll_checks()

        # Next Forge use revives the runner, which restores polling without re-landing or re-notifying.
        woke = land.repo.forge("next")
        assert woke.returncode == 0, woke.stderr
        _wait_for(lambda: _poll_checks() >= polls_before + 2, timeout=20.0)
        _human_merge(land, tmp_path, "fix/poll-fix")
        _wait_for(lambda: not (tmp_path / "repo-fix-poll-fix").exists() and _runner_exited(tmp_path), timeout=45.0)

        assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == calls_before
        assert _runner_log(land).count("poll-fix is ready; a human merges") == 1
        if os.name != "nt":
            poll_notices = [a for a in _notices(notice_log)
                            if any("poll-fix" in x for x in a) and not any("Forge runner done" in x for x in a)]
            assert len(poll_notices) == 1 and notices_before == 1
        return

    _install_multi_gh(land, tmp_path)
    _agent(land)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    if case == "stop_during_check_wait":
        cfg_lines = [line for line in (land.repo.path / "forge.toml").read_text("utf-8").splitlines()
                     if not line.strip().startswith(("test_place", "checks"))]
        land.commit(land.repo.path, "forge.toml",
                    "\n".join(cfg_lines) + '\ntest_place = "ci"\nchecks = ["ci-tests"]\n')
        land.repo.git("push", "-q", "origin", "main")
        land.checks([{"name": "ci-tests", "status": "in_progress", "conclusion": None}])
        check_marker = tmp_path / "check-wait-entered"
        gh_script = land.repo.bin / ("gh.py" if os.name == "nt" else "gh")
        if gh_script.exists():
            gh_text = gh_script.read_text(encoding="utf-8")
            marker_hook = (
                f'if "check-runs" in " ".join(args):\n'
                f'    pathlib.Path({str(check_marker)!r}).write_text("waiting", encoding="utf-8")\n'
            )
            gh_script.write_text(gh_text.replace('if args[:2] == ["pr", "list"]', marker_hook + 'if args[:2] == ["pr", "list"]', 1), encoding="utf-8")

        started = land.repo.forge("fix", "start", "Wait fix", "--done", "Wait fix done", "--slug", "wait-fix")
        assert started.returncode == 0, started.stderr
        _wait_for(lambda: check_marker.exists(), timeout=45.0)

        land_lock = land.repo.path / ".git" / "forge" / "land-wait-fix.lock"
        stopped = land.repo.forge("stop", "wait-fix")
        assert stopped.returncode == 0, stopped.stderr
        _wait_for(lambda: _lock_is_free(land_lock), timeout=10.0)
        assert not (land.repo.bin / "merged-fix-wait-fix").exists()
        gh_calls = [json.loads(line) for line in (land.repo.bin / "gh-calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        assert not [c for c in gh_calls if c[:2] == ["pr", "merge"]]

        # Flip checks to pass and immediately run forge land wait-fix: no "Another land run" refusal.
        monkeypatch.setenv("FORGE_NO_RUNNER", "1")
        land.checks([{"name": "ci-tests", "status": "completed", "conclusion": "success"}])
        resumed = land.repo.forge("land", "wait-fix")
        assert "Another land run" not in resumed.stdout + resumed.stderr
        assert resumed.returncode == 0, resumed.stdout + resumed.stderr
        assert (land.repo.bin / "merged-fix-wait-fix").exists()
        return

    if case == "sigkill_restart_at_build_and_merge_boundaries":
        # Pause right inside close's pr create (after build finishes, before merge) so SIGKILL hits
        # between build and close, and again right after pr merge writes merged-fix-* (before cleanup).
        close_entered = tmp_path / "close-entered"
        close_release = tmp_path / "close-release"
        merge_entered = tmp_path / "merge-entered"
        merge_release = tmp_path / "merge-release"
        gh_script = land.repo.bin / ("gh.py" if os.name == "nt" else "gh")
        gh_text = gh_script.read_text(encoding="utf-8")
        close_hook = (
            'if args[:2] == ["pr", "create"]:\n'
            f'    pathlib.Path({str(close_entered)!r}).write_text("in-close", encoding="utf-8")\n'
            '    import time as _t\n'
            f'    while not pathlib.Path({str(close_release)!r}).exists():\n'
            '        _t.sleep(0.05)\n'
        )
        merge_hook = (
            f'    pathlib.Path({str(merge_entered)!r}).write_text("merged", encoding="utf-8")\n'
            '    import time as _t\n'
            f'    while not pathlib.Path({str(merge_release)!r}).exists():\n'
            '        _t.sleep(0.05)\n'
            '    answer("")'
        )
        assert 'if args[:2] == ["pr", "list"]' in gh_text and '    answer("")' in gh_text
        gh_text = gh_text.replace('if args[:2] == ["pr", "list"]', close_hook + 'if args[:2] == ["pr", "list"]', 1)
        gh_text = gh_text.replace('    answer("")', merge_hook, 1)
        gh_script.write_text(gh_text, encoding="utf-8")

        started = land.repo.forge("fix", "start", "Once fix", "--done", "Once fix done", "--slug", "once-fix")
        assert started.returncode == 0, started.stderr

        # 1. Kill runner with SIGKILL after build finishes and before close completes.
        _wait_for(lambda: close_entered.exists(), timeout=60.0)
        _kill_runner(tmp_path)

        # Revive runner while the surviving land process still holds the lock; it leaves once-fix alone.
        woke1 = land.repo.forge("next")
        assert woke1.returncode == 0, woke1.stderr
        _wait_for(lambda: _all_runners_done(tmp_path), timeout=45.0)

        # Release close and merge so the surviving land run finishes on its own and frees its lock.
        once_lock = land.repo.path / ".git" / "forge" / "land-once-fix.lock"
        merge_release.write_text("go", encoding="utf-8")
        close_release.write_text("go", encoding="utf-8")
        _wait_for(lambda: (land.repo.bin / "merged-fix-once-fix").exists() and _lock_is_free(once_lock), timeout=60.0)

        # Revive runner after merge; it cleans up the folder and repeats neither build nor merge.
        woke2 = land.repo.forge("next")
        assert woke2.returncode == 0, woke2.stderr
        _wait_for(lambda: not (tmp_path / "repo-fix-once-fix").exists() and _all_runners_done(tmp_path), timeout=60.0)

        assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == 1
        gh_calls = [json.loads(line) for line in (land.repo.bin / "gh-calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        merge_calls = [c for c in gh_calls if c[:2] == ["pr", "merge"]]
        assert len(merge_calls) == 1, merge_calls

        # 2. Start a second fix and kill the runner with SIGKILL right after pr merge and before cleanup.
        merge_entered.unlink(missing_ok=True)
        merge_release.unlink(missing_ok=True)
        cleanup_lock = land.repo.path / ".git" / "forge" / "land-cleanup-fix.lock"
        started2 = land.repo.forge("fix", "start", "Cleanup fix", "--done", "Cleanup fix done", "--slug", "cleanup-fix")
        assert started2.returncode == 0, started2.stderr
        _wait_for(lambda: merge_entered.exists(), timeout=60.0)
        assert (tmp_path / "repo-fix-cleanup-fix").exists()
        _kill_runner(tmp_path)
        merge_release.write_text("go", encoding="utf-8")
        _wait_for(lambda: _lock_is_free(cleanup_lock), timeout=45.0)

        woke3 = land.repo.forge("next")
        assert woke3.returncode == 0, woke3.stderr
        _wait_for(lambda: not (tmp_path / "repo-fix-cleanup-fix").exists() and _all_runners_done(tmp_path), timeout=60.0)

        assert (land.repo.bin / "merged-fix-cleanup-fix").exists()
        assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == 2
        gh_calls2 = [json.loads(line) for line in (land.repo.bin / "gh-calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        merge_calls2 = [c for c in gh_calls2 if c[:2] == ["pr", "merge"]]
        assert len(merge_calls2) == 2, merge_calls2
        return

    # owner_stop_survives_restart_and_land_lifts_it:
    # Start slow-fix and keeper-fix on one live runner. keeper-fix keeps that same runner alive
    # across `forge stop slow-fix` (on both 2-core and multi-core machines) so we kill the live
    # runner strictly AFTER the owner's stop is recorded, then revive with `forge next`.
    slow_marker = tmp_path / "slow-started"
    slow_release = tmp_path / "slow-release"
    keeper_marker = tmp_path / "keeper-started"
    keeper_release = tmp_path / "keeper-release"
    module = land.repo.bin / "claude_agent_sdk" / "__init__.py"
    original = module.read_text(encoding="utf-8")
    patch = (
        f'        if "slow-fix" in os.getcwd() and not Path({str(slow_release)!r}).exists():\n'
        f'            Path({str(slow_marker)!r}).write_text("started", encoding="utf-8")\n'
        '            import time as _t\n'
        f'            while not Path({str(slow_release)!r}).exists():\n'
        '                _t.sleep(0.05)\n'
        f'        if "keeper-fix" in os.getcwd() and not Path({str(keeper_release)!r}).exists():\n'
        f'            Path({str(keeper_marker)!r}).write_text("started", encoding="utf-8")\n'
        '            import time as _t\n'
        f'            while not Path({str(keeper_release)!r}).exists():\n'
        '                _t.sleep(0.05)\n'
        '        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n'
    )
    module.write_text(
        original.replace('        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n', patch),
        encoding="utf-8",
    )

    started = land.repo.forge("fix", "start", "Slow fix", "--done", "Slow fix done", "--slug", "slow-fix")
    assert started.returncode == 0, started.stderr
    started_keeper = land.repo.forge("fix", "start", "Keeper fix", "--done", "Keeper fix done", "--slug", "keeper-fix")
    assert started_keeper.returncode == 0, started_keeper.stderr
    _wait_for(lambda: slow_marker.exists() and _runner_pid(tmp_path) is not None, timeout=30.0)
    runner_pid = _runner_pid(tmp_path)
    assert runner_pid is not None

    # 1. Set the owner's stop on slow-fix while the live runner is running.
    stopped = land.repo.forge("stop", "slow-fix")
    assert stopped.returncode == 0, stopped.stderr
    _wait_for(lambda: keeper_marker.exists(), timeout=30.0)
    assert _runner_pid(tmp_path) == runner_pid

    spawns_before_kill = _spawns(tmp_path)
    slow_calls_after_stop = sum("slow-fix" in str(c.get("cwd", "")) for c in calls(land.repo.bin / "claude-sdk-calls.jsonl"))

    # 2. Kill the live runner strictly AFTER the owner's stop is set.
    killed_pid = _kill_runner(tmp_path)
    assert killed_pid == runner_pid

    # Allow both builds to finish if anything tries to run them; keeper-fix's surviving land finishes on its own.
    keeper_lock = land.repo.path / ".git" / "forge" / "land-keeper-fix.lock"
    slow_release.write_text("go", encoding="utf-8")
    keeper_release.write_text("go", encoding="utf-8")
    _wait_for(lambda: (land.repo.bin / "merged-fix-keeper-fix").exists() and _lock_is_free(keeper_lock), timeout=60.0)

    # 3. Use Forge again: a new runner starts, cleans up keeper-fix without repeating its build,
    #    and leaves slow-fix stopped without building it again.
    woke = land.repo.forge("next")
    assert woke.returncode == 0, woke.stderr
    _wait_for(lambda: not (tmp_path / "repo-fix-keeper-fix").exists() and _all_runners_done(tmp_path), timeout=60.0)

    spawns_after_revive = _spawns(tmp_path)
    assert len(spawns_after_revive) > len(spawns_before_kill) and spawns_after_revive[-1] != runner_pid
    all_calls = calls(land.repo.bin / "claude-sdk-calls.jsonl")
    assert sum("slow-fix" in str(c.get("cwd", "")) for c in all_calls) == slow_calls_after_stop
    assert sum("keeper-fix" in str(c.get("cwd", "")) for c in all_calls) == 1
    assert not (land.repo.bin / "merged-fix-slow-fix").exists()

    # Turn off the runner for the manual merge / land --all / land checks.
    monkeypatch.setenv("FORGE_NO_RUNNER", "1")

    # forge merge on the stopped item refuses and changes nothing.
    merged = land.repo.forge("merge", "slow-fix")
    assert merged.returncode != 0
    assert "slow-fix was stopped; forge land slow-fix continues it" in merged.stdout + merged.stderr

    # With slow-fix stopped and another fix ready, forge land --all merges the other and leaves slow-fix stopped.
    other = land.repo.forge("fix", "start", "Other fix", "--done", "Other fix done", "--slug", "other-fix")
    assert other.returncode == 0, other.stderr
    built_other = land.repo.forge("work", "other-fix")
    assert built_other.returncode == 0, built_other.stderr
    closed_other = land.repo.forge("close", "other-fix")
    assert closed_other.returncode == 0, closed_other.stderr

    land_all = land.repo.forge("land", "--all")
    assert "slow-fix was stopped; forge land slow-fix continues it" in land_all.stdout
    assert (land.repo.bin / "merged-fix-other-fix").exists()
    assert not (land.repo.bin / "merged-fix-slow-fix").exists()

    # The stop is still on record afterwards.
    still_stopped = land.repo.forge("merge", "slow-fix")
    assert still_stopped.returncode != 0
    assert "slow-fix was stopped; forge land slow-fix continues it" in still_stopped.stdout + still_stopped.stderr

    # Hand-run forge land slow-fix lifts the stop and merges it.
    resumed = land.repo.forge("land", "slow-fix")
    assert resumed.returncode == 0, resumed.stderr
    assert (land.repo.bin / "merged-fix-slow-fix").exists()
