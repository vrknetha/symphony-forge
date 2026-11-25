"""A close owns its reviewer and the reviewer's children, even after a hard kill."""
import contextlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, _install
from test_close import env  # noqa: F401
from test_fix_agent_runs_wait_in_line import _until
from test_lanes_agents import alive

STORY = "FIX-KILLED-CLOSE-ENDS-REVIEW"
pytestmark = pytest.mark.platform


@pytest.mark.parametrize("ending", ["kill", "terminate", "interrupt", "stop", "normal"])
def test_1_close_ends_its_review_tree_and_releases_upgrade(env, ending):
    # Audit: real close and upgrade own this lifecycle contract. The third-party
    # helper alone is fake; its child and all process termination remain real.
    repo = env.repo
    item, _ = env.start_fix()
    launcher = repo.bin / "forge"
    close_pid = repo.bin / "close-pid"
    interpreter = sys.executable
    if os.name != "nt":
        # Exercise the extra launcher hop on Unix too. Windows uses the real
        # virtual-environment Python redirector, without an interpreter stub.
        redirector = repo.bin / "python-redirector"
        redirector.write_text(f"#!{sys.executable}\nimport subprocess, sys\n"
            f"sys.exit(subprocess.call([{sys.executable!r}, *sys.argv[1:]]))\n", "utf-8")
        redirector.chmod(0o755)
        interpreter = str(redirector)
    launcher.write_text(launcher.read_text("utf-8").replace("from forge.cli import main",
        "import os, pathlib\n"
        "if sys.argv[1:2] == ['close']:\n"
        f"    pathlib.Path({json.dumps(close_pid.as_posix())}).write_text(str(os.getpid()))\n"
        f"    sys.executable = {json.dumps(interpreter)}\n"
        "from forge.cli import main"), "utf-8")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(60)
    child = (
        "import json, os, socket, sys; "
        f"s = socket.create_connection({listener.getsockname()!r}); "
        "s.sendall((json.dumps([int(sys.argv[1]), os.getpid()]) + '\\n').encode()); "
        "print('ready', flush=True); s.recv(1)"
    )
    Path(os.environ["AUTOREVIEW"]).write_text(
        "import json, os, pathlib, subprocess, sys\n"
        "group = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' "
        "else {'start_new_session': True})\n"
        f"child = subprocess.Popen([sys.executable, '-c', {child!r}, str(os.getpid())], "
        "stdout=subprocess.PIPE, **group)\n"
        "child.stdout.readline()\n"
        + ("pathlib.Path(sys.argv[sys.argv.index('--json-output') + 1]).write_text(json.dumps("
           "{'findings': [], 'review_status': 'scoped-clean'}), encoding='utf-8')\n"
           if ending == "normal" else "child.wait()\n"),
        encoding="utf-8")
    close = subprocess.Popen([sys.executable, str(repo.bin / "forge"), "close", item],
        cwd=repo.path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pids = []
    connection = None
    try:
        connection, _ = listener.accept()
        connection.settimeout(20)
        pids = json.loads(connection.makefile("rb").readline())
        owner = int(close_pid.read_text("utf-8"))
        if ending != "normal":
            assert all(alive(pid) for pid in pids)
        if ending == "normal":
            pass
        elif ending == "stop":
            stopped = repo.forge("stop", item)
            assert stopped.returncode == 0, stopped.stdout + stopped.stderr
        else:
            # End the actual close interpreter, not the venv redirector that
            # waits for it. SIGTERM on Windows calls TerminateProcess.
            sig = (signal.SIGKILL if ending == "kill" and os.name != "nt" else
                   signal.SIGINT if ending == "interrupt" and os.name != "nt" else signal.SIGTERM)
            os.kill(owner, sig)
        close.wait(timeout=240 if os.name == "nt" else 30)
        if ending == "normal":
            assert close.returncode == 0
        _until(lambda: not any(alive(pid) for pid in pids), "the whole review tree to end")
        lanes = repo.forge("lanes", "--json")
        assert not any(row["kind"] == "review" for row in json.loads(lanes.stdout)["agents"]["entries"])
        # This older target reaches the upgrade run gate, then refuses only its
        # version. No installer or network access is needed to prove admission.
        upgrade = repo.forge("upgrade", "v0.0.1")
        assert "Forge runs are still in progress" not in upgrade.stdout + upgrade.stderr
        assert "would not be an upgrade" in upgrade.stdout + upgrade.stderr, upgrade.stdout + upgrade.stderr
    finally:
        if connection is not None:
            connection.close()
        listener.close()
        if close.poll() is None:
            close.kill()
        close.wait(timeout=30)
        for pid in reversed(pids):
            if alive(pid):
                if os.name == "nt":
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(pid, signal.SIGKILL)


@pytest.mark.skipif(os.name == "nt", reason="Only POSIX engines join the helper process group")
def test_2_review_engine_timeouts_still_end_the_engine(env, monkeypatch):
    # Sharing the close-owned group must preserve Autoreview's individual
    # engine timeout. Exercise the pinned helper, with only the model faked.
    repo = env.repo
    item, _ = env.start_fix()
    tool = Path(os.environ["AUTOREVIEW"])
    shutil.copyfile(ROOT / "tests/fixtures/autoreview-ce14dcca/scripts/autoreview", tool)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(60)
    # Keep the real helper alive after a timed-out engine, as a review with
    # another pass would be. Whole-close cleanup must not supply this proof.
    with tool.open("a", encoding="utf-8") as helper:
        helper.write("\noriginal = sanitized_main\n"
            "def sanitized_main():\n"
            "    import socket\n"
            "    try:\n"
            "        result = original()\n"
            "    except SystemExit as error:\n"
            "        result = error.code\n"
            f"    with socket.create_connection({listener.getsockname()!r}) as gate:\n"
            "        gate.sendall(b'finished\\n')\n"
            "        gate.recv(1)\n"
            "    return result\n")
    monkeypatch.setenv("AUTOREVIEW_ENGINE_TIMEOUT_SECONDS", "2")
    _install(repo.bin, "codex", f'''#!{sys.executable}
import os, socket, sys
if '--version' in sys.argv:
    print('codex-cli 0.136.0')
    raise SystemExit(0)
sys.stdin.read()
with socket.create_connection({listener.getsockname()!r}) as connection:
    connection.sendall((str(os.getpid()) + '\\n').encode())
    connection.recv(1)
''')
    close = subprocess.Popen([sys.executable, str(repo.bin / "forge"), "close", item],
        cwd=repo.path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pids = []
    try:
        for _ in range(2):  # Close permits two incomplete review attempts.
            with listener.accept()[0] as connection:
                connection.settimeout(20)
                pids.append(int(connection.makefile("rb").readline()))
                with listener.accept()[0] as gate:
                    gate.settimeout(20)
                    assert gate.makefile("rb").readline() == b"finished\n"
                    try:
                        assert connection.recv(1) == b""
                        _until(lambda: not alive(pids[-1]), "the timed-out review engine to end")
                    finally:
                        gate.sendall(b"1")
        output, error = close.communicate(timeout=30)
        assert close.returncode == 1, output + error
        assert "engine timed out" in output + error
    finally:
        listener.close()
        if close.poll() is None:
            close.kill()
        close.communicate(timeout=30)
        for pid in pids:
            if alive(pid):
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
