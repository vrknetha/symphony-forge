"""Forge commands deliver Claude defaults to role files and the SDK."""
import os
import re
import tomllib

from test_claude_subagents import _new_claude_task
from test_codex_worker import sdk_data  # noqa: F401
from test_setup import _fresh_client
from test_story import DOC, GRILL, new_story, setup
from test_subagent_roles import _claude
from test_worker import calls

STORY = "FIX-NO-OPUS-OUTSIDE-COORDINATOR"

DIAGNOSTICS = ("debugger", "security", "performance")
SONNET = {"model": "claude-sonnet-5-5", "effort": "high"}


def test_1_claude_diagnostics_and_grill_default_to_sonnet_high(repo, gh, tmp_path):
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    settings = client / "forge.toml"
    initial = settings.read_text("utf-8")
    assert tomllib.loads(initial)["models"]["grill"]["claude"] == SONNET
    for name in DIAGNOSTICS:
        fields, _ = _claude(client, name)
        assert (fields["model"], fields["effort"]) == (SONNET["model"], SONNET["effort"]), name

    repo.git("checkout", "-qb", "fix/model-defaults", cwd=client)
    without_grill = re.sub(r'(?ms)^\[models\.grill\.claude\]\n.*?(?=^\[|\Z)', "", initial)
    for model, effort in ((None, "high"), ("opus", "medium")):
        config = without_grill
        if model:
            config += f'\n[models.grill.claude]\nmodel = "{model}"\neffort = "{effort}"\n'
        settings.write_text(config, "utf-8")
        synced = repo.forge("sync", cwd=client)
        assert synced.returncode == 0, synced.stdout + synced.stderr
        fields, _ = _claude(client, "reader")
        assert (fields["model"], fields["effort"]) == (model or SONNET["model"], effort)
        assert settings.read_text("utf-8") == config


def test_2_claude_sdk_diagnostics_use_sonnet_with_the_stock_helper_pair(
        repo, gh, tmp_path, monkeypatch, sdk_data):
    _, _, log = _new_claude_task(repo, gh, tmp_path, monkeypatch, sdk_data)
    worked = repo.forge("work", "BOARD/PAGE")
    assert worked.returncode == 0, worked.stdout + worked.stderr
    [sent] = calls(log)
    agents = sent["options"]["agents"]
    for name in DIAGNOSTICS:
        assert {key: agents[name][key] for key in SONNET} == SONNET, name
    assert agents["general-purpose"]["model"] == "claude-haiku-5-5"
    assert agents["general-purpose"]["effort"] == "high"


def test_3_claude_sdk_plan_read_defaults_to_sonnet_high(repo, monkeypatch, sdk_data):
    setup(repo)
    monkeypatch.setenv("CODEX_THREAD_ID", "thr-coordinator")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(sdk_data))
    monkeypatch.setenv("PYTHONPATH", str(repo.bin) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    shop = new_story(repo, "SHOP")
    settings = shop / "forge.toml"
    settings.write_text(settings.read_text("utf-8").replace(GRILL, ""), "utf-8")
    (shop / "plans/SHOP.md").write_text(DOC, "utf-8")
    read = repo.forge("read", "SHOP")
    assert read.returncode == 0, read.stdout + read.stderr
    [sent] = calls(repo.bin / "claude-calls.jsonl")
    assert {key: sent["options"][key] for key in SONNET} == SONNET
    assert sent["options"]["permission_mode"] == "plan"
