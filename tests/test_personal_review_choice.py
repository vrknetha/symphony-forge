"""A clone can select its own plan reader and code reviewer."""
import json
import os

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env
from test_story import DOC, approved_constitution, new_story, worktree
from test_worker import calls, install_claude

STORY = "who-reviews-or-cold-reads-cannot-be-swit"
pytestmark = pytest.mark.platform


def test_1_local_reviews_selects_the_cold_reader(env, repo, monkeypatch, tmp_path):
    log = install_agy(repo, monkeypatch)
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    settings = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", 'reviews = "claude"\n' + settings)
    approved_constitution(repo)
    repo.git("push", "-q", "origin", "main")
    shop = new_story(repo, "BASKET")
    (shop / "plans/BASKET.md").write_text(DOC, encoding="utf-8")
    teammate = tmp_path / "teammate"
    repo.git("clone", "-q", repo.git("remote", "get-url", "origin"), str(teammate))
    rule = "Keep basket prices in the shop's currency."
    constitution = "docs/product/CONSTITUTION.md"
    env.commit(teammate, constitution, (teammate / constitution).read_text("utf-8") + "\n" + rule + "\n")
    repo.git("push", "-q", "origin", "main", cwd=teammate)

    repo.write("forge.local.toml", 'reviews = "antigravity"\n')
    read = repo.forge("read", "BASKET", cwd=shop)
    assert read.returncode == 0, read.stdout + read.stderr
    [prompt] = [row["params"]["prompt"][0]["text"] for row in calls(log)
                if row.get("method") == "session/prompt"]
    assert rule in prompt


def test_2_local_reviews_selects_the_reviewer_and_refuses_the_builder(
        env, repo, monkeypatch, isolated_codex_home):
    monkeypatch.delenv("CODEX_THREAD_ID")
    (isolated_codex_home / "config.toml").write_text(
        f'[projects.{json.dumps(str(repo.path.resolve()))}]\ntrust_level = "trusted"\n', encoding="utf-8")
    codex = repo.bin / ("codex-app-server.cmd" if os.name == "nt" else "codex-app-server")
    monkeypatch.setenv("CODEX_BIN", str(codex))
    install_claude(repo)
    log = install_agy(repo, monkeypatch)
    settings = (repo.path / "forge.toml").read_text("utf-8")
    env.commit(repo.path, "forge.toml", 'reviews = "claude"\n' + settings)
    repo.git("push", "-q", "origin", "main")
    item = "tidy-readme"
    started = repo.forge("fix", "start", "Readme greets new readers",
                         "--slug", item, "--done", "The readme opens with a greeting")
    assert started.returncode == 0, started.stdout + started.stderr
    folder = worktree(repo, f"fix/{item}")

    repo.write("forge.local.toml", 'workers = "codex"\n')
    monkeypatch.setenv("STUB_CODEX_TOUCH", "greeting.txt")
    monkeypatch.setenv("STUB_CODEX_COMMIT", "1")
    built = repo.forge("work", item)
    assert built.returncode == 0, built.stdout + built.stderr
    repo.git("show", "HEAD:greeting.txt", cwd=folder)

    repo.write("forge.local.toml", 'workers = "claude"\n')
    monkeypatch.setenv("STUB_CLAUDE_LEAVE", "closing.txt")
    monkeypatch.setenv("STUB_CLAUDE_COMMIT_FROM", "1")
    built = repo.forge("work", item)
    assert built.returncode == 0, built.stdout + built.stderr
    repo.git("show", "HEAD:closing.txt", cwd=folder)

    for family, name in (("claude", "Claude Code"), ("codex", "Codex")):
        repo.write("forge.local.toml", f'reviews = "{family}"\n')
        refused = env.close(item)
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert f"{name} built {item}, so Forge will not let {name} review it." in refused.stderr
        assert "set reviews in forge.local.toml" in refused.stderr
        assert not env.review_calls()

    repo.write("forge.local.toml", 'reviews = "antigravity"\n')
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    monkeypatch.setenv("AGY_BIN", "agy.cmd" if os.name == "nt" else "agy")
    monkeypatch.setenv("STUB_AGY_REVIEW", json.dumps({
        "review_completion": "complete", "overall_correctness": "patch is correct",
        "overall_explanation": "The greeting works.", "overall_confidence": 1, "findings": [],
    }))
    env.open_pr("Readme greets new readers")
    closed = env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    assert any(row.get("method") == "session/prompt" for row in calls(log))
