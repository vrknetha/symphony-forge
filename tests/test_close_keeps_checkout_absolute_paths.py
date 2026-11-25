"""Real pinned Autoreview keeps findings citing absolute paths inside the checkout.

Test audit: run the real validator through forge close when the reviewer cites changed
files by direct absolute checkout path, by a real directory symlink alias to the checkout,
and (on case-insensitive filesystems) by a differently cased checkout and file spelling.
Fake only Codex's response and GitHub. Close must keep every finding with its repo-relative
path after one model call, with no second review run. No seam.
"""
import json
import os
import shutil
import sys
from pathlib import Path

from conftest import _install
from test_close import PIN, ROOT, env  # noqa: F401

STORY = "a-review-finding-that-names-a-file-by-it"


def test_1_close_keeps_a_finding_citing_an_absolute_checkout_path(env):
    item, worktree = env.start_fix(changes={"app.py": "print('one')\nprint('two')\nprint('three')\n"})
    tool = Path(os.environ["AUTOREVIEW"])
    fixture = ROOT / "tests/fixtures/autoreview-ce14dcca"
    assert (fixture / ".upstream-sha").read_text("utf-8").strip() == PIN
    shutil.copyfile(fixture / "scripts/autoreview", tool)
    calls = env.tmp / "model-calls.jsonl"

    cases = [
        ("Saving loses the basket", (worktree / "app.py").as_posix(), 1),
    ]
    alias = env.tmp / "checkout-alias"
    try:
        alias.symlink_to(worktree, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
    else:
        cases.append(("Alias path drops the total", (alias / "app.py").as_posix(), 2))

    swapped = worktree.with_name(worktree.name.swapcase())
    if swapped.exists() and os.path.samefile(swapped, worktree):
        cases.append(("Mixed case path skips tax", (swapped / "APP.PY").as_posix(), 3))

    findings = [
        {"title": title,
         "body": "Gain 4, Work 2, Harm 1\nThe normal save path loses data.",
         "priority": "P1", "confidence": 0.9, "category": "bug",
         "code_location": {"file_path": path, "line": line}}
        for title, path, line in cases
    ]
    _install(env.repo.bin, "codex", f'''#!{sys.executable}
import json, sys
from pathlib import Path
args = sys.argv[1:]
if "--version" in args:
    print("codex-cli 0.136.0")
    raise SystemExit(0)
sys.stdin.read()
findings = {json.dumps(findings)}
with Path({json.dumps(calls.as_posix())}).open("a", encoding="utf-8") as log:
    log.write(json.dumps([f["code_location"]["file_path"] for f in findings]) + "\\n")
report = {{"findings": findings,
    "review_completion": "complete", "overall_correctness": "patch is incorrect",
    "overall_explanation": "Saving loses data.", "overall_confidence": 0.9}}
Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(report), encoding="utf-8")
''')

    closed = env.close(item)
    output = closed.stdout + closed.stderr
    assert closed.returncode == 1, output
    for title, _, line in cases:
        assert f"{title} (app.py:{line})" in output, output
    assert "Autoreview run 1 did not finish" not in output
    assert "invalid file path" not in output
    assert len(calls.read_text("utf-8").splitlines()) == 1
