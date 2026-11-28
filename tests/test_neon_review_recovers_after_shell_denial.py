"""Close gets a valid Neon report after a denied shell call ends the turn."""
import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env
from test_worker import calls

STORY = "when-neon-tries-to-run-a-shell-command-a"


@pytest.mark.platform
@pytest.mark.parametrize(("stop_reason", "refusal"), [("end_turn", "request"), ("cancelled", "update")])
def test_1_close_recovers_neon_review_after_shell_denial(env, repo, monkeypatch, stop_reason, refusal):
    log = install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    monkeypatch.setenv("STUB_AGY_REVIEW_RECOVERY", stop_reason)
    monkeypatch.setenv("STUB_AGY_REVIEW_PERMISSION", refusal)
    settings = (repo.path / "forge.toml").read_text(encoding="utf-8")
    env.commit(repo.path, "forge.toml", settings + 'reviews = "antigravity"\n'
               '[models.review.antigravity]\nmodel = "gemini-4-neon"\n')
    repo.git("push", "-q", "origin", "main")
    item, _ = env.start_fix(worker="claude")
    env.open_pr("Change the greeting")

    closed = env.close(item)

    output = closed.stdout + closed.stderr
    assert closed.returncode == 0, output
    initial, recovery = [row["params"] for row in calls(log) if row.get("method") == "session/prompt"]
    assert "+print('hello')" in initial["prompt"][0]["text"]
    assert initial["sessionId"] == recovery["sessionId"]
    assert "read-only file tools" in recovery["prompt"][0]["text"]
