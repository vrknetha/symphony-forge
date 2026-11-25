"""Real pinned Autoreview validates an absolute citation before close displays it.

Test audit: run the real validator with a symlinked temporary root. The launcher
path can differ from the helper's resolved root, which Path.cwd() hid before.
Fake only Codex's response and GitHub. Close must print the retained finding
with its repo path, after one model call. No seam.
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from conftest import _install
from test_close import PIN, ROOT, env  # noqa: F401

STORY = "review-temp-tree-paths"


@pytest.mark.parametrize("spelling", ["launcher", "resolved"])
def test_1_close_keeps_a_finding_through_the_temporary_review_tree(env, monkeypatch, spelling):
    item, _ = env.start_fix()
    actual = env.tmp / "review-temp"
    actual.mkdir()
    alias = env.tmp / "review-temp-link"
    try:
        alias.symlink_to(actual, target_is_directory=True)
    except OSError:
        if spelling == "launcher":
            pytest.skip("Directory symlinks are unavailable on this host")
        alias = actual
    for name in ("TMPDIR", "TMP", "TEMP"):
        monkeypatch.setenv(name, alias.as_posix())
    tool = Path(os.environ["AUTOREVIEW"])
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    assert (fixture / ".upstream-sha").read_text("utf-8").strip() == PIN
    shutil.copyfile(fixture / "scripts/autoreview", tool)
    calls = env.tmp / "model-calls.jsonl"
    _install(env.repo.bin, "codex", f'''#!{sys.executable}
import json, sys
from pathlib import Path
args = sys.argv[1:]
if "--version" in args:
    print("codex-cli 0.136.0")
    raise SystemExit(0)
sys.stdin.read()
tree = Path(args[args.index("-C") + 1])
if {spelling!r} == "resolved":
    tree = tree.resolve()
path = (tree / "app.py").as_posix()
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
