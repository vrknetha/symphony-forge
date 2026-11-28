"""Close gets a valid Neon report after a denied shell call ends the turn."""
import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env
from test_run_records import records
from test_worker import calls

STORY = "when-neon-tries-to-run-a-shell-command-a"


@pytest.fixture
def neon_review(env, repo, monkeypatch):
    log = install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    settings = (repo.path / "forge.toml").read_text(encoding="utf-8")
    env.commit(repo.path, "forge.toml", settings + 'reviews = "antigravity"\n'
               '[models.review.antigravity]\nmodel = "gemini-4-neon"\n')
    repo.git("push", "-q", "origin", "main")
    item, _ = env.start_fix(worker="claude")
    env.open_pr("Change the greeting")
    return item, log


@pytest.mark.platform
@pytest.mark.parametrize(("stop_reason", "refusal"), [
    ("end_turn", "request"), ("cancelled", "update"), ("end_turn", "id-only"),
])
def test_1_close_recovers_neon_review_after_shell_denial(env, monkeypatch, neon_review, stop_reason, refusal):
    item, log = neon_review
    monkeypatch.setenv("STUB_AGY_REVIEW_RECOVERY", stop_reason)
    monkeypatch.setenv("STUB_AGY_REVIEW_PERMISSION", refusal)

    closed = env.close(item)

    output = closed.stdout + closed.stderr
    assert closed.returncode == 0, output
    initial, recovery = [row["params"] for row in calls(log) if row.get("method") == "session/prompt"]
    assert "+print('hello')" in initial["prompt"][0]["text"]
    assert initial["sessionId"] == recovery["sessionId"]
    assert "read-only file tools" in recovery["prompt"][0]["text"]


@pytest.mark.platform
def test_2_close_records_first_neon_turn_usage_when_recovery_fails(env, repo, monkeypatch, neon_review):
    item, _ = neon_review
    monkeypatch.setenv("STUB_AGY_REVIEW_RECOVERY", "connection-error")
    monkeypatch.setenv("STUB_AGY_REVIEW_PERMISSION", "request")

    closed = env.close(item)

    output = closed.stdout + closed.stderr
    assert closed.returncode == 1 and "Review connection lost" in output, output
    usage = [(row["input_tokens"], row["cached_input_tokens"], row["output_tokens"])
             for row in records(repo, "events.jsonl") if row["item"] == item
             and row["event"] == "run end" and row["kind"] == "review" and row["outcome"] == "failed"]
    assert usage and set(usage) == {(1200, 1000, 300)}
