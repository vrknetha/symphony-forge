"""Run Forge against Antigravity's process boundary."""
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from conftest import ROOT
from test_close import blocked, env as close_env, finding
from test_story import worktree
from test_task import story
from test_worker import calls

STORY = "FORGE-ANTIGRAVITY-1"
pytestmark = pytest.mark.platform


def install_agy(repo, monkeypatch):
    home = repo.bin / "agy-home"
    home.mkdir()
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(home))
    stub = repo.bin / "agy"
    shutil.copyfile(ROOT / "tests/stubs/agy", stub)
    stub.chmod(0o755)
    if os.name == "nt":
        shim = stub.with_suffix(".cmd")
        shim.write_text(f'@"{sys.executable}" "%~dp0agy" %*\n', encoding="utf-8")
        stub = shim
    monkeypatch.setenv("AGY_BIN", str(stub))
    return repo.bin / "agy-calls.jsonl"


def setup(repo, gh, monkeypatch, *, local=False):
    log = install_agy(repo, monkeypatch)
    version = repo.forge("--version").stdout.split()[-1]
    settings = (f'version = "{version}"\nrepo = "forge-source"\n'
                'test = "git status --porcelain"\n')
    models = ('workers = "antigravity"\n'
              '[models.build.antigravity]\nmodel = "gemini-4-neon"\neffort = "low"\n'
              '[models.lite.antigravity]\nmodel = "gemini-3.8-flash"\neffort = "medium"\n')
    repo.write("forge.toml", settings if local else settings + models)
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Set up worker")
    repo.git("push", "-q", "origin", "main")
    story(repo)
    for part in ("HELP", "API"):
        started = repo.forge("task", "start", f"BOARD/{part}")
        assert started.returncode == 0, started.stdout + started.stderr
    if local:
        repo.write("forge.local.toml", models)
    return log


def work(repo, item, *args):
    result = repo.forge("work", item, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_1_builds_and_fixes_run_on_antigravity_with_their_model_and_effort(repo, gh, monkeypatch):
    log = setup(repo, gh, monkeypatch)
    monkeypatch.setenv("STUB_AGY_COMMIT", "1")
    folder = worktree(repo, "task/BOARD-HELP")
    second_folder = worktree(repo, "task/BOARD-API")
    output = work(repo, "BOARD/HELP")
    assert "Building BOARD/HELP with Antigravity (gemini-4-neon, low)" in output
    assert "Antigravity runs gemini-4-neon at low." in output
    first, *requests = calls(log)
    assert Path(first["cwd"]).resolve() == folder.resolve()
    assert first["argv"][0:2] == ["acp", "--gemini-dir"]
    assert first["argv"][-1] == "--dangerously-skip-permissions"
    profile = Path(first["argv"][2])
    assert any(r.get("method") == "session/new" and Path(r["params"]["cwd"]) == folder for r in requests)
    assert [(r["params"]["configId"], r["params"]["value"]) for r in requests
            if r.get("method") == "session/set_config_option"] == [
                ("model", "gemini-4-neon"), ("thought_level", "low"),
            ]
    assert "# Worker brief" in next(r["params"]["prompt"][0]["text"] for r in requests
                                    if r.get("method") == "session/prompt")
    assert repo.git("log", "-1", "--format=%s", cwd=folder) == "Build with Antigravity"
    def events(item):
        return [event for path in (repo.path / ".git/forge").rglob("*.jsonl")
                for event in calls(path) if event.get("item") == item
                and event.get("kind") == "worker"]

    assert any(e["event"] == "run start" and e["family"] == "antigravity" for e in events("BOARD/HELP"))
    assert any(e["event"] == "run end" and (e["family"], e["model"], e["effort"], e["input_tokens"])
               == ("antigravity", "gemini-4-neon", "low", 1200) for e in events("BOARD/HELP"))
    monkeypatch.setenv("STUB_AGY_NO_CACHE", "1")
    work(repo, "BOARD/API")
    assert any(e["event"] == "run end" and e["input_tokens"] == 200 for e in events("BOARD/API"))
    second = [r for r in calls(log) if "argv" in r][-1]
    assert Path(second["cwd"]).resolve() == second_folder.resolve()
    other_profile = Path(second["argv"][2])
    assert other_profile != profile
    skills = json.loads((other_profile / "config/skills.json").read_text(encoding="utf-8"))
    assert Path(skills["entries"][0]["path"]) == Path(second["cwd"]) / ".codex/skills"
    started = repo.forge("fix", "start", "Build a spare part", "--done", "The spare part is ready")
    assert started.returncode == 0, started.stdout + started.stderr
    fix_folder = worktree(repo, "fix/build-a-spare-part")
    assert "Antigravity runs gemini-3.8-flash at medium." in work(repo, "build-a-spare-part")
    fix_launch = [r for r in calls(log) if "argv" in r][-1]
    assert Path(fix_launch["cwd"]).resolve() == fix_folder.resolve()
    assert repo.git("log", "-1", "--format=%s", cwd=fix_folder) == "Build with Antigravity"
    assert (fix_folder / "antigravity.txt").is_file()
    repo.write("forge.local.toml", '[models.build.codex]\nmodel="gpt-6.2-sol"\neffort="low"\n')
    settings = Path.home() / ".gemini/antigravity-cli/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"gcp":{"project":"test-project"},"permissions":{"allow":["command(*)"]}}',
                        encoding="utf-8-sig")
    monkeypatch.setenv("STUB_AGY_PLAN", "plus")
    monkeypatch.setenv("STUB_AGY_ASK", "1")
    output = work(repo, "BOARD/API")
    assert "Antigravity runs gemini-4-argon at low." in output
    assert "Next: forge work BOARD/API --note" in output
    last = calls(log)
    turn = last[max(i for i, request in enumerate(last) if "argv" in request):]
    saved_settings = Path(turn[0]["argv"][2]) / "antigravity-cli/settings.json"
    assert json.loads(saved_settings.read_text(encoding="utf-8")) == {"gcp": {"project": "test-project"}}
    assert not any(request.get("params", {}).get("configId") == "model" for request in turn)
    assert any(e["event"] == "run end" and e["model"] == "gemini-4-argon" for e in events("BOARD/API"))
    monkeypatch.delenv("STUB_AGY_ASK")
    repo.write("forge.local.toml", '[models.build.antigravity]\nmodel="gemini-9"\neffort="low"\n')
    refused = repo.forge("work", "BOARD/HELP")
    assert "Antigravity offers no model gemini-9 on this account; it offers gemini-4-argon, gemini-3.8-flash." in refused.stderr
    assert [e for e in events("BOARD/HELP") if e["event"] == "run end"][-1]["outcome"] == "failed"
    head = repo.git("rev-parse", "HEAD", cwd=folder)
    monkeypatch.setenv("STUB_AGY_VERSION", "1.5.11")
    refused = repo.forge("work", "BOARD/HELP")
    assert "Antigravity 1.5.11 is installed, and Forge needs 1.5.12 or newer." in refused.stderr
    monkeypatch.setenv("AGY_BIN", str(repo.bin / "missing-agy"))
    refused = repo.forge("work", "BOARD/HELP")
    assert "Forge cannot run the Antigravity CLI (agy)." in refused.stderr
    assert repo.git("rev-parse", "HEAD", cwd=folder) == head


def test_2_a_repair_round_continues_the_session_with_a_higher_effort(repo, gh, tmp_path, monkeypatch):
    review = close_env.__wrapped__(repo, gh, tmp_path, monkeypatch)
    log = setup(repo, gh, monkeypatch)
    monkeypatch.setenv("STUB_AGY_COMMIT", "1")
    work(repo, "BOARD/HELP")
    initial = calls(log)
    folder = Path(initial[0]["cwd"])
    original = next(r["params"]["sessionId"] for r in initial if r.get("method") == "session/prompt")
    review.reviews(blocked(finding("P1", "Missing help", "antigravity.txt")))
    repo.git("commit", "--allow-empty", "-qm", "Record worker proof", "-m",
             "Proof list:\n- 1: check: stub worker wrote the change", cwd=folder)
    closed = review.close("BOARD/HELP")
    assert "Missing help" in closed.stdout + closed.stderr
    output = work(repo, "BOARD/HELP")
    assert "Antigravity runs gemini-4-neon at high." in output
    repair = calls(log)[len(initial):]
    assert [r["params"]["sessionId"] for r in repair if r.get("method") == "session/resume"] == [original]
    assert not any(r.get("method") == "session/new" for r in repair)
    assert "Missing help" in next(r["params"]["prompt"][0]["text"] for r in repair
                                  if r.get("method") == "session/prompt")
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT", "1")
    monkeypatch.setenv("SSH_CONNECTION", "127.0.0.1 1234 127.0.0.1 22")
    refused = repo.forge("work", "BOARD/HELP")
    assert "Antigravity is not signed in." in refused.stderr
    assert "agy acp --gemini-dir " in refused.stderr and "--login" in refused.stderr
    assert refused.stderr.rstrip().endswith("then forge work BOARD/HELP")
    monkeypatch.delenv("SSH_CONNECTION")
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT")
    monkeypatch.delenv("STUB_AGY_COMMIT")
    monkeypatch.setenv("STUB_AGY_DIRTY", "1")
    before_nudge = len(calls(log))
    work(repo, "BOARD/HELP")
    nudge = calls(log)[before_nudge:]
    assert [r["params"]["sessionId"] for r in nudge if r.get("method") == "session/resume"] == [original, original]
    assert "commit" in [r["params"]["prompt"][0]["text"] for r in nudge
                        if r.get("method") == "session/prompt"][-1].lower()
    monkeypatch.delenv("STUB_AGY_DIRTY")
    monkeypatch.setenv("STUB_AGY_COMMIT", "1")
    monkeypatch.setenv("STUB_AGY_FORGET", "1")
    assert f"Antigravity no longer has session {original}." in work(repo, "BOARD/HELP")
    assert "# Worker brief" in [r["params"]["prompt"][0]["text"] for r in calls(log)
                                if r.get("method") == "session/prompt"][-1]
