from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 6: when the work is done, the runner ends and makes no recurring GitHub calls.

import time

import pytest

from test_close import env  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_runner_moves_approved_work_to_merge import (  # noqa: F401
    _human_merge,
    _install_multi_gh,
    _lock_is_free,
    _runner_exited,
    _runner_log,
    _runner_started,
    _wait_for,
    runner_cleanup,
)


@pytest.mark.parametrize("case", ["idle", "human_merge", "agent_merge"])
def test_6_runner_ends_when_idle(case, land, tmp_path, monkeypatch):
    _install_multi_gh(land, tmp_path)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    if case == "idle":
        # Idle repo: `forge lanes` actually wakes a runner (runner.lock created) that exits with zero gh calls.
        assert land.repo.forge("lanes").returncode == 0
        _wait_for(lambda: _runner_exited(tmp_path), timeout=60.0, detail=lambda: _runner_log(land))
        assert not land.gh_calls()
        return

    if case == "human_merge":
        # Human-merged PR cleaned up before its 60s poll: runner stays quiet between polls
        # (no GitHub calls on 50ms ticks), then clears its polling entry and exits as soon as cleanup runs.
        started_human = land.repo.forge("fix", "start", "Idle human", "--done", "Human merged", "--slug", "idle-human")
        assert started_human.returncode == 0, started_human.stderr
        land_lock = land.repo.path / ".git" / "forge" / "land-idle-human.lock"
        _wait_for(lambda: "idle-human is ready; a human merges" in _runner_log(land) and _lock_is_free(land_lock),
                  timeout=60.0, detail=lambda: _runner_log(land))
        calls_while_waiting = len(land.gh_calls())
        time.sleep(0.3)
        assert len(land.gh_calls()) == calls_while_waiting
        _human_merge(land, tmp_path, "fix/idle-human")
        assert land.repo.forge("next").returncode == 0
        _wait_for(lambda: not (tmp_path / "repo-fix-idle-human").exists() and _runner_exited(tmp_path),
                  timeout=60.0, detail=lambda: _runner_log(land))
        calls_after_human = len(land.gh_calls())
        time.sleep(0.25)
        assert len(land.gh_calls()) == calls_after_human
        return

    # agent_merge: runner exits within a few ticks after the last item merges and makes no more gh calls.
    _agent(land)
    started = land.repo.forge("fix", "start", "Last fix", "--done", "Last fix merged", "--slug", "last-fix")
    assert started.returncode == 0, started.stderr
    _wait_for(lambda: (land.repo.bin / "merged-fix-last-fix").exists() and _runner_exited(tmp_path),
              timeout=60.0, detail=lambda: _runner_log(land))
    count_after_merge = len(land.gh_calls())
    time.sleep(0.25)
    assert len(land.gh_calls()) == count_after_merge
