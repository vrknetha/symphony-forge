"""Forge init and sync deliver the Claude defaults and preserve explicit model pins."""
import re
import tomllib

from test_setup import _fresh_client
from test_subagent_roles import _claude

STORY = "FIX-NO-OPUS-OUTSIDE-COORDINATOR"


def test_1_claude_diagnostics_and_grill_default_to_sonnet_high(repo, gh, tmp_path):
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    settings = client / "forge.toml"
    initial = settings.read_text("utf-8")
    sonnet = {"model": "claude-sonnet-5-5", "effort": "high"}
    assert tomllib.loads(initial)["models"]["grill"]["claude"] == sonnet
    for name in ("debugger", "security", "performance"):
        fields, _ = _claude(client, name)
        assert (fields["model"], fields["effort"]) == (sonnet["model"], sonnet["effort"]), name

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
        assert (fields["model"], fields["effort"]) == (model or sonnet["model"], effort)
        assert settings.read_text("utf-8") == config
