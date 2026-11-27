"""Upgrade ends CI-only closes before install, while reviews still protect it.

The old live-close test required refusal during CI. This replacement exercises
continuation through real commands, with only external services faked. The
installer models Windows refusing an environment still in use. No production
seam is needed.
"""
import sys

import pytest

import conftest
from conftest import _install
from test_close import env, run  # noqa: F401
from test_fix_agent_runs_wait_in_line import _until
from test_lanes_agents import finish, hold_agents, start
from test_upgrade_command import MARK, RELEASE, UV, unsynced_up, up  # noqa: F401

STORY = "upgrade-ignores-ci-waits"
pytestmark = pytest.mark.platform


def test_1_upgrade_allows_ci_wait_and_keeps_review_protected(up, tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_CHECKS_WAIT", "600")
    monkeypatch.setenv("FORGE_CHECKS_POLL", "0.1")
    hold_agents(up.env)
    up.env.checks([run("tests", None, "in_progress"), run("forge-pr-check")])
    item, checkout = up.env.start_fix()
    # A launcher above close, like a virtual environment's python.exe on Windows, starts it, waits
    # for it and keeps the tool environment a moment after it ends.
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text("import subprocess, sys, time\n"
                       "code = subprocess.call([sys.executable, *sys.argv[1:]])\n"
                       "time.sleep(2)\n"
                       "sys.exit(code)\n", "utf-8")
    closing, output = start(checkout, tmp_path / "close", up.repo, "close", item, via=wrapper)
    processes = [closing]
    # Model the real installer's environment-in-use refusal on every platform.
    installer = UV.format(python=sys.executable, mark=MARK,
                          root=str(conftest.ROOT), idle_machine=conftest.IDLE_MACHINE)
    installer = installer.replace('    put(here.parent / "uvbin" / "forge",',
        f'    pid = {closing.pid}\n'
        '    if os.name == "nt":  # os.kill(pid, 0) sends Ctrl+C there; it is no check\n'
        '        import ctypes\n'
        '        code, kernel = ctypes.c_ulong(), ctypes.windll.kernel32\n'
        '        handle = kernel.OpenProcess(0x1000, False, pid)\n'
        '        live = bool(handle) and kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259\n'
        '    else:\n'
        '        try:\n'
        '            os.kill(pid, 0)\n'
        '            live = not subprocess.run(\n'
        '                ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip().startswith("Z")\n'
        '        except OSError:\n'
        '            live = False\n'
        '    if live: sys.exit("tool environment is still in use by close")\n'
        '    put(here.parent / "uvbin" / "forge",')
    _install(up.repo.bin, "uv", installer)

    try:
        _until(lambda: closing.poll() is not None or (up.repo.bin / "started-review").exists(), "the review")
        assert closing.poll() is None, output.read_text("utf-8")
        refused = up.run(RELEASE)
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert "Forge runs are still in progress" in refused.stderr
        assert "(review)" in refused.stderr
        assert up.uv() == []

        (up.repo.bin / "go-all").touch()
        _until(lambda: closing.poll() is not None or "Waiting:" in output.read_text("utf-8"), "the close check wait")
        assert closing.poll() is None, output.read_text("utf-8")
        upgrading, upgrade_output = start(up.repo.path, tmp_path / "upgrade", up.repo, "upgrade", RELEASE)
        processes.append(upgrading)
        installed = f"Installed Forge {RELEASE}."
        _until(lambda: upgrading.poll() is not None or installed in upgrade_output.read_text("utf-8"),
               "completed installation while CI stays pending")
        assert upgrading.poll() is None, upgrade_output.read_text("utf-8")
        assert installed in upgrade_output.read_text("utf-8")
        assert closing.wait(timeout=30) != 0, output.read_text("utf-8")
        assert (f"Ended close for {item} to install Forge. Run forge close {item} to resume the CI wait."
                in upgrade_output.read_text("utf-8"))
        resumed, resumed_output = start(checkout, tmp_path / "resumed", up.repo, "close", item,
                                        launcher=tmp_path / "uvbin" / "forge")
        processes.append(resumed)
        _until(lambda: resumed.poll() is not None or "Waiting:" in resumed_output.read_text("utf-8"),
               "the resumed close check wait")
        assert resumed.poll() is None, resumed_output.read_text("utf-8")
        up.env.checks([run("tests"), run("forge-pr-check")])
        assert upgrading.wait(timeout=90) == 0, upgrade_output.read_text("utf-8")
        assert resumed.wait(timeout=90) == 0, resumed_output.read_text("utf-8")
        assert "Ready:" in resumed_output.read_text("utf-8")
    finally:
        up.env.checks([run("tests"), run("forge-pr-check")])
        finish(up.repo, processes)
