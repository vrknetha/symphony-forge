"""Close keeps a written review or identifies the tool that was refused."""
import json

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env, finding
from test_run_records import records
from test_worker import calls

STORY = "neon-s-review-ends-with-review-engine-re"


@pytest.mark.platform
def test_1_antigravity_review_names_a_refused_tool_when_no_answer(env, repo, monkeypatch, fake_clock):
    log = install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    settings = (repo.path / "forge.toml").read_text(encoding="utf-8")
    env.commit(repo.path, "forge.toml", settings + 'reviews = "antigravity"\n'
               '[models.review.antigravity]\nmodel = "gemini-4-neon"\n')
    repo.git("push", "-q", "origin", "main")
    item, _ = env.start_fix(worker="claude")
    env.open_pr("Change the greeting")

    def failed_reviews():
        return [row for row in records(repo, "events.jsonl") if row["item"] == item
                and row["event"] == "run end" and row["kind"] == "review" and row["outcome"] == "failed"]

    for index, (refusal, reply) in enumerate((
        ("request", ""),
        ("update", ""),
        ("request", json.dumps({"findings": []})),
    ), 1):
        monkeypatch.setenv("STUB_AGY_REVIEW_PERMISSION", refusal)
        monkeypatch.setenv("STUB_AGY_REVIEW", reply)
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        assert closed.returncode == 1, output
        assert "Review service rate limit. Waiting" not in output, output
        assert 'after this tool was refused "Inspect rate limit configuration"' in output, output
        assert "empty output" not in output and "non-JSON output" not in output, output
        runs = failed_reviews()
        assert len(runs) == index * 2
        sessions = [row["params"]["sessionId"] for row in calls(log) if row.get("method") == "session/prompt"]
        assert [row["chat"] for row in runs] == sessions
        assert all((row["input_tokens"], row["cached_input_tokens"], row["output_tokens"])
                   == (1200, 1000, 300) for row in runs)

    serious = finding("P1", "The greeting omits the reader")
    serious["code_location"].pop("column")
    serious["source_attribution"] = None
    monkeypatch.setenv("STUB_AGY_REVIEW", json.dumps({
        "review_completion": "complete", "overall_correctness": "patch is incorrect",
        "overall_explanation": serious["title"], "overall_confidence": 1,
        "findings": [serious],
    }, indent=2))
    reviewed = env.close(item)
    output = reviewed.stdout + reviewed.stderr
    assert reviewed.returncode == 1, output
    assert "The review left serious findings open" in output, output
    assert serious["title"] in output, output
