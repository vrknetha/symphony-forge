"""forge start sorts ideas in the configured builder's read-only model."""
import json

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_codex_worker import _sent
from test_tools_session_hold import Session
from test_worker import calls, install_claude

STORY = "FIX-THE-EXPLORER-DOES-NOT-FOLLOW-THE-BUILDER"
REPLY = "Lane: discovery\nReason: The problem is unclear.\nQuestion: What should change?"


@pytest.mark.platform
@pytest.mark.parametrize("family, model, effort, custom", [
    ("codex", "gpt-6.1-terra", "medium", False),
    ("claude", "claude-haiku-5-5", "high", False),
    ("antigravity", "gemini-4-neon", "low", False),
    ("antigravity", "gemini-3.8-flash", "high", True),
])
def test_1_start_uses_the_builder_family_and_explore_models(
        repo, monkeypatch, tmp_path, isolated_codex_home, family, model, effort, custom):
    version = repo.forge("--version").stdout.split()[-1]
    config = f'version = "{version}"\nworkers = "{family}"\ntools = "both"\n'
    if custom:
        config += f'\n[models.explore.{family}]\nmodel = "{model}"\neffort = "{effort}"\n'
    repo.write("forge.toml", config)
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Choose who builds")
    repo.git("push", "-q", "origin", "main")

    if family == "antigravity":
        log = install_agy(repo, monkeypatch)
        monkeypatch.setenv("AUTOREVIEW", str(
            ROOT / "tests/fixtures/autoreview-ce14dcca/scripts/autoreview"))
        monkeypatch.setenv("STUB_AGY_REVIEW", REPLY)
    elif family == "claude":
        log = install_claude(repo, worker=False)
        monkeypatch.setenv("STUB_CLAUDE_RESULT", REPLY)
    else:
        (isolated_codex_home / "config.toml").write_text(
            f'[projects.{json.dumps(repo.path.as_posix())}]\ntrust_level = "trusted"\n',
            encoding="utf-8")
        log = repo.bin / "codex-app-server.jsonl"
        monkeypatch.setenv("STUB_CODEX_TEXT", REPLY)

    host = "codex" if family == "claude" else "claude"
    monkeypatch.delenv("CODEX_THREAD_ID" if host == "claude" else "CLAUDECODE", raising=False)
    monkeypatch.setenv("CLAUDECODE" if host == "claude" else "CODEX_THREAD_ID", "1")
    session = Session(repo, tmp_path / "intake-host", host + "-intake")
    try:
        started = session.forge("start", "Improve the welcome")
    finally:
        session.close()

    assert started.returncode == 0, started.stdout + started.stderr
    assert "Forge chose discovery: The problem is unclear." in started.stdout
    assert "Ask the human: What should change?" in started.stdout
    if family == "antigravity":
        selected = {call["configId"]: call["value"]
                    for call in _sent(log, "session/set_config_option")}
        assert selected == {"model": model, "thought_level": effort}
        assert len(_sent(log, "session/prompt")) == 1
    elif family == "claude":
        [turn] = calls(log)
        assert (turn["options"]["model"], turn["options"]["effort"],
                turn["options"]["permission_mode"]) == (model, effort, "plan")
    else:
        [turn] = _sent(log, "thread/start")
        assert (turn["config"]["model"], turn["config"]["model_reasoning_effort"],
                turn["sandbox"]) == (model, effort, "read-only")
