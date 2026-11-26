"""FORGE-CODEXAPPROVE-1: typed approval through the Codex prompt hook."""
from __future__ import annotations

import re

from test_story import DOC, hook, ready, setup

STORY = "FORGE-CODEXAPPROVE-1"


# Captured from Codex 0.172.0 when spawn_agent started its child with an initial prompt.
# Each test replaces the checkout path and prompt with its own.
HELPER = {
    "session_id": "01a217fb-2c1d-73f0-940e-9d4bb254334e",
    "turn_id": "01a217fb-2c56-78d3-9764-3d6facc67578",
    "agent_id": "01a217fb-2c54-7333-b369-52a057ca6c48",
    "agent_type": "default",
    "transcript_path": None,
    "hook_event_name": "UserPromptSubmit",
    "model": "gpt-5.4",
    "permission_mode": "bypassPermissions",
}


def test_1_2_typed_approval_checks_the_story_sender_and_turn(repo, monkeypatch):
    setup(repo, keys=("SHOP", "WISH"))
    ready(repo, "SHOP")
    ready(repo, "WISH", DOC.replace("save a basket", "keep a wish list"))
    config = repo.path / "forge.toml"
    config.write_text('tools = "codex"\n' + config.read_text(encoding="utf-8"), encoding="utf-8")
    shown = repo.forge("next").stdout
    codes = dict(re.findall(r"show plans/(\w+)\.md[^\n]+approve_plan_([0-9a-f]{6})", shown))
    shop, wish = codes["SHOP"], codes["WISH"]
    assert f"then ask the owner to type approve SHOP {shop}." in shown
    payload = {"cwd": repo.path.as_posix(), "hook_event_name": "UserPromptSubmit",
               "session_id": "owner-session", "turn_id": "owner-turn"}

    def send(prompt, **fields):
        result = hook(repo, {**payload, "prompt": prompt, **fields})
        assert result.returncode == 0, result.stderr
        return result.stdout

    heads = [repo.git("rev-parse", f"story/{key}") for key in ("SHOP", "WISH")]
    no_match = "The approved plan matches no story doc waiting for approval"
    assert no_match in send(f"approve SHOP {wish}")
    assert no_match in send(f"approve UNKNOWN-1 {shop}")
    for code in (shop[:5], "xyzxyz", shop + "0", shop + " please"):
        assert "approve <KEY> <6-character code>" in send(f"approve SHOP {code}")
    assert send("approve the plan please") == ""
    assert send("ordinary prompt") == ""
    line = f"  ApPrOvE shop {shop.upper()}  "
    for event in ("PreToolUse", "PostToolUse"):
        assert send(line, hook_event_name=event) == ""
    assert "Only the owner can type" in send(line, **HELPER)
    with monkeypatch.context() as worker:
        worker.setenv("FORGE_WORKER", "1")
        assert send(line) == ""
    for name in ("session_id", "turn_id"):
        assert "no session or event id" in send(line, **{name: None})
    assert [repo.git("rev-parse", f"story/{key}") for key in ("SHOP", "WISH")] == heads

    assert "Recorded the approval of" in send(line)
    assert "Next: forge task start SHOP/SAVE" in repo.forge("next").stdout
    committed = repo.git("rev-parse", "story/SHOP")
    assert committed != heads[0]
    assert "a replay records nothing" in send(line)
    assert "a replay records nothing" in send(f"approve WISH {wish}")
    assert no_match in send(line, turn_id="new-turn")
    assert repo.git("rev-parse", "story/SHOP") == committed
    assert repo.git("rev-parse", "story/WISH") == heads[1]
