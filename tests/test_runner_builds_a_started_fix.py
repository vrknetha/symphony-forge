from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 2: a fix started with Forge is built, checked and merged by the background runner,
# its folder is removed, and a settings fix naming forge.toml allows its worker to edit forge.toml.

from pathlib import Path

from test_close import env  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_runner_moves_approved_work_to_merge import _install_multi_gh, _runner_gone, _wait_for
from test_worker import calls


def test_2_runner_builds_a_started_fix(land, tmp_path, monkeypatch):
    _install_multi_gh(land, tmp_path)
    _agent(land)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    # 1. Ordinary fix: reaches merge with no other command, folder removed, brief forbids forge.toml.
    started = land.repo.forge("fix", "start", "Ordinary fix", "--done", "Work file added", "--slug", "ordinary-fix")
    assert started.returncode == 0, started.stderr
    _wait_for(lambda: (land.repo.bin / "merged-fix-ordinary-fix").exists() and _runner_gone(tmp_path))
    assert not (tmp_path / "repo-fix-ordinary-fix").exists()
    ordinary_calls = calls(land.repo.bin / "claude-sdk-calls.jsonl")
    assert ordinary_calls
    assert "Workers never edit `forge.toml`" in ordinary_calls[-1]["prompt"]

    # 2. Settings fix naming forge.toml: stub edits forge.toml, keeps the edit, merges with no chat,
    #    and its brief lacks "Workers never edit `forge.toml`".
    module = land.repo.bin / "claude_agent_sdk" / "__init__.py"
    edit_toml = (
        '        p = Path("forge.toml")\n'
        '        p.write_text(p.read_text("utf-8") + "cold_read_rounds = 1\\n", encoding="utf-8")\n'
    )
    module.write_text(
        module.read_text("utf-8").replace('        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n', edit_toml),
        "utf-8",
    )
    started_cfg = land.repo.forge(
        "fix", "start", "Update cold read rounds",
        "--done", "cold_read_rounds is set to 1 in forge.toml",
        "--slug", "settings-fix",
    )
    assert started_cfg.returncode == 0, started_cfg.stderr
    _wait_for(lambda: (land.repo.bin / "merged-fix-settings-fix").exists() and _runner_gone(tmp_path))
    assert not (tmp_path / "repo-fix-settings-fix").exists()
    settings_calls = calls(land.repo.bin / "claude-sdk-calls.jsonl")
    assert "Workers never edit `forge.toml`" not in settings_calls[-1]["prompt"]
    land.repo.git("fetch", "-q", "origin", "main")
    assert "cold_read_rounds = 1" in land.repo.git("show", "origin/main:forge.toml")
