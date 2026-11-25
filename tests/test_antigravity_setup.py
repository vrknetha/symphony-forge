"""Doctor and init report supported Antigravity setup at the command boundary."""
from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from test_antigravity_build import install_agy
from test_close import CLEAN, GREEN, PIN, Forge
from test_setup import _fresh_client
from test_task import story as seed_story

STORY = "FORGE-ANTIGRAVITY-1"
pytestmark = pytest.mark.platform


def _doctor_settings(repo, top: Path, workers="claude", reviews="antigravity", local=""):
    path = top / "forge.toml"
    settings = path.read_text(encoding="utf-8")
    settings = re.sub(r'^workers = ".*"$', f'workers = "{workers}"', settings, flags=re.M)
    settings = re.sub(r'^tools = ".*"$', 'tools = "claude"', settings, flags=re.M)
    if not re.search(r"(?m)^tools =", settings):
        first_table = re.search(r"(?m)^\[", settings)
        at = first_table.start() if first_table else len(settings)
        settings = settings[:at] + 'tools = "claude"\n\n' + settings[at:]
    settings = re.sub(r'^reviews = ".*"\n?', "", settings, flags=re.M)
    if reviews:
        first_table = re.search(r"(?m)^\[", settings)
        at = first_table.start() if first_table else len(settings)
        settings = settings[:at] + f'reviews = "{reviews}"\n\n' + settings[at:]
    path.write_text(settings, encoding="utf-8")
    local_path = top / "forge.local.toml"
    if local:
        local_path.write_text(local, encoding="utf-8")
    else:
        local_path.unlink(missing_ok=True)


def _install_autoreview(tmp_path, monkeypatch):
    folder = tmp_path / "autoreview"
    scripts = folder / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "tests/stubs/autoreview"
    shutil.copyfile(source, scripts / "autoreview")
    (folder / ".upstream-sha").write_text(PIN + "\n", encoding="utf-8")
    monkeypatch.setenv("AUTOREVIEW", str(scripts / "autoreview"))
    monkeypatch.setenv("AUTOREVIEW_STUB", str(tmp_path / "reviews.json"))
    (tmp_path / "reviews.json").write_text(json.dumps([CLEAN]), encoding="utf-8")


def _doctor_client(repo, gh, tmp_path, monkeypatch):
    gh.respond("auth", "status", stdout="Logged in to GitHub\n")
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    _install_autoreview(tmp_path, monkeypatch)
    return client


def test_5_doctor_reports_antigravity(repo, gh, tmp_path, monkeypatch):
    log = install_agy(repo, monkeypatch)
    client = _doctor_client(repo, gh, tmp_path, monkeypatch)
    cases = [
        ("missing", "claude", None, "Forge cannot run the Antigravity CLI (agy)."),
        ("old", "claude", "1.5.11",
         "Antigravity 1.5.11 is installed, and Forge needs 1.5.12 or newer."),
        ("signed out", "antigravity", "1.5.14",
         "Antigravity is not signed in."),
        ("unknown", "claude", "1.5.14",
         "Forge could not check Antigravity's sign-in:"),
        ("signed in", "antigravity", "1.5.14", ""),
    ]
    for case, workers, version, expected in cases:
        _doctor_settings(repo, client, workers, "antigravity",
                         'workers = "antigravity"\n' if case == "missing" else "")
        monkeypatch.setenv("AGY_BIN", str(repo.bin / "missing-agy") if version is None
                           else str(repo.bin / ("agy.cmd" if os.name == "nt" else "agy")))
        monkeypatch.delenv("STUB_AGY_SIGNED_OUT", raising=False)
        monkeypatch.delenv("STUB_AGY_SIGNED_OUT_FULL", raising=False)
        monkeypatch.delenv("STUB_AGY_BROKEN", raising=False)
        if version is not None:
            monkeypatch.setenv("STUB_AGY_VERSION", version)
        if case == "signed out":
            monkeypatch.setenv("STUB_AGY_SIGNED_OUT", "1")
        elif case == "unknown":
            monkeypatch.setenv("STUB_AGY_BROKEN", "1")

        checked = repo.forge("doctor", cwd=client)
        output = checked.stdout + checked.stderr
        if expected:
            assert expected in output, output
        else:
            assert "Antigravity is not signed in." not in output, output
            assert "Forge could not check Antigravity's sign-in:" not in output, output
        if case in ("signed out", "unknown"):
            assert ("run agy and sign in" if case == "signed out"
                    else "run agy to check it, then forge doctor") in output
        if case == "signed in":
            assert "Antigravity" not in output, output
        if case == "unknown":
            assert "Everything checks out for Forge" not in output, output

    # SSH does not share the keyring, so Doctor checks this checkout's full profile.
    _doctor_settings(repo, client, workers="claude", reviews="antigravity")
    monkeypatch.setenv("STUB_AGY_VERSION", "1.5.14")
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT", raising=False)
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT_FULL", raising=False)
    monkeypatch.setenv("SSH_CONNECTION", "127.0.0.1 1234 127.0.0.1 22")
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT_FULL", "1")
    checked = repo.forge("doctor", cwd=client)
    assert "Antigravity's full profile for this checkout is not signed in." in checked.stdout, checked.stdout
    assert "agy acp --gemini-dir" in checked.stdout and "--login" in checked.stdout
    assert log.is_file()
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT_FULL")

    # Without either selector, Doctor does not probe or report an installed CLI.
    _doctor_settings(repo, client, workers="claude", reviews="claude")
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT", "1")
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT_FULL", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    checked = repo.forge("doctor", cwd=client)
    assert "Antigravity" not in checked.stdout + checked.stderr
    monkeypatch.delenv("SSH_CONNECTION", raising=False)

    # Sync the opt-in on the approved story branch, then fast-forward the initialized checkout.
    client_repo = type(repo)(client, repo.bin)
    _doctor_settings(repo, client, workers="antigravity", reviews="antigravity")
    seed_story(client_repo)
    client_repo.git("checkout", "story/BOARD")
    synced = repo.forge("sync", cwd=client)
    assert synced.returncode == 0, synced.stdout + synced.stderr
    client_repo.git("add", "-A")
    client_repo.git("commit", "-qm", "Sync Antigravity setup")
    client_repo.git("checkout", "main")
    client_repo.git("merge", "--ff-only", "story/BOARD")
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT", raising=False)
    monkeypatch.setenv("SSH_CONNECTION", "127.0.0.1 1234 127.0.0.1 22")
    checked = repo.forge("doctor", cwd=client)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "Antigravity is not signed in." not in checked.stdout
    assert "could not check Antigravity's sign-in" not in checked.stdout
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT_FULL", "1")
    started = repo.forge("task", "start", "BOARD/HELP", cwd=client)
    assert started.returncode == 0, started.stdout + started.stderr
    output = started.stdout + started.stderr
    assert "Started BOARD/HELP on task/BOARD-HELP" in output, output
    assert "Antigravity's full profile for this worktree is not signed in." in output, output
    assert "agy acp --gemini-dir" in output and "--login" in output, output
    assert "Next: forge work BOARD/HELP" not in output, output
    assert output.rstrip().endswith("then forge work BOARD/HELP"), output
    where = Path(re.search(r" in (.+)$", started.stdout.splitlines()[0])[1])
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    launch = next(call for call in reversed(calls) if call.get("argv", [None])[0:1] == ["acp"])
    profile = Path(launch["argv"][launch["argv"].index("--gemini-dir") + 1])
    assert str(profile.resolve()) in output
    skills = json.loads((profile / "config/skills.json").read_text(encoding="utf-8"))
    assert Path(skills["entries"][0]["path"]).resolve() == (where / ".codex/skills").resolve()

    # An unknown result gives a person a way to check the new profile before work.
    monkeypatch.delenv("STUB_AGY_SIGNED_OUT_FULL")
    monkeypatch.setenv("STUB_AGY_BROKEN", "1")
    uncertain = repo.forge("task", "start", "BOARD/API", cwd=client)
    assert uncertain.returncode == 0, uncertain.stdout + uncertain.stderr
    output = uncertain.stdout + uncertain.stderr
    assert "could not check Antigravity's sign-in for this worktree" in output, output
    assert "Next: cd " in output and "&& forge doctor" in output, output
    assert "Next: forge work BOARD/API" not in output, output


@pytest.mark.parametrize("version,installed", [("1.5.14", True), ("1.5.11", False), (None, False)])
def test_6_new_repo_says_antigravity_is_installed_and_other_repos_are_unchanged(
        repo, gh, tmp_path, monkeypatch, version, installed):
    log = install_agy(repo, monkeypatch)
    if version is None:
        monkeypatch.delenv("STUB_AGY_VERSION", raising=False)
        monkeypatch.setenv("AGY_BIN", str(repo.bin / "missing-agy"))
    else:
        monkeypatch.setenv("STUB_AGY_VERSION", version)
    # Init must report installation without asking for sign-in.
    monkeypatch.setenv("STUB_AGY_SIGNED_OUT", "1")
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    if installed:
        assert "Antigravity 1.5.14 is installed. Ask your agent if you want it to build or review; " \
               "forge doctor checks its sign-in." in initialized.stdout
    else:
        assert "Antigravity" not in initialized.stdout
    config = tomllib.loads((client / "forge.toml").read_text(encoding="utf-8"))
    assert config["workers"] == "claude"
    assert "reviews" not in config
    assert "antigravity" not in json.dumps(config)
    assert not log.exists()

    synced = repo.forge("sync", cwd=client)
    assert synced.returncode == 0, synced.stdout + synced.stderr
    assert not (client / ".agents").exists()

    if installed:
        _install_autoreview(tmp_path, monkeypatch)
        client_repo = type(repo)(client, repo.bin)
        fixture = Forge(client_repo, gh, tmp_path)
        fixture.reviews(CLEAN)
        fixture.checks(GREEN)
        gh.respond("pr", "list", stdout="[]")
        gh.respond("pr", "create", stdout="https://github.com/acme/client/pull/7\n")
        gh.respond("pr", "edit")
        gh.respond("pr", "ready")
        started = repo.forge("fix", "start", "Readme greets new readers", "--done",
                             "The readme opens with a greeting", "--kind", "mechanical", cwd=client)
        assert started.returncode == 0, started.stdout + started.stderr
        first = started.stdout.splitlines()[0]
        item = re.search(r"Started fix ([a-z0-9-]+) on fix/", first)[1]
        where = Path(first.rsplit(" in ", 1)[1].rstrip("."))
        fixture.commit(where, "README.md", "# Welcome\n", "Work\n\nProof list:\n"
                       "- Done when: check: The readme opens with a greeting")
        closed = fixture.close(item)
        assert closed.returncode == 0, closed.stdout + closed.stderr
        [call] = fixture.review_calls()
        assert call["args"][call["args"].index("--engine") + 1] == "codex"
