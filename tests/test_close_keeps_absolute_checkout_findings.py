"""Close keeps a finding that cites the original worktree by absolute path."""
import json
import os
import shutil
import sys
from pathlib import Path

from conftest import _install
from test_close import ROOT, env, finding, report  # noqa: F401

STORY = "abb-sol-abspath"


def test_1_close_keeps_absolute_checkout_finding_without_retry(env):
    item, checkout = env.start_fix()
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca/scripts/autoreview"
    shutil.copyfile(fixture, os.environ["AUTOREVIEW"])
    issue = finding("P1", "Saving loses the basket", (checkout / "app.py").as_posix())
    del issue["code_location"]["column"]
    response = report(issue)
    del response["usage"], response["review_status"]
    response["review_completion"] = "complete"
    calls = env.tmp / "model-calls"
    _install(env.repo.bin, "codex", f'''#!{sys.executable}
import sys
from pathlib import Path
args = sys.argv[1:]
if "--version" in args:
    print("codex-cli 0.136.0")
    raise SystemExit(0)
sys.stdin.read()
with Path({json.dumps(calls.as_posix())}).open("a", encoding="utf-8") as log:
    log.write("review\\n")
Path(args[args.index("--output-last-message") + 1]).write_text(
    {json.dumps(json.dumps(response))}, encoding="utf-8")
''')

    closed = env.close(item)
    output = closed.stdout + closed.stderr
    assert closed.returncode == 1, output
    assert "Saving loses the basket (app.py:1)" in output, output
    assert calls.read_text("utf-8").splitlines() == ["review"]
