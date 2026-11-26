"""The Bash hook gives the coordinator a structured, rate-limited handoff cue."""
import json

STORY = "FORGE-CHATHANDOVER-1"


def test_1_context_line_past_half_window(repo, tmp_path, monkeypatch):
    transcript = tmp_path / "transcript.jsonl"
    worktree = tmp_path / "task"
    repo.git("worktree", "add", "-b", "task/CHAT-1-HANDOVER", str(worktree))
    monkeypatch.delenv("FORGE_WORKER", raising=False)

    def record(event):
        transcript.write_text(json.dumps(event) + "\n", encoding="utf-8")

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

    def claude(output):
        record({"type": "assistant", "message": {"usage": {
            "input_tokens": 100_000, "cache_read_input_tokens": 200_000,
            "cache_creation_input_tokens": 100_000, "output_tokens": output,
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
