"""Antigravity cold reads use a filtered copy and reviews use the configured family."""
import os
from pathlib import Path

import pytest

from conftest import ROOT
from test_antigravity_build import install_agy
from test_close import env as close_env
from test_story import DOC, approved_constitution, new_story
from test_worker import calls

STORY = "FORGE-ANTIGRAVITY-1"


@pytest.mark.platform
def test_3_antigravity_reads_and_reviews_safely_and_own_family_reviews_are_refused(
        repo, gh, monkeypatch, tmp_path):
    close = close_env.__wrapped__(repo, gh, tmp_path, monkeypatch)
    log = install_agy(repo, monkeypatch)
    settings = (repo.path / "forge.toml").read_text("utf-8")
    close.commit(repo.path, "forge.toml", settings + 'reviews = "claude"\n')
    repo.git("push", "-q", "origin", "main")
    item, fix = close.start_fix(worker="claude")
    head = repo.git("rev-parse", "HEAD", cwd=fix)
    rejected = close.close(item)
    assert rejected.returncode == 1
    assert f"Claude Code built {item}, so Forge will not let Claude Code review it." in rejected.stderr
    assert repo.git("rev-parse", "HEAD", cwd=fix) == head
    assert not close.review_calls()
    close.commit(repo.path, "forge.toml", settings + 'reviews = "codex"\n')
    repo.git("push", "-q", "origin", "main")
    close.open_pr("Readme greets new readers")
    reviewed = close.close(item)
    assert reviewed.returncode == 0, reviewed.stdout + reviewed.stderr
    [review] = close.review_calls()
    assert review["args"][review["args"].index("--engine") + 1] == "codex"

    close.commit(repo.path, "AGENTS.md", "# Rules\n\n## Review rules\nCheck basket totals.\n")
    approved_constitution(repo)
    repo.git("push", "-q", "origin", "main")
    shop = new_story(repo, "BASKET")
    remote_doc = shop / "plans/BASKET.md"
    remote_doc.write_text(DOC, encoding="utf-8")
    repo.git("add", "--", "plans/BASKET.md", cwd=shop)
    repo.git("commit", "-qm", "Save basket plan", cwd=shop)
    repo.git("push", "-q", "origin", "story/BASKET", cwd=shop)
    remote = repo.git("remote", "get-url", "origin", cwd=repo.path)
    remote_shop = tmp_path / "remote-reader"
    repo.git("clone", "-q", "--branch", "story/BASKET", remote, str(remote_shop), cwd=repo.path)
    repo.git("config", "core.hooksPath", "checkout-hooks", cwd=remote_shop)
    close.commit(repo.path, "forge.toml", settings + 'reviews = "antigravity"\n')
    repo.git("push", "-q", "origin", "main")
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    monkeypatch.setenv("AUTOREVIEW", str(fixture / "scripts/autoreview"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "agent-data"))
    (repo.bin / "claude_agent_sdk.py").unlink(missing_ok=True)
    close.commit(shop, ".env.production", "Example secret.\n")
    close.commit(shop, ".gitignore", "ignored.txt\n")
    close.commit(shop, ".gitattributes", "filtered.txt filter=crypt\n")
    close.commit(shop, "filtered.txt", "Committed text.\n")
    doc = shop / "plans/BASKET.md"
    doc.write_text(DOC + "\nA working-tree amendment.\n", encoding="utf-8")
    brief = shop / "docs/product/BRIEF.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("A working-tree product brief.", encoding="utf-8")
    (shop / "filtered.txt").write_text("Readable working-tree text.", encoding="utf-8")
    repo.git("config", "filter.crypt.clean", "git hash-object --stdin", cwd=shop)
    ignore = tmp_path / "personal-ignore"
    ignore.write_text(".npmrc\n", encoding="utf-8")
    global_config = tmp_path / "personal-gitconfig"
    repo.git("config", "--file", str(global_config), "core.excludesFile", ignore.as_posix())
    repo.git("config", "--file", str(global_config), "user.name", "Test Reader")
    repo.git("config", "--file", str(global_config), "user.email", "reader@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    (shop / ".npmrc").write_text("Example private registry settings.\n", encoding="utf-8")
    if os.name != "nt":  # Windows requires a host privilege to create symlinks.
        (shop / "notes.md").symlink_to(".env.production")
        (shop / "registry-notes.md").symlink_to(".npmrc")
        (shop / "_agents").mkdir()
        (shop / "_agents/hooks.json").symlink_to("../filtered.txt")
    monkeypatch.setenv("STUB_AGY_TOUCH", "touch.txt")
    monkeypatch.setenv("STUB_AGY_ESCAPE", str(shop / "ignored.txt"))
    monkeypatch.setenv("STUB_AGY_PEEK", str(brief))
    monkeypatch.setenv("STUB_AGY_FETCH", "1")
    monkeypatch.setenv("STUB_AGY_SHOW", "plans/BASKET.md,docs/product/BRIEF.md,filtered.txt")
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT", "1")
    remote_trace = tmp_path / "remote-read-git.jsonl"
    monkeypatch.setenv("GIT_TRACE2_EVENT", str(remote_trace))
    monkeypatch.setenv("GIT_TRACE2_CONFIG_PARAMS", "core.hooksPath")
    repo.git("remote", "set-url", "origin", str(tmp_path / "missing.git"), cwd=remote_shop)
    before = len(calls(log))
    unavailable = repo.forge("read", "BASKET", cwd=remote_shop)
    assert unavailable.returncode == 1
    assert unavailable.stderr == ("Forge could not check the latest reader settings.\n"
                                  "Next: check origin, then forge read BASKET\n")
    assert len(calls(log)) == before
    repo.git("remote", "set-url", "origin", remote, cwd=remote_shop)
    remote_read = repo.forge("read", "BASKET", cwd=remote_shop)
    assert remote_read.returncode == 1 and "Antigravity is not signed in." in remote_read.stderr
    assert 'reviews = "antigravity"' in repo.git("show", "origin/main:forge.toml", cwd=remote_shop)
    fetches = [event["sid"] for event in calls(remote_trace)
               if event["event"] == "cmd_name" and event["name"] == "fetch"]
    assert fetches
    for fetch in fetches:
        hook_paths = [event["value"] for event in calls(remote_trace)
                      if event["sid"] == fetch and event.get("param") == "core.hookspath"]
        assert hook_paths and Path(hook_paths[-1]).is_absolute()
        assert not Path(hook_paths[-1]).is_relative_to(remote_shop)
    refused = repo.forge("read", "BASKET", cwd=shop)
    assert refused.stderr.rstrip().endswith("then forge read BASKET"), refused.stderr
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT")

    # No driver is available for this required filter. Cold reads do not need to use it.
    repo.git("config", "filter.unavailable.required", "true", cwd=shop)
    with (shop / ".gitattributes").open("a", encoding="utf-8") as attributes:
        attributes.write("private-format.txt filter=unavailable\n")
    (shop / "private-format.txt").write_text("Example working-tree bytes.", encoding="utf-8")
    repo.git("config", "core.hooksPath", "checkout-hooks", cwd=shop)
    trace = tmp_path / "read-git.jsonl"
    monkeypatch.setenv("GIT_TRACE2_EVENT", str(trace))
    monkeypatch.setenv("GIT_TRACE2_CONFIG_PARAMS", "core.hooksPath")
    read = repo.forge("read", "BASKET", cwd=shop)
    assert read.returncode == 0, read.stdout + read.stderr
    git_events = calls(trace)
    [commit] = [event["sid"] for event in git_events
                if event["event"] == "cmd_name" and event["name"] == "commit"]
    hooks_paths = [event["value"] for event in git_events
                   if event["sid"] == commit and event.get("param") == "core.hookspath"]
    assert hooks_paths and Path(hooks_paths[-1]).is_absolute()
    assert not Path(hooks_paths[-1]).is_relative_to(shop)
    launch = [line for line in calls(log) if "argv" in line][-1]
    copy = Path(launch["cwd"])
    assert copy.parts[-2:] == ("read", "BASKET") and not copy.is_relative_to(shop)
    assert launch["argv"] == ["acp", "--gemini-dir", launch["argv"][2]]
    assert Path(launch["argv"][2]).name == "read-profile"
    assert not any((copy / path).exists() for path in (
        ".git", ".env.production", ".npmrc", "notes.md", "registry-notes.md", "_agents",
        "AGENTS.md", "touch.txt"))
    if os.name != "nt":
        assert copy.parents[1].stat().st_mode & 0o077 == 0
    assert not (shop / "ignored.txt").exists()
    [shown] = [line["files"] for line in calls(log) if "files" in line]
    assert shown == {"plans/BASKET.md": doc.read_text("utf-8"),
                     "docs/product/BRIEF.md": brief.read_text("utf-8"),
                     "filtered.txt": "Readable working-tree text."}
    prompt = [line for line in calls(log) if line.get("method") == "session/prompt"][-1]
    assert "Check basket totals." in prompt["params"]["prompt"][0]["text"]
    decisions = {line["id"]: line["result"]["outcome"]["optionId"] for line in calls(log)
                 if str(line.get("id", "")).startswith("read-") and "result" in line}
    assert decisions == {"read-outside": "no", "read-unknown": "no", "read-fetch": "no",
                         "read-inside": "yes"}
    assert "See /plans/BASKET.md" in (shop / "plans/BASKET.read.md").read_text("utf-8")
    doc.write_text(doc.read_text("utf-8").replace("A working-tree amendment.", "A second amendment."),
                   encoding="utf-8")
    rerun = repo.forge("read", "BASKET", cwd=shop)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    [resume] = [line for line in calls(log) if line.get("method") == "session/resume"]
    assert resume["params"]["sessionId"] == prompt["params"]["sessionId"]

    # Readable inputs can still be copied, but a filtered plan cannot be committed as plain text.
    with (shop / ".gitattributes").open("a", encoding="utf-8") as attributes:
        attributes.write("plans/BASKET.md filter=crypt\n")
    head = repo.git("rev-parse", "HEAD", cwd=shop)
    before = len(calls(log))
    unsafe = repo.forge("read", "BASKET", cwd=shop)
    assert unsafe.returncode == 1
    assert "Forge cannot safely record an Antigravity read with a Git filter on plans/BASKET.md." in unsafe.stderr
    assert repo.git("rev-parse", "HEAD", cwd=shop) == head
    assert len(calls(log)) == before
