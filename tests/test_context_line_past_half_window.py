"""The Bash hook gives the coordinator a structured, rate-limited handoff cue."""
import json

import pytest

STORY = "FORGE-CHATHANDOVER-1"


@pytest.mark.platform
def test_1_context_line_past_half_window(repo, tmp_path, monkeypatch):
    transcript = tmp_path / "transcript.jsonl"
    worktree = tmp_path / "task"
    repo.git("worktree", "add", "-b", "task/CHAT-1-HANDOVER", str(worktree))
    monkeypatch.delenv("FORGE_WORKER", raising=False)

    def record(event):
        with transcript.open("a", encoding="utf-8") as log:
            log.write(json.dumps(event) + "\n")

    def hook(session, expected=None, *, cwd=None, **fields):
        result = repo.forge("hook", "deny", cwd=cwd, input=json.dumps({
            "hook_event_name": "PreToolUse", "tool_input": {"command": "pwd"},
            "session_id": session, "transcript_path": str(transcript), **fields,
        }))
        assert result.returncode == 0, result.stderr
        if expected is None:
            assert not result.stdout
        else:
            output = json.loads(result.stdout)["hookSpecificOutput"]
            assert output["hookEventName"] == "PreToolUse"
            assert output["additionalContext"] == (
                f"This chat uses {expected} tokens. Hand over at the next quiet moment: "
                "see Handoff in the Forge guide."
            )

    def claude(output, *, model="claude-haiku-5-5", input_tokens=100_000, cache=200_000,
               creation=100_000):
        record({"type": "assistant", "message": {"model": model, "usage": {
            "input_tokens": input_tokens, "cache_read_input_tokens": cache,
            "cache_creation_input_tokens": creation, "output_tokens": output,
        }}})

    claude(0)
    hook("claude")
    claude(100_000)
    hook("claude")
    claude(200_000)
    hook("claude", "600K of 1M")
    hook("claude", cwd=worktree)
    hook("other", "600K of 1M", cwd=worktree)
    hook("subagent", agent_id="helper")
    hook("null", transcript_path=None)
    hook("missing", transcript_path=str(tmp_path / "missing.jsonl"))
    with monkeypatch.context() as env:
        env.setenv("FORGE_WORKER", "1")
        hook("worker")
    claude(300_000)
    hook("claude", "700K of 1M")
    hook("claude-small-window", "700K of 800K", context_window=800_000)
    claude(110_001)
    hook("just-over-half", "510,001 of 1M")

    for model in ("claude-haiku-4-5-20251001", "claude-opus-4-5-20251101", "claude-sonnet-4-5"):
        claude(20_000, model=model, cache=0, creation=0)
        hook(model, "120K of 200K")

    transcript = tmp_path / "rollout.jsonl"

    def codex(latest):
        record({"type": "event_msg", "payload": {"type": "token_count", "info": {
            "model_context_window": 500_000,
            "last_token_usage": {"total_tokens": latest},
            "total_token_usage": {"total_tokens": 900_000},
        }}})

    codex(150_000)
    hook("codex")
    codex(300_000)
    hook("codex", "300K of 500K")
    codex(450_000)
    hook("codex", "450K of 500K")

    def session_start(source):
        result = repo.forge("hook", "context", cwd=worktree, input=json.dumps({
            "hook_event_name": "SessionStart", "session_id": "codex", "source": source,
            "transcript_path": str(transcript),
        }))
        assert result.returncode == 0, result.stderr

    session_start("resume")
    hook("codex")
    session_start("compact")
    codex(150_000)
    hook("codex")
    codex(260_000)
    hook("codex", "260K of 500K")
    hook("codex")
