from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 6: when the work is done, the runner ends and makes no recurring GitHub calls.

import time

from test_close import env  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_runner_moves_approved_work_to_merge import _install_multi_gh, _runner_gone, _wait_for


def test_6_runner_ends_when_idle(land, tmp_path, monkeypatch):
    _install_multi_gh(land, tmp_path)
    _agent(land)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    # 1. Idle repo: `forge lanes` wakes a runner that ends with zero gh calls.
    assert land.repo.forge("lanes").returncode == 0
    _wait_for(lambda: _runner_gone(tmp_path))
    assert not land.gh_calls()

    # 2. After the last item merges, the runner exits within a few ticks and makes no more gh calls.
    started = land.repo.forge("fix", "start", "Last fix", "--done", "Last fix merged", "--slug", "last-fix")
    assert started.returncode == 0, started.stderr
    _wait_for(lambda: (land.repo.bin / "merged-fix-last-fix").exists() and _runner_gone(tmp_path))
    count_after_merge = len(land.gh_calls())
    time.sleep(0.25)
    assert len(land.gh_calls()) == count_after_merge
