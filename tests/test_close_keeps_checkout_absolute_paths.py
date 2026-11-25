"""Real pinned Autoreview keeps a finding that cites an absolute path inside the checkout.

Test audit: run the real validator through forge close when the reviewer cites a file
using its absolute path inside the checkout (both raw and resolved). Fake only Codex's
response and GitHub. Close must keep the finding with its repo-relative path after one
model call, with no second review run. No seam.
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from conftest import _install
from test_close import PIN, ROOT, env  # noqa: F401

STORY = "a-review-finding-that-names-a-file-by-it"


@pytest.mark.parametrize("spelling", ["raw", "resolved"])
def test_1_close_keeps_a_finding_citing_an_absolute_checkout_path(env, spelling):
    item, worktree = env.start_fix()
    tool = Path(os.environ["AUTOREVIEW"])
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    assert (fixture / ".upstream-sha").read_text("utf-8").strip() == PIN
    shutil.copyfile(fixture / "scripts/autoreview", tool)
    calls = env.tmp / "model-calls.jsonl"
    checkout = worktree.resolve() if spelling == "resolved" else worktree
    cited = (checkout / "app.py").as_posix()
    _install(env.repo.bin, "codex", f'''#!{sys.executable}
import json, sys
from pathlib import Path
args = sys.argv[1:]
if "--version" in args:
    print("codex-cli 0.136.0")
    raise SystemExit(0)
sys.stdin.read()
path = {json.dumps(cited)}
with Path({json.dumps(calls.as_posix())}).open("a", encoding="utf-8") as log:
    log.write(json.dumps(path) + "\\n")
report = {{"findings": [{{"title": "Saving loses the basket",
    "body": "Gain 4, Work 2, Harm 1\\nThe normal save path loses the basket.",
    "priority": "P1", "confidence": 0.9, "category": "bug",
    "code_location": {{"file_path": path, "line": 1}}}}],
    "review_completion": "complete", "overall_correctness": "patch is incorrect",
    "overall_explanation": "Saving loses the basket.", "overall_confidence": 0.9}}
Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(report), encoding="utf-8")
''')

    closed = env.close(item)
    output = closed.stdout + closed.stderr
    assert closed.returncode == 1, output
    assert "Saving loses the basket (app.py:1)" in output, output
    assert "Autoreview run 1 did not finish" not in output
    assert "invalid file path" not in output
    assert len(calls.read_text("utf-8").splitlines()) == 1
