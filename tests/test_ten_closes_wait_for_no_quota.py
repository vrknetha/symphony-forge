"""Ten closes at once with a healthy GitHub core budget print no quota wait."""
import json
import subprocess
import sys
import time

import pytest

from test_close import env  # noqa: F401
from test_queue_land_all import client, _fix  # noqa: F401

STORY = "with-ten-closes-and-github-s-core-budget"
pytestmark = pytest.mark.platform


@pytest.mark.timeout(240)
def test_1_ten_closes_with_a_healthy_core_budget_print_no_quota_wait(client, monkeypatch, fake_clock):
    env = client
    places = [_fix(env, monkeypatch, f"change-{number}", number + 1,
                   {f"file{number}.py": "VALUE = 1\n"}) for number in range(10)]
    stub = env.repo.bin / "gh"
    intercept = '''import os, threading, time
if args[:2] == ["api", "rate_limit"]:
    print(json.dumps({"resources": {
        "core": {"remaining": 4300, "reset": int(time.time()) + 3600},
        "graphql": {"remaining": 4300, "reset": int(time.time()) + 3600}}}))
    sys.exit(0)
if args[:4] == ["api", "--paginate", "--jq", ".check_runs[]"]:
    branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True,
                            text=True).stdout.strip()
    mine = here / ("held-" + str(os.getpid()))
    # A wait is held while its file is fresh: a request that times out stops touching it.
    def held():
        return sum(time.time() - path.stat().st_mtime < 0.5 for path in here.glob("held-*"))
    while not (here / "overlap").exists() and not (here / "release-all").exists():
        mine.touch()
        if held() >= 10:
            (here / "overlap").touch()
        threading.Event().wait(0.05)
'''
    stub.write_text(stub.read_text("utf-8").replace(
        "args = sys.argv[1:]\n", "args = sys.argv[1:]\n" + intercept, 1), encoding="utf-8")
    overlap = env.repo.bin / "overlap"
    processes, streams, outputs = [], [], []
    try:
        for number, where in enumerate(places):
            output = env.tmp / f"close-{number}.out"
            outputs.append(output)
            stdout = output.open("wb")
            streams.append(stdout)
            processes.append(subprocess.Popen(
                [sys.executable, str(env.repo.bin / "forge"), "close", f"change-{number}"],
                cwd=where, stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + 120
        while not overlap.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert overlap.exists(), "The ten check waits were never held at the same time."
    finally:
        (env.repo.bin / "release-all").touch()
        for process in processes:
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        for stream in streams:
            stream.close()
    for process, output in zip(processes, outputs):
        text = output.read_text("utf-8")
        assert process.returncode == 0, text
        assert "Waiting for GitHub API quota" not in text, text
