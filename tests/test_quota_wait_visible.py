"""Waits for GitHub quota print the numbers they follow, recheck each minute and resume.

Only GitHub and the clock are fake (Forge's fake clock: sleeps advance time, nothing waits).
Each test builds its own repo, its own fake GitHub and its own quota numbers.
"""
import json
from datetime import datetime, timezone

import pytest

from test_close import env  # noqa: F401

STORY = "quota-wait-visible"
pytestmark = pytest.mark.platform

RESET = 2_000_000_000  # A fixed reset time, far ahead: 03:33:20 UTC.


def _quota_stub(stub, low, high, switch_after, extra=""):
    """Quota reads log their (fake) time. The reading is `low` until `switch_after` reads, then `high`."""
    first, rest = stub.read_text("utf-8").split("\n", 1)
    stub.write_text(first + "\n" + f'''import json, pathlib, sys, time
if sys.argv[1:3] == ["api", "rate_limit"]:
    log = pathlib.Path(__file__).resolve().parent / "reads"
    rows = log.read_text().splitlines() if log.exists() else []
    with log.open("a") as stream: stream.write(str(time.monotonic()) + "\\n")
    amount = {low!r} if len(rows) < {switch_after} else {high!r}
    print(json.dumps({{"resources": {{name: {{"limit": 5000, "remaining": amount, "reset": {RESET}}}
                                    for name in ("core", "graphql")}}}}))
    sys.exit(0)
{extra}''' + rest, encoding="utf-8")


def _stamp_waiting_lines(env):
    """Record the fake-clock time of every printed wait line, in the forge process itself."""
    clock = env.tmp / "clock" / "sitecustomize.py"
    clock.write_text(clock.read_text("utf-8") + f'''
import builtins
_print = builtins.print
def print(*args, **kwargs):
    if args and "Waiting for GitHub API quota" in str(args[0]):
        with open({(env.repo.bin / "said").as_posix()!r}, "a") as stream: stream.write(str(time.monotonic()) + "\\n")
    _print(*args, **kwargs)
builtins.print = print
''', encoding="utf-8")


def _waiting_lines(output):
    return [line for line in output.splitlines() if "Waiting for GitHub API quota" in line]


def _reads(env):
    return [float(row) for row in (env.repo.bin / "reads").read_text("utf-8").splitlines()]


def test_1_check_wait_prints_numbers_every_few_minutes_and_resumes(env, fake_clock):
    item, where = env.start_fix()
    _stamp_waiting_lines(env)
    _quota_stub(env.repo.bin / "gh", 0, 4379, 9)
    done = env.repo.forge("close", item, cwd=where)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = _waiting_lines(done.stdout)
    assert len(lines) >= 3
    stamps = [float(row) for row in (env.repo.bin / "said").read_text("utf-8").splitlines()]
    assert len(stamps) == len(lines)
    reads = _reads(env)
    # The wait starts at its first quota read and ends at the last one. No silence over a few minutes
    # at any point: before the first line, between lines, or after the last line until the resume.
    marks = [reads[0], *stamps, reads[-1]]
    assert all(after - before <= 150 for before, after in zip(marks, marks[1:]))
    expected = datetime.fromtimestamp(RESET, timezone.utc).strftime("%H:%M:%S UTC")
    assert all(f"REST 0/5000, resets {expected}; GraphQL 0/5000, resets {expected}" in line
               for line in lines)
    reads = _reads(env)
    assert all(after - before <= 60 for before, after in zip(reads, reads[1:]))
    assert reads[-1] - reads[0] >= 240  # The close waited several minutes, and said so each two.


def test_2_rate_limit_error_retries_as_soon_as_quota_is_back(env, fake_clock):
    item, where = env.start_fix()
    clock = env.tmp / "clock" / "sitecustomize.py"
    clock.write_text(clock.read_text("utf-8") +
                     '\nreal_time = time.time\ntime.time = lambda: real_time() + float(offset.read_text("utf-8"))\n',
                     encoding="utf-8")
    first, rest = (env.repo.bin / "gh").read_text("utf-8").split("\n", 1)
    (env.repo.bin / "gh").write_text(first + "\n" + f'''import json, pathlib, sys, time
here = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
limited, after = here / "limited", here / "reads-after-limit"
if args[:2] == ["api", "rate_limit"]:
    rows = after.read_text().splitlines() if after.exists() else []
    if limited.exists():
        with after.open("a") as stream: stream.write(str(time.monotonic()) + "\\n")
    amount = 0 if limited.exists() and len(rows) < 1 else 4379  # Zero at the first read after the failure.
    print(json.dumps({{"resources": {{name: {{"limit": 5000, "remaining": amount, "reset": {RESET}}}
                                    for name in ("core", "graphql")}}}}))
    sys.exit(0)
if args[:2] == ["pr", "edit"]:
    with (here / "attempts").open("a") as stream: stream.write(str(time.monotonic()) + "\\n")
    rows = after.read_text().splitlines() if after.exists() else []
    if not limited.exists() or len(rows) < 2:  # Every attempt fails until quota is reported back.
        limited.write_text("x")
        print("API rate limit exceeded for user.", file=sys.stderr)
        sys.exit(1)
''' + rest, encoding="utf-8")
    done = env.repo.forge("close", item, cwd=where)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = [line for line in (done.stdout + done.stderr).splitlines() if "rate limit reached" in line]
    assert lines and all("REST 0/5000, resets" in line and "GraphQL 0/5000, resets" in line for line in lines)
    attempts = [float(row) for row in (env.repo.bin / "attempts").read_text("utf-8").splitlines()]
    recovered = float((env.repo.bin / "reads-after-limit").read_text("utf-8").splitlines()[1])
    assert attempts[1] >= recovered  # No retry while quota still read zero.
    assert 0 <= attempts[1] - recovered < 1  # The retry follows the refresh that showed quota.
    assert recovered - attempts[0] < 60  # Without a fixed one-minute pause.


def test_4_one_wait_stays_open_while_a_little_quota_remains(env, fake_clock):
    item, where = env.start_fix()
    _quota_stub(env.repo.bin / "gh", 150, 150, 0)
    done = env.repo.forge("close", item, cwd=where)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not _waiting_lines(done.stdout)
