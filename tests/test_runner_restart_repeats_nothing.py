from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 5: a restart repeats no finished build and undoes no stop that the owner set;
# forge stop ends a running build or check wait and frees the land lock; forge merge and
# forge land --all respect the stop; single-item forge land lifts it.

import json
import os
import signal
import time
from pathlib import Path

import pytest

from test_close import env  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_runner_moves_approved_work_to_merge import (  # noqa: F401
    _install_multi_gh,
    _runner_exited,
    _wait_for,
    runner_cleanup,
)
from test_worker import calls


def _runner_pid(tmp_path: Path) -> int | None:
    info = tmp_path / "xdg" / "forge" / "runner.json"
    if not info.exists():
        return None
    try:
        return json.loads(info.read_text(encoding="utf-8")).get("pid")
    except (OSError, ValueError):
        return None


@pytest.mark.parametrize("case", [
    "owner_stop_survives_restart_and_land_lifts_it",
    "sigkill_restart_repeats_nothing",
])
def test_5_runner_restart_repeats_nothing(case, land, tmp_path, monkeypatch):
    _install_multi_gh(land, tmp_path)
    _agent(land)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    if case == "sigkill_restart_repeats_nothing":
        started = land.repo.forge("fix", "start", "Once fix", "--done", "Once fix done", "--slug", "once-fix")
        assert started.returncode == 0, started.stderr
        _wait_for(lambda: len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) >= 1, timeout=30.0)

        pid = _runner_pid(tmp_path)
        if pid:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        _wait_for(lambda: _runner_exited(tmp_path), timeout=15.0)

        woke = land.repo.forge("next")
        assert woke.returncode == 0, woke.stderr
        _wait_for(lambda: (land.repo.bin / "merged-fix-once-fix").exists() and _runner_exited(tmp_path), timeout=45.0)

        assert not (tmp_path / "repo-fix-once-fix").exists()
        assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == 1
        gh_calls = [json.loads(line) for line in (land.repo.bin / "gh-calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        merge_calls = [c for c in gh_calls if c[:2] == ["pr", "merge"]]
        assert len(merge_calls) == 1, merge_calls
        return

    # Make the builder sleep when building slow-fix until a marker file exists.
    marker = tmp_path / "slow-started"
    release = tmp_path / "slow-release"
    module = land.repo.bin / "claude_agent_sdk" / "__init__.py"
    original = module.read_text(encoding="utf-8")
    patch = (
        f'        if "slow-fix" in os.getcwd() and not Path({str(release)!r}).exists():\n'
        f'            Path({str(marker)!r}).write_text("started", encoding="utf-8")\n'
        '            import time; time.sleep(30)\n'
        '        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n'
    )
    module.write_text(
        original.replace('        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n', patch),
        encoding="utf-8",
    )

    started = land.repo.forge("fix", "start", "Slow fix", "--done", "Slow fix done", "--slug", "slow-fix")
    assert started.returncode == 0, started.stderr
    _wait_for(lambda: marker.exists(), timeout=30.0)

    # Stop slow-fix while it is building, then kill the runner and revive it.
    stopped = land.repo.forge("stop", "slow-fix")
    assert stopped.returncode == 0, stopped.stderr

    pid = _runner_pid(tmp_path)
    if pid:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    _wait_for(lambda: _runner_exited(tmp_path), timeout=15.0)

    # Allow slow-fix to finish quickly if anything ever tried to build it again.
    release.write_text("go", encoding="utf-8")
    calls_after_stop = len(calls(land.repo.bin / "claude-sdk-calls.jsonl"))

    # Revive runner with forge next: slow-fix must NOT be built again.
    woke = land.repo.forge("next")
    assert woke.returncode == 0, woke.stderr
    time.sleep(0.5)
    _wait_for(lambda: _runner_exited(tmp_path), timeout=30.0)
    assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == calls_after_stop

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
