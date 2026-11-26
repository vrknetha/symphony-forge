"""forge start sorts ideas in the configured builder's read-only model."""
import json
from pathlib import Path

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_codex_worker import _sent
from test_tools_session_hold import Session
from test_worker import calls, install_claude

STORY = "FIX-THE-EXPLORER-DOES-NOT-FOLLOW-THE-BUILDER"
REPLY = "Lane: discovery\nReason: The problem is unclear.\nQuestion: What should change?"
IDEA = "Improve the welcome"


def _settings(repo, config, remote="origin"):
    repo.write("forge.toml", config)
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Choose who builds")
    repo.git("push", "-q", remote, "main")


@pytest.fixture
def config(repo, family):
    version = repo.forge("--version").stdout.split()[-1]
    return f'version = "{version}"\nworkers = "{family}"\ntools = "both"\n'


@pytest.fixture
def provider_log(repo, monkeypatch, isolated_codex_home, family):
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
            f'[projects.{json.dumps(str(repo.path))}]\ntrust_level = "trusted"\n',
            encoding="utf-8")
        log = repo.bin / "codex-app-server.jsonl"
        monkeypatch.setenv("STUB_CODEX_TEXT", REPLY)
    return log


@pytest.fixture
def start(repo, monkeypatch, tmp_path, family):
    host = "codex" if family == "claude" else "claude"
    monkeypatch.delenv("CODEX_THREAD_ID" if host == "claude" else "CLAUDECODE", raising=False)
    monkeypatch.setenv("CLAUDECODE" if host == "claude" else "CODEX_THREAD_ID", "1")
    session = Session(repo, tmp_path / "intake-host", host + "-intake")
    try:
        yield lambda: session.forge("start", IDEA)
    finally:
        session.close()


@pytest.mark.platform
@pytest.mark.parametrize("family, model, effort, custom", [
    ("codex", "gpt-6.1-terra", "medium", False),
    ("claude", "claude-haiku-5-5", "high", False),
    ("antigravity", "gemini-4-neon", "low", False),
    ("antigravity", "gemini-3.8-flash", "high", True),
])
def test_1_start_uses_the_builder_family_and_explore_models(
        repo, config, provider_log, start, family, model, effort, custom):
    # Leave a checkout and its remote-tracking ref behind a teammate's published settings.
    # The old Claude choice would match the session and incorrectly return a native offer.
    if family == "codex":
        _settings(repo, config.replace('workers = "codex"', 'workers = "claude"'))
        repo.git("branch", "fix/stale-settings")
        origin = repo.git("remote", "get-url", "origin")
        _settings(repo, config, remote=origin)
        repo.git("switch", "-q", "fix/stale-settings")
        assert 'workers = "claude"' in repo.git("show", "origin/main:forge.toml")
    else:
        if custom:
            config += f'\n[models.explore.{family}]\nmodel = "{model}"\neffort = "{effort}"\n'
        _settings(repo, config)

    started = start()
    assert started.returncode == 0, started.stdout + started.stderr
    assert "Forge chose discovery: The problem is unclear." in started.stdout
    assert "Ask the human: What should change?" in started.stdout
    if family == "antigravity":
        selected = {call["configId"]: call["value"]
                    for call in _sent(provider_log, "session/set_config_option")}
        assert selected == {"model": model, "thought_level": effort}
        [turn] = _sent(provider_log, "session/new")
        assert len(_sent(provider_log, "session/prompt")) == 1
        assert not Path(turn["cwd"]).exists(), "The read copy survived the command"
    elif family == "claude":
        [turn] = calls(provider_log)
        assert (turn["options"]["model"], turn["options"]["effort"],
                turn["options"]["permission_mode"]) == (model, effort, "plan")
    else:
        [turn] = _sent(provider_log, "thread/start")
        assert (turn["config"]["model"], turn["config"]["model_reasoning_effort"],
                turn["sandbox"]) == (model, effort, "read-only")


@pytest.mark.platform
@pytest.mark.parametrize("family, variable, value, problem", [
    ("claude", "STUB_CLAUDE_EXIT", "3", "stub claude: the model gave up"),
    ("codex", "STUB_CODEX_STATUS", "failed", "stub codex: the model gave up"),
    ("antigravity", "STUB_AGY_SIGNED_OUT", "1", "Antigravity is not signed in."),
])
def test_2_start_reports_provider_failures_without_retrying(
        repo, monkeypatch, config, provider_log, start, family, variable, value, problem):
    _settings(repo, config)
    monkeypatch.setenv(variable, value)
    failed = start()
    assert failed.returncode == 1, failed.stdout + failed.stderr
    assert problem in failed.stderr
    assert "forge start " in failed.stderr
    if family == "codex":
        assert len(_sent(provider_log, "turn/start")) == 1
    elif family == "claude":
        assert len(calls(provider_log)) == 1
    else:
        [turn] = _sent(provider_log, "session/new")
        assert not Path(turn["cwd"]).exists(), "The read copy survived the refusal"
