"""Check Forge's Codex request and the pinned SDK's first model call."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from conftest import REAL_CODEX_HOME
from test_close import env  # noqa: F401
from test_codex_resume import _resuming
from test_codex_smoke import CONFIG, ENV, ROOT, _drive, _one
from test_codex_worker import _sent, sdk_data  # noqa: F401

STORY = "FORGE-TOKENS-1"
HOST_CONTEXT = {"memories.use_memories": False, "skills.bundled.enabled": False}


@pytest.mark.parametrize("live", [
    pytest.param(False, id="request"),
    pytest.param(True, id="live", marks=[
        pytest.mark.platform,
        pytest.mark.skipif(os.environ.get("FORGE_LIVE_CODEX") != "1",
                           reason="calls the real model only in codex-smoke"),
    ]),
])
def test_3_codex_skips_host_context(live, request, tmp_path, monkeypatch):
    if not live:
        repo = request.getfixturevalue("env").repo
        sdk = request.getfixturevalue("sdk_data")
        _, calls, _ = _resuming(repo, monkeypatch, sdk)
        done = repo.forge("work", "BOARD/PAGE")
        assert done.returncode == 0, done.stdout + done.stderr
        config = _sent(calls, "thread/start")[-1]["config"]
        assert {key: config.get(key) for key in HOST_CONTEXT} == HOST_CONTEXT
        return

    assert (ENV / "forge-sdk-ready").is_file(), f"Pinned Codex SDK missing in {ENV}"
    home = request.getfixturevalue("isolated_codex_home")
    shutil.copyfile(REAL_CODEX_HOME / "auth.json", home / "auth.json")
    (home / "auth.json").chmod(0o600)
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    (home / "config.toml").write_text(
        '[features]\nmemories = true\n[memories]\nversion = "v1"\ngenerate_memories = false\n'
        f'[projects.{json.dumps(str(project))}]\ntrust_level = "trusted"\n', encoding="utf-8")
    (home / "memories").mkdir()
    (home / "memories/memory_summary.md").write_text(
        "An unrelated preference for synthetic experiments: use violet labels.\n" * 50,
        encoding="utf-8")

    # Put a unique receipt in the shipped skill's description so the model can
    # identify it only when the project skill catalog is visible.
    receipt = f"forge-{uuid.uuid4().hex[:12]}"
    skill_path = Path(".codex/skills/test-audit/SKILL.md")
    skill = (ROOT / skill_path).read_text(encoding="utf-8")
    head, description, tail = skill.partition("description: \"")
    assert description
    target = project / skill_path
    target.parent.mkdir(parents=True)
    (project / ".codex/config.toml").touch()
    target.write_text(f'{head}{description}Receipt {receipt}. {tail}', encoding="utf-8")
    prompt = ("From the available skills list already in your context, return only the receipt in "
              "the description of the test-audit skill. Do not use tools or open any files.")

    first_input = {}
    for label, override in [("baseline", {}), *(
            (key, {key: value}) for key, value in HOST_CONTEXT.items())]:
        lines = _drive(project, "Forge host context smoke", prompt, config={**CONFIG, **override})
        end = _one(lines, "status")
        assert end["status"] == "completed", end
        first = next(line["params"]["tokenUsage"]["last"]["inputTokens"]
                     for line in lines if line.get("event") == "thread/tokenUsage/updated")
        first_input[label] = first
        print(f"{label}: first model call used {first} input tokens")
        assert end["text"].strip() == receipt, end
        items = [line["params"]["item"]["type"] for line in lines
                 if line.get("event") == "item/completed"]
        assert set(items) <= {"userMessage", "agentMessage", "reasoning"}, items
    assert all(0 < first_input[key] < first_input["baseline"] for key in HOST_CONTEXT), first_input
