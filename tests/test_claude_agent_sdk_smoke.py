"""Run Forge's worker command with the pinned Claude Agent SDK and a fake CLI.

Test audit:
1. Protects the real SDK query, options, and streamed event contract used by a worker.
2. A changed SDK API or event shape could break turns while the stub-based worker tests pass.
3. Existing command tests replace the whole SDK package; this command test replaces only its CLI.
4. It uses `forge work`; no production test seam is needed.

The smoke workflow installs the SDK from the package index. The test runs there only and makes no
Anthropic request. It copies the SDK environment with hard links before hiding the copied CLI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

import pytest
from conftest import patient


STORY = "codex-0-169-0-and-later-add-environmenti"
PIN = "0.2.187"
READY = "forge-sdk-ready"
DATA = Path(os.environ.get("XDG_DATA_HOME") or os.environ.get("LOCALAPPDATA")
            or Path.home() / ".local" / "share")
SOURCE_ENV = DATA / "forge" / "claude-sdk" / f"claude-agent-sdk-{PIN}"
SOURCE_PYTHON = SOURCE_ENV / "bin" / "python"

pytestmark = pytest.mark.platform


FAKE_CLAUDE = r'''import json, os, sys

log = os.environ["CLAUDE_SDK_SMOKE_LOG"]
def record(value):
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps(value) + "\n")

record({"argv": sys.argv[1:], "sdk": os.environ.get("CLAUDE_AGENT_SDK_VERSION")})
session = "fake-claude-session"
for line in sys.stdin:
    message = json.loads(line)
    record({"input": message})
    if message.get("type") == "control_request":
        print(json.dumps({"type": "control_response", "response": {
            "subtype": "success", "request_id": message["request_id"], "response": {}}}),
            flush=True)
    elif message.get("type") == "user":
        print(json.dumps({"type": "assistant", "session_id": session,
            "message": {"model": "claude-sonnet-smoke", "content": [
                {"type": "text", "text": "pinned Claude SDK smoke turn"}]}}), flush=True)
        print(json.dumps({"type": "result", "subtype": "success", "duration_ms": 1,
            "duration_api_ms": 0, "is_error": False, "num_turns": 1,
            "session_id": session, "result": "pinned Claude SDK smoke turn",
            "usage": {"input_tokens": 1, "output_tokens": 1}}), flush=True)
        break
'''


@pytest.mark.skipif(
    os.environ.get("FORGE_LIVE_CODEX") != "1",
    reason="the codex-smoke workflow installs the real SDK for this no-network worker turn",
)
@pytest.mark.skipif(os.name == "nt", reason="the real-SDK smoke workflow runs on Ubuntu")
def test_3_claude_worker_turn_uses_the_pinned_sdk(repo, monkeypatch, tmp_path):
    assert (SOURCE_ENV / READY).is_file(), f"the smoke workflow did not install Claude Agent SDK {PIN}"
    assert SOURCE_PYTHON.is_file(), f"the smoke workflow did not install Python for Claude Agent SDK {PIN}"

    version = repo.forge("--version").stdout.split()[-1]
    repo.write("forge.toml", f'version = "{version}"\nrepo = "client"\n'
               'tools = "both"\nworkers = "claude"\ntest = "git status --porcelain"\n'
               '[models.fix.claude]\nmodel = "sonnet"\neffort = "low"\n')
    repo.git("add", "forge.toml")
    repo.git("commit", "--allow-empty", "-qm", "Configure Claude worker")
    repo.git("push", "-q", "origin", "main")
    started = repo.forge("fix", "start", "Run the Claude SDK smoke test", "--done",
                         "A Claude worker turn completes with the pinned SDK")
    assert started.returncode == 0, started.stdout + started.stderr

    data = Path(os.environ["XDG_DATA_HOME"])
    sdk_env = data / "forge" / "claude-sdk" / f"claude-agent-sdk-{PIN}"
    patient(lambda: shutil.rmtree(sdk_env))
    patient(lambda: shutil.copytree(SOURCE_ENV, sdk_env, symlinks=True, copy_function=os.link))
    bundled = next(sdk_env.glob("lib/python*/site-packages/claude_agent_sdk/_bundled/claude"))
    hidden = bundled.with_name("claude.forge-smoke-hidden")
    bundled.rename(hidden)

    log = tmp_path / "claude-sdk-smoke.jsonl"
    fake = repo.bin / "claude"
    fake.write_text(f"#!{sys.executable}\n{FAKE_CLAUDE}", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("CLAUDE_SDK_SMOKE_LOG", str(log))
    monkeypatch.delenv("PYTHONPATH", raising=False)
    try:
        worked = repo.forge("work", "run-the-claude-sdk-smoke-test")
    finally:
        hidden.rename(bundled)

    assert worked.returncode == 0, worked.stdout + worked.stderr
    assert "pinned Claude SDK smoke turn" in worked.stdout
    records = [json.loads(line) for line in log.read_text("utf-8").splitlines()]
    assert records[0]["sdk"] == PIN, records
    assert any(record.get("input", {}).get("request", {}).get("subtype") == "initialize"
               for record in records), records
    assert any(record.get("input", {}).get("type") == "user"
               and "# Worker brief" in str(record["input"].get("message"))
               for record in records), records
