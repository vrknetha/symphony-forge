"""Worker briefs keep a short related-test list and point to a file for a long one."""

import re
from pathlib import Path

import pytest

from test_codex_resume import _resuming, _text

STORY = "FORGE-TOKENS-1"


@pytest.mark.parametrize("count", [1, 30], ids=["short", "long"])
def test_2_worker_briefs_bound_related_tests(repo, monkeypatch, sdk_data, count):
    folder, calls, turns = _resuming(repo, monkeypatch, sdk_data)
    names = [f"tests/test_{number:02d}_{'related_' * 10}board.py" for number in range(count)]
    (folder / "tests").mkdir(exist_ok=True)
    for name in names:
        (folder / name).write_text("# Covers board behavior.\n", encoding="utf-8")
    repo.git("add", "--", *names, cwd=folder)
    repo.git("commit", "-qm", "Add related tests", cwd=folder)

    for _ in range(2):  # first brief and continuation use the same limit
        worked = repo.forge("work", "BOARD/PAGE")
        assert worked.returncode == 0, worked.stdout + worked.stderr
        brief = _text(calls)
        assert "`tests/test_board.py`" in brief  # the part's required test stays inline
        if count == 1:
            assert f"`{names[0]}`" in brief
        else:
            reference = re.search(rf"{count} files listed in `([^`]+)`", brief)
            assert reference, "the brief must give the count and the path to the full list"
            path = Path(reference[1])
            assert path.parent.resolve() == turns.parent.resolve()
            assert path.read_text(encoding="utf-8").splitlines() == names
            assert all(name not in brief for name in names)
