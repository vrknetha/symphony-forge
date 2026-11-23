"""forge ask "<question>" runs one read-only Codex turn on the builders' app-server path and prints
the answer. Each test is named test_<n>_<rule> after the Done-when item of the fix it proves.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

from conftest import machine_cores
from test_codex_worker import QUIET, _codex_repo, _sent
from test_codex_worker import sdk_data  # noqa: F401  (a fixture)

import pytest

STORY = "FIX-FORGE-ASK"


def _lanes(repo) -> list[dict]:
    return json.loads(repo.forge("lanes", "--json").stdout)["agents"]["entries"]


def _forge(repo, *args, stall=False):
    return subprocess.Popen([sys.executable, str(repo.bin / "forge"), *args], cwd=repo.path,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            env={**os.environ, **({"STUB_CODEX_STATUS": "stall"} if stall else {})})


@pytest.mark.platform
def test_1_ask_runs_one_read_only_codex_turn(repo, monkeypatch, sdk_data):
    _, stub = _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\nworkers = "codex"\n'
               '\n[models.ask]\nmodel = "gpt-6.2-sol"\neffort = "high"\n')

    # The model comes from [models.ask].
    asked = repo.forge("ask", "Why is the sky blue?")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert "stub codex: built it with" in asked.stdout
    starts, turns = _sent(stub, "thread/start"), _sent(stub, "turn/start")
    assert len(starts) == len(turns) == 1
    assert (starts[0]["sandbox"], starts[0]["approvalPolicy"]) == ("read-only", "never")
    assert starts[0]["config"] == {**QUIET, "model": "gpt-6.2-sol", "model_reasoning_effort": "high"}
    assert turns[0]["sandboxPolicy"]["type"] == "readOnly"
    assert "Why is the sky blue?" in turns[0]["input"][0]["text"]
    # --model beats [models.ask].
    assert repo.forge("ask", "Q", "--model", "gpt-6.2-astra").returncode == 0
    assert _sent(stub, "thread/start")[-1]["config"]["model"] == "gpt-6.2-astra"

    # A failed turn says why and gives a command that runs.
    monkeypatch.setenv("STUB_CODEX_STATUS", "failed")
    failed = repo.forge("ask", "Q")
    assert failed.returncode == 1 and failed.stderr.startswith("Codex ended the turn: failed")
    assert 'Next: forge ask "Q"' in failed.stderr
    monkeypatch.delenv("STUB_CODEX_STATUS")

    # With every place taken, a second ask waits its turn; both show in the lane views as asks.
    if os.name != "nt":
        machine_cores(repo, 2)  # one agent place
        first = _forge(repo, "ask", "Q", stall=True)
        try:
            for _ in range(100):
                if any(run["kind"] == "ask" and run["started_at"] for run in _lanes(repo)):
                    break
                time.sleep(0.2)
            second = _forge(repo, "ask", "Q2")
            for _ in range(100):
                runs = [run for run in _lanes(repo) if run["kind"] == "ask"]
                if len(runs) == 2:
                    break
                time.sleep(0.2)
            assert sorted(bool(run["started_at"]) for run in runs) == [False, True]
            assert {run["title"] for run in runs} == {"A question"} and runs[0]["model"] == "gpt-6.2-sol"
            first.send_signal(signal.SIGINT)
            first.wait(timeout=30)
            out, _ = second.communicate(timeout=60)
            assert second.returncode == 0 and "stub codex" in out
        finally:
            for process in (first, second):
                process.kill()


@pytest.mark.platform
def test_2_a_new_repos_guide_shows_ask(repo, gh, tmp_path):
    client, remote = tmp_path / "client", tmp_path / "client.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(client)], check=True)
    repo.git("remote", "add", "origin", str(remote), cwd=client)
    gh.respond("api", stdout="{}")
    assert repo.forge("init", "--actions", "yes", cwd=client).returncode == 0
    for rel in (".claude/skills/forge/SKILL.md", ".codex/skills/forge/SKILL.md"):
        text = " ".join((client / rel).read_text("utf-8").split())
        assert 'forge ask "<question>" [--model <model>]' in text, rel
