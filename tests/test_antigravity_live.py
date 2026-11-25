"""Check the real Antigravity ACP server without loading Forge."""

import json
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Timer

import pytest

LIVE_AGY = os.environ.get("FORGE_LIVE_AGY")
STORY = "FORGE-ANTIGRAVITY-LIVE"


@contextmanager
def _acp(agy, workspace, profile, *flags):
    with subprocess.Popen(
        [agy, "acp", "--gemini-dir", str(profile), *flags],
        cwd=workspace, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True, encoding="utf-8",
    ) as process:
        deadline = Timer(120, process.kill)
        deadline.start()

        def request(identifier, method, params, events=None):
            def send(message):
                process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
                process.stdin.flush()

            send({"id": identifier, "method": method, "params": params})
            for line in process.stdout:
                reply = json.loads(line)
                if events is not None and "method" in reply:
                    events.append(reply)
                if "method" in reply and "id" in reply:
                    send({"id": reply["id"], "result": {"outcome": {"outcome": "cancelled"}}})
                elif reply.get("id") == identifier:
                    assert "error" not in reply, (method, reply.get("error"))
                    return reply["result"]
            pytest.fail(f"Antigravity closed stdout during {method}.")

        try:
            yield request
        finally:
            deadline.cancel()
            process.kill()


@pytest.mark.platform
def test_1_live_acp_contract():
    """Rule: Antigravity's ACP server can start a turn in a disposable profile."""
    agy = LIVE_AGY
    if not agy:
        pytest.skip("Set FORGE_LIVE_AGY to the signed-in Antigravity CLI path.")
    with TemporaryDirectory(prefix="forge-agy-") as folder:
        _check_contract(agy, Path(folder).resolve())


def _check_contract(agy, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    profile = tmp_path / "full"
    profile.mkdir()
    hooks = profile / "config"
    hooks.mkdir()
    hook_marker = tmp_path / "guard-ran"
    command_marker = workspace / "command-ran"
    quote = subprocess.list2cmdline if os.name == "nt" else shlex.join
    hook = (
        f"from pathlib import Path; import sys; Path({str(hook_marker)!r}).write_text(sys.stdin.read()); "
        "print('{\"decision\":\"deny\",\"reason\":\"Live contract test\"}')"
    )
    (hooks / "hooks.json").write_text(json.dumps({
        "forge": {"PreToolUse": [{
            "matcher": "run_command",
            "hooks": [{"type": "command", "command": quote([sys.executable, "-I", "-c", hook]),
                       "timeout": 60}],
        }]},
    }), encoding="utf-8")
    context = {"cwd": str(workspace), "mcpServers": []}
    initialize = {"protocolVersion": 1, "clientCapabilities": {}}

    def prompt(request, identifier, text, events=None):
        return request(identifier, "session/prompt", {
            "sessionId": session["sessionId"], "prompt": [{"type": "text", "text": text}],
        }, events)

    with _acp(agy, workspace, profile, "--dangerously-skip-permissions") as request:
        init = request(1, "initialize", initialize)
        print("initialize:", json.dumps(init, sort_keys=True))
        assert init["agentCapabilities"]["sessionCapabilities"]["resume"] == {}
        session = request(2, "session/new", context)
        options = {option["id"]: option for option in session["configOptions"]}
        print("configOptions:", json.dumps(options, sort_keys=True))
        assert "gemini-4-neon" in {option["value"] for option in options["model"]["options"]}
        assert {"low", "medium", "high", "xhigh"} <= {
            option["value"] for option in options["thought_level"]["options"]
        }
        for identifier, (key, value) in enumerate(
            [("model", "gemini-4-neon"), ("thought_level", "low")], 10,
        ):
            changed = request(identifier, "session/set_config_option", {
                "sessionId": session["sessionId"], "configId": key, "value": value,
            })
            assert any(option["id"] == key and option["currentValue"] == value
                       for option in changed["configOptions"])
        result = prompt(request, 3, "Reply with the word Ready. Use no tools.")
        print("prompt:", json.dumps(result, sort_keys=True))
        assert result["stopReason"] == "end_turn"
        run_command = quote([sys.executable, "-I", "-c",
                             f"from pathlib import Path; Path({str(command_marker)!r}).touch()"])
        prompt(request, 4, f"Use run_command to execute this command once: {run_command}\n"
               "If denied, stop. Do not use any other tools.")
        assert hook_marker.is_file(), "The full profile's PreToolUse hook did not run."
        tool = json.loads(hook_marker.read_text(encoding="utf-8"))["toolCall"]
        assert tool["name"] == "run_command" and tool["args"]["CommandLine"] == run_command
        assert not command_marker.exists(), "The hook's deny decision did not stop the command."

    with _acp(agy, workspace, profile) as request:
        request(1, "initialize", initialize)
        resumed = request(2, "session/resume", {**context, "sessionId": session["sessionId"]})
        print("resume config:", [option["id"] for option in resumed.get("configOptions", [])])
        assert prompt(request, 3, "Reply with Ready. Use no tools.")["stopReason"] == "end_turn"

    profile = tmp_path / "read"
    settings = profile / "antigravity-cli"
    settings.mkdir(parents=True)
    (settings / "settings.json").write_text(json.dumps({"toolPermission": "strict", "permissions": {
        "deny": ["write_file(*)", "command(*)", "execute_url(*)", "read_url(*)", "mcp(*)"],
        "ask": ["read_file(*)"],
    }}), encoding="utf-8")
    inside, outside = workspace / "inside.txt", tmp_path / "outside.txt"
    for path in (inside, outside):
        path.write_text("Live test data.", encoding="utf-8")
    write_marker = workspace / "write-ran.txt"
    problems = []
    with _acp(agy, workspace, profile) as request:
        request(1, "initialize", initialize)
        session = request(2, "session/new", context)
        for identifier, (text, name, path) in enumerate([
            (f"Use the file reading tool to read {inside}.", "read_file", inside),
            (f"Use the file reading tool to read {outside}.", "read_file", outside),
            (f"Use the file writing tool to create {write_marker} with the text Ready.",
             "write_file", write_marker),
            (f"Use run_command to execute this exact command: {run_command}", "run_command", None),
        ], 3):
            events = []
            prompt(request, identifier, text + "\nTry exactly once. If denied, stop.", events)
            calls = [event["params"]["toolCall"] for event in events
                     if event["method"] == "session/request_permission"]
            print(f"Read profile {name} permission requests:", [call.get("name") for call in calls])
            updates = [event["params"]["update"] for event in events
                       if event["method"] == "session/update"]
            failed = [update for update in updates if update.get("name") == name
                      and update.get("status") == "failed"
                      and "permission check failed" in update.get("rawOutput", "")]
            if name == "read_file":
                if not any(call["name"] == name and any(
                    Path(location["path"]).resolve() == path for location in call.get("locations", [])
                ) for call in calls):
                    problems.append(f"Read did not reach the client for {path.name}.")
            if not failed and not any(call.get("name") == name for call in calls):
                problems.append(f"No permission refusal was reported for {name}.")
        assert not write_marker.exists()
        assert not command_marker.exists()
    assert not problems, problems
