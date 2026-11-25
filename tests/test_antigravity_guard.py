"""The Antigravity worker uses Forge's lane and guard through the command boundary."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from conftest import machine_cores
from test_antigravity_build import setup
from test_fix_agent_runs_wait_in_line import _until
from test_lanes_agents import alive, finish, start
from test_worker import calls

STORY = "FORGE-ANTIGRAVITY-1"
pytestmark = pytest.mark.platform


def test_4_antigravity_runs_share_lanes_stop_and_always_run_with_the_guard(
    repo, gh, tmp_path, monkeypatch,
):
    log = setup(repo, gh, monkeypatch, local=True)
    machine_cores(repo, 2)
    monkeypatch.setenv("XDG_DATA_HOME", ".cache")
    monkeypatch.setenv("STUB_AGY_HOLD", "1")
    first, first_output = start(repo.path, tmp_path / "first", repo, "work", "BOARD/HELP")
    processes = [first]
    try:
        _until(lambda: first.poll() is not None or
               any(entry.get("method") == "session/prompt" for entry in calls(log)), "first prompt")
        assert first.poll() is None, first_output.read_text(encoding="utf-8")
        launch = calls(log)[0]
        profile = Path(launch["argv"][2])
        assert profile.is_absolute()
        assert not profile.is_relative_to(repo.path.resolve())
        monkeypatch.delenv("STUB_AGY_HOLD")
        second, output = start(repo.path, tmp_path / "second", repo, "work", "BOARD/API")
        processes.append(second)
        _until(lambda: second.poll() is not None or
               "number 1 in line" in output.read_text(encoding="utf-8"), "second worker waiting")
        assert second.poll() is None, output.read_text(encoding="utf-8")
        assert len([entry for entry in calls(log) if "argv" in entry]) == 1
        stopped = repo.forge("stop", "BOARD/HELP")
        assert stopped.returncode == 0, stopped.stdout + stopped.stderr
        assert "Stopped the run." in stopped.stdout
        first.wait(timeout=30)
        assert not alive(launch["pid"])
        assert second.wait(timeout=30) == 0, output.read_text(encoding="utf-8")
        assert len([entry for entry in calls(log) if "argv" in entry]) == 2
        launches = [entry for entry in calls(log) if "argv" in entry]
        assert all(Path(entry["argv"][2]).is_absolute() for entry in launches)
        assert any(entry.get("guard") == {"decision": "allow"} for entry in calls(log))
    finally:
        if first.poll() is None:
            repo.forge("stop", "BOARD/HELP")
        finish(repo, processes)

    cwd = Path(launch["cwd"])
    hooks = json.loads((profile / "config/hooks.json").read_text(encoding="utf-8"))
    commands = {entry["matcher"]: entry["hooks"][0]["command"]
                for entry in hooks["forge"]["PreToolUse"]}
    command = commands["run_command"]
    assert Path(command.split(" -I ", 1)[0].strip("\"'")).is_absolute()
    guard = Path(command.split(" -S ", 1)[1].strip("\"'"))
    assert guard.is_absolute() and guard.is_file()
    assert guard.is_relative_to(Path.home().resolve())
    assert not guard.is_relative_to(cwd.resolve())
    marker = cwd / "fake-ran"
    imports = cwd / "fake-imports"
    package = imports / "forge"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from pathlib import Path\nPath('fake-ran').touch()\n", encoding="utf-8",
    )
    for name in ("forge", "forge.cmd", "git", "git.cmd", "argparse.py"):
        fake = cwd / name
        source = (
            "from pathlib import Path\nPath('fake-ran').touch()\n" if name.endswith(".py")
            else "@echo ran>fake-ran\n" if name.endswith(".cmd")
            else "#!/bin/sh\ntouch fake-ran\n"
        )
        fake.write_text(source, encoding="utf-8")
        fake.chmod(0o755)
    env = {**os.environ, "PATH": str(cwd) + os.pathsep + os.environ["PATH"], "PYTHONPATH": str(imports)}
    for name, args, decision in [
        ("run_command", {"CommandLine": "git push --force origin main"}, "deny"),
        ("run_command", {"CommandLine": "git status"}, "allow"),
        ("run_command", {}, "deny"),
        ("manage_task", {"Action": "send_input", "Input": "git reset --hard\n"}, "deny"),
        ("manage_task", {"Action": "status"}, "allow"),
    ]:
        assert name in commands, f"Forge does not register a guard for {name}."
        payload = {"toolCall": {"name": name, "args": args}}
        result = subprocess.run(commands[name], shell=True, cwd=cwd, env=env,
                                input=json.dumps(payload), text=True, capture_output=True, check=True)
        answer = json.loads(result.stdout)
        assert answer["decision"] == decision
        if not args:
            assert answer["reason"] == "Forge cannot read this command, so it does not run."
        assert not marker.exists()
