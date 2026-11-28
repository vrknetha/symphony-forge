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

from conftest import ROOT, machine_cores
from test_antigravity_build import install_agy
from test_codex_worker import QUIET, _codex_repo, _sent, _stub
from test_codex_worker import sdk_data  # noqa: F401  (a fixture)
from test_worker import calls as claude_calls, install_claude

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
    default_config = (repo.path / "forge.toml").read_text(encoding="utf-8")
    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\nworkers = "codex"\n'
               '\n[models.ask]\nmodel = "gpt-6.2-sol"\neffort = "high"\n')

    # The model comes from [models.ask], and the answer is printed and recorded in the work log.
    asked = repo.forge("ask", "Why is the sky blue?")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert "stub codex: built it with" in asked.stdout
    assert any("stub codex: built it with" in text for text in _ask_logs(repo))
    assert [call["forge_worker"] for call in _stub(stub) if "pid" in call] == ["1"]
    starts, turns = _sent(stub, "thread/start"), _sent(stub, "turn/start")
    assert len(starts) == len(turns) == 1
    assert (starts[0]["sandbox"], starts[0]["approvalPolicy"]) == ("read-only", "never")
    assert starts[0]["config"] == {**QUIET, "model": "gpt-6.2-sol", "model_reasoning_effort": "high"}
    assert turns[0]["sandboxPolicy"]["type"] == "readOnly"
    assert "Why is the sky blue?" in turns[0]["input"][0]["text"]
    # --model beats [models.ask].
    assert repo.forge("ask", "Q", "--model", "gpt-6.2-astra").returncode == 0
    assert _sent(stub, "thread/start")[-1]["config"]["model"] == "gpt-6.2-astra"

    # A failed turn says why and gives a safe retry line (replacing the old raw-question echo).
    monkeypatch.setenv("STUB_CODEX_STATUS", "failed")
    failed = repo.forge("ask", "Q")
    assert failed.returncode == 1 and failed.stderr.startswith("Codex ended the turn: failed")
    assert "Next: run forge ask again with the same question\n" in failed.stderr
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
            # The waiting ask must not have invoked Codex before acquiring the agent place.
            assert not any("Q2" in turn["input"][0]["text"] for turn in _sent(stub, "turn/start"))
            first.send_signal(signal.SIGINT)
            first.wait(timeout=30)
            out, _ = second.communicate(timeout=60)
            assert second.returncode == 0 and "stub codex" in out
            assert any("Q2" in turn["input"][0]["text"] for turn in _sent(stub, "turn/start"))
        finally:
            for process in (first, second):
                process.kill()

    repo.write("forge.toml", default_config)
    asked = repo.forge("ask", "What changed?", "--model", "gpt-6.2-sol")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert "model_reasoning_effort" not in _sent(stub, "thread/start")[-1]["config"]
    assert "effort" not in _sent(stub, "turn/start")[-1]


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


def _ask_logs(repo) -> list[str]:
    logs = repo.path / ".git" / "forge"
    if not logs.exists():
        return []
    return [p.read_text("utf-8", errors="replace") for p in sorted(logs.glob("work-ask-*.log"))]


def _install_agy_with_autoreview(repo, monkeypatch):
    log = install_agy(repo, monkeypatch)
    monkeypatch.setenv("AUTOREVIEW", str(ROOT / "tests/fixtures/autoreview-ce14dcca/scripts/autoreview"))
    return log


def _wait_in_line(repo, model: str, expected_text: str, count_calls) -> None:
    """Hold the single agent place with a stalled Codex ask and verify `model` runs only after acquiring it."""
    before_calls = count_calls()
    before_expected_logs = sum(expected_text in text for text in _ask_logs(repo))
    first = _forge(repo, "ask", "Hold", "--model", "gpt-6.2-sol", stall=True)
    second = None
    try:
        for _ in range(100):
            if any(run["kind"] == "ask" and run["started_at"] for run in _lanes(repo)):
                break
            time.sleep(0.2)
        second = _forge(repo, "ask", "Waiting question", "--model", model)
        runs = []
        for _ in range(100):
            runs = [run for run in _lanes(repo) if run["kind"] == "ask"]
            if len(runs) == 2:
                break
            time.sleep(0.2)
        assert sorted(bool(run["started_at"]) for run in runs) == [False, True]
        assert any(run["model"] == model and not run["started_at"] for run in runs)
        # While queued in agent_slot, neither the provider nor its work log has been written yet.
        assert second.poll() is None
        assert count_calls() == before_calls
        assert sum(expected_text in text for text in _ask_logs(repo)) == before_expected_logs
        first.send_signal(signal.SIGINT)
        first.wait(timeout=30)
        out, err = second.communicate(timeout=60)
        assert second.returncode == 0, out + err
        assert expected_text in out
        assert count_calls() == before_calls + 1
        assert sum(expected_text in text for text in _ask_logs(repo)) == before_expected_logs + 1
    finally:
        for process in (first, second):
            if process is not None:
                process.kill()


@pytest.mark.platform
def test_3_ask_routes_claude_and_gemini_and_records_answers(repo, monkeypatch, sdk_data):
    _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    install_claude(repo, worker=True)
    claude_log = repo.bin / "claude-calls.jsonl"
    monkeypatch.setenv("STUB_CLAUDE_RESULT", "Claude final answer\n")
    asked = repo.forge("ask", "Explain this module", "--model", "claude-haiku-5-5")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert asked.stdout.strip() == "Claude final answer"
    assert "SDK worker output" not in asked.stdout
    recorded = claude_calls(claude_log)
    assert len(recorded) == 1
    opts = recorded[0]["options"]
    assert opts["model"] == "claude-haiku-5-5"
    assert opts["permission_mode"] == "plan"
    assert opts["setting_sources"] == []
    assert opts["disallowed_tools"] == ["Bash", "Edit", "Write", "NotebookEdit"]
    assert opts["strict_mcp_config"] is True
    assert opts["mcp_servers"] == {}
    assert any("Claude final answer" in text for text in _ask_logs(repo))

    agy_log = _install_agy_with_autoreview(repo, monkeypatch)
    monkeypatch.setenv("STUB_AGY_REVIEW", "Gemini final answer")
    asked = repo.forge("ask", "Explain this module", "--model", "gemini-4-neon")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert "Gemini final answer" in asked.stdout
    agy_prompts = lambda: sum(  # noqa: E731
        1 for line in agy_log.read_text("utf-8").splitlines()
        if json.loads(line).get("method") == "session/prompt")
    assert agy_prompts() == 1
    assert any("Gemini final answer" in text for text in _ask_logs(repo))

    if os.name != "nt":
        machine_cores(repo, 2)  # one agent place
        _wait_in_line(repo, "claude-haiku-5-5", "Claude final answer", lambda: len(claude_calls(claude_log)))
        _wait_in_line(repo, "gemini-4-neon", "Gemini final answer", agy_prompts)


@pytest.mark.platform
def test_4_model_flag_and_config_precedence_and_worktree_routing(repo, monkeypatch, sdk_data):
    _, stub = _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    install_claude(repo, worker=True)
    claude_log = repo.bin / "claude-calls.jsonl"
    agy_log = _install_agy_with_autoreview(repo, monkeypatch)
    version = repo.forge("--version").stdout.split()[-1]

    # Single [models.ask] Claude entry is used by bare forge ask.
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
               '\n[models.ask]\nmodel = "claude-haiku-5-5"\neffort = "high"\n')
    asked = repo.forge("ask", "Check config")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    recorded = claude_calls(claude_log)
    assert len(recorded) == 1
    assert (recorded[0]["options"]["model"], recorded[0]["options"]["effort"]) == ("claude-haiku-5-5", "high")

    # --model gpt-... overrides [models.ask] and does not send the Claude effort to Codex.
    asked = repo.forge("ask", "Check override", "--model", "gpt-6.2-astra")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    codex_cfg = _sent(stub, "thread/start")[-1]["config"]
    assert codex_cfg["model"] == "gpt-6.2-astra"
    assert "model_reasoning_effort" not in codex_cfg

    # Per-family [models.ask.<family>] uses the selected family's model and effort on bare asks and --model.
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
               '\n[models.ask.codex]\nmodel = "gpt-6.2-sol"\neffort = "medium"\n'
               '\n[models.ask.claude]\nmodel = "claude-sonnet-5-5"\neffort = "high"\n'
               '\n[models.ask.antigravity]\nmodel = "gemini-4-neon"\neffort = "medium"\n')
    # Bare ask from Codex session picks [models.ask.claude]'s configured model and effort.
    asked = repo.forge("ask", "Bare from codex")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    recorded = claude_calls(claude_log)
    assert (recorded[-1]["options"]["model"], recorded[-1]["options"]["effort"]) == ("claude-sonnet-5-5", "high")
    # Bare ask from Claude session picks [models.ask.codex]'s configured model and effort.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    asked = repo.forge("ask", "Bare from claude")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    codex_cfg = _sent(stub, "thread/start")[-1]["config"]
    assert (codex_cfg["model"], codex_cfg["model_reasoning_effort"]) == ("gpt-6.2-sol", "medium")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "codex-session")
    # Explicit --model gemini-... picks [models.ask.antigravity]'s configured effort.
    asked = repo.forge("ask", "Check agy effort", "--model", "gemini-4-neon")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    agy_entries = [json.loads(line) for line in agy_log.read_text("utf-8").splitlines()]
    assert any(entry.get("method") == "session/set_config_option"
               and entry["params"] == {"sessionId": entry["params"]["sessionId"],
                                       "configId": "thought_level", "value": "medium"}
               for entry in agy_entries)

    # A worktree with an older forge.toml follows main's [models.ask].
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n')
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Reset forge.toml")
    repo.git("push", "-q", "origin", "main")
    worktree = repo.path.parent / "ask-wt"
    repo.git("worktree", "add", "-q", "-b", "fix/old-config", str(worktree))
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
               '\n[models.ask]\nmodel = "claude-haiku-5-5"\neffort = "low"\n')
    repo.git("add", "forge.toml")
    repo.git("commit", "-qm", "Set Claude ask on main")
    repo.git("push", "-q", "origin", "main")
    before = len(claude_calls(claude_log))
    asked = repo.forge("ask", "From worktree", cwd=worktree)
    assert asked.returncode == 0, asked.stdout + asked.stderr
    after = claude_calls(claude_log)
    assert len(after) == before + 1
    assert after[-1]["options"]["model"] == "claude-haiku-5-5"


@pytest.mark.platform
def test_5_default_family_asks_other_session_family(repo, monkeypatch, sdk_data):
    _, stub = _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    install_claude(repo, worker=True)
    claude_log = repo.bin / "claude-calls.jsonl"
    version = repo.forge("--version").stdout.split()[-1]

    # Codex session (default in tests) asks Claude.
    asked = repo.forge("ask", "From codex")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert len(claude_calls(claude_log)) == 1
    assert len(_sent(stub, "turn/start")) == 0

    # Codex session with tools = "codex" and reviews = "codex" still asks Claude.
    repo.write("forge.toml", f'version = "{version}"\nrepo = "forge-source"\n'
               'tools = "codex"\nreviews = "codex"\n')
    asked = repo.forge("ask", "Still claude")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert len(claude_calls(claude_log)) == 2

    # Claude Code session asks Codex.
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    asked = repo.forge("ask", "From claude")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert len(_sent(stub, "turn/start")) == 1

    # Plain terminal (neither session variable) asks Codex.
    monkeypatch.delenv("CLAUDECODE", raising=False)
    asked = repo.forge("ask", "From terminal")
    assert asked.returncode == 0, asked.stdout + asked.stderr
    assert len(_sent(stub, "turn/start")) == 2


@pytest.mark.platform
def test_6_read_only_and_failures_across_families(repo, monkeypatch, sdk_data):
    _, stub = _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    install_claude(repo, worker=True)
    claude_log = repo.bin / "claude-calls.jsonl"
    _install_agy_with_autoreview(repo, monkeypatch)

    tracked = repo.path / "README.md"
    tracked.write_text("edited tracked\n", encoding="utf-8")
    untracked = repo.path / "scratch.txt"
    untracked.write_text("untracked\n", encoding="utf-8")
    before_status = repo.git("status", "--porcelain")

    # Stubs attempt writes whenever read-only isolation is missing: Claude via hooks/MCP/tools
    # (STUB_CLAUDE_UNSAFE_TOUCH) and Gemini in its checkout (STUB_AGY_DIRTY).
    monkeypatch.setenv("STUB_CLAUDE_UNSAFE_TOUCH", str(tracked))
    monkeypatch.setenv("STUB_AGY_DIRTY", "1")
    for model in ("gpt-6.2-sol", "claude-haiku-5-5", "gemini-4-neon"):
        asked = repo.forge("ask", "Inspect only", "--model", model)
        assert asked.returncode == 0, asked.stdout + asked.stderr
        assert tracked.read_bytes() == b"edited tracked\n"
        assert untracked.read_bytes() == b"untracked\n"
        assert repo.git("status", "--porcelain") == before_status
    monkeypatch.delenv("STUB_CLAUDE_UNSAFE_TOUCH")
    monkeypatch.delenv("STUB_AGY_DIRTY")
    assert _sent(stub, "thread/start")[-1]["sandbox"] == "read-only"
    assert _sent(stub, "turn/start")[-1]["sandboxPolicy"]["type"] == "readOnly"
    claude_opts = claude_calls(claude_log)[-1]["options"]
    assert claude_opts["permission_mode"] == "plan"
    assert claude_opts["setting_sources"] == []
    assert claude_opts["strict_mcp_config"] is True
    assert claude_opts["mcp_servers"] == {}
    assert {"Bash", "Edit", "Write"}.issubset(set(claude_opts["disallowed_tools"]))

    secret_q = "Check `uname` and $(whoami)"

    # Codex failure keeps the reason, preserves --model, and never echoes shell expressions.
    monkeypatch.setenv("STUB_CODEX_STATUS", "failed")
    failed_codex = repo.forge("ask", secret_q, "--model", "gpt-6.2-sol")
    assert failed_codex.returncode == 1
    assert failed_codex.stderr.startswith("Codex ended the turn: failed")
    assert "Next: run forge ask again with the same question and --model gpt-6.2-sol\n" in failed_codex.stderr
    assert secret_q not in failed_codex.stderr
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    failed_codex_bare = repo.forge("ask", secret_q)
    assert failed_codex_bare.returncode == 1
    assert "Next: run forge ask again with the same question\n" in failed_codex_bare.stderr
    assert "--model" not in failed_codex_bare.stderr
    assert secret_q not in failed_codex_bare.stderr
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "codex-session")
    monkeypatch.delenv("STUB_CODEX_STATUS")

    monkeypatch.setenv("STUB_CLAUDE_EXIT", "1")
    failed = repo.forge("ask", secret_q, "--model", "claude-haiku-5-5")
    assert failed.returncode == 1
    assert "stub claude: the model gave up" in failed.stderr
    assert "Next: run forge ask again with the same question and --model claude-haiku-5-5\n" in failed.stderr
    assert secret_q not in failed.stderr

    failed_bare = repo.forge("ask", secret_q)
    assert failed_bare.returncode == 1
    assert "Next: run forge ask again with the same question\n" in failed_bare.stderr
    assert "--model" not in failed_bare.stderr
    assert secret_q not in failed_bare.stderr
    monkeypatch.delenv("STUB_CLAUDE_EXIT")

    monkeypatch.setenv("STUB_AGY_BROKEN", "1")
    failed_agy = repo.forge("ask", secret_q, "--model", "gemini-4-neon")
    assert failed_agy.returncode == 1
    assert "Unrecognized test failure" in failed_agy.stderr
    assert "Next: run forge ask again with the same question and --model gemini-4-neon\n" in failed_agy.stderr
    assert secret_q not in failed_agy.stderr
    monkeypatch.delenv("STUB_AGY_BROKEN")
