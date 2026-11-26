"""Close keeps a written review or identifies the tool that was refused."""
import json

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env

STORY = "neon-s-review-ends-with-review-engine-re"


@pytest.mark.platform
def test_1_antigravity_review_names_a_refused_tool_when_no_answer(env, repo, monkeypatch):
    install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    monkeypatch.setenv("STUB_AGY_REVIEW_PERMISSION", "1")
    settings = (repo.path / "forge.toml").read_text(encoding="utf-8")
    env.commit(repo.path, "forge.toml", settings + 'reviews = "antigravity"\n'
               '[models.review.antigravity]\nmodel = "gemini-4-neon"\n')
    repo.git("push", "-q", "origin", "main")
    item, _ = env.start_fix(worker="claude")
    env.open_pr("Change the greeting")

    closed = env.close(item)

    output = closed.stdout + closed.stderr
    assert closed.returncode == 1, output
    assert 'Forge refused the tool "Inspect the patch with Git"' in output, output
    assert "empty output" not in output

    monkeypatch.setenv("STUB_AGY_REVIEW", json.dumps({
        "review_completion": "complete", "overall_correctness": "patch is correct",
        "overall_explanation": "The greeting still works.", "overall_confidence": 1,
        "findings": [],
    }))
    reviewed = env.close(item)
    assert reviewed.returncode == 0, reviewed.stdout + reviewed.stderr
