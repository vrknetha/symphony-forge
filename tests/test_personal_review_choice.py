"""A clone can select its own plan reader and code reviewer."""
import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env
from test_story import DOC, approved_constitution, new_story
from test_worker import calls

STORY = "who-reviews-or-cold-reads-cannot-be-swit"
pytestmark = pytest.mark.platform


def test_1_local_reviews_selects_the_cold_reader(env, repo, monkeypatch):
    log = install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    settings = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", 'reviews = "claude"\n' + settings)
    approved_constitution(repo)
    repo.git("push", "-q", "origin", "main")
    shop = new_story(repo, "BASKET")
    (shop / "plans/BASKET.md").write_text(DOC, encoding="utf-8")

    repo.write("forge.local.toml", 'reviews = "antigravity"\n')
    read = repo.forge("read", "BASKET", cwd=shop)
    assert read.returncode == 0, read.stdout + read.stderr
    assert any(row.get("method") == "session/prompt" for row in calls(log))


def test_2_local_reviews_selects_the_reviewer_and_refuses_the_builder(env, repo):
    settings = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", 'reviews = "claude"\n' + settings)
    repo.git("push", "-q", "origin", "main")
    item, _ = env.start_fix(worker="claude")

    repo.write("forge.local.toml", 'reviews = "claude"\n')
    refused = env.close(item)
    assert refused.returncode == 1
    assert f"Claude Code built {item}, so Forge will not let Claude Code review it." in refused.stderr
    assert "set reviews in forge.local.toml" in refused.stderr
    assert not env.review_calls()

    repo.write("forge.local.toml", 'reviews = "codex"\n')
    env.open_pr("Readme greets new readers")
    closed = env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    [review] = env.review_calls()
    assert review["args"][review["args"].index("--engine") + 1] == "codex"
