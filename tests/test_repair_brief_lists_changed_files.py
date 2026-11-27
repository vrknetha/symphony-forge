"""Worker briefs keep a short related-test list and point to a file for a long one."""

import re
from pathlib import Path

import pytest

from test_codex_resume import _resuming, _text

STORY = "FORGE-TOKENS-1"


@pytest.mark.parametrize("list_length", [2_000, 2_001], ids=["at-limit", "over-limit"])
def test_2_worker_briefs_bound_related_tests(repo, monkeypatch, sdk_data, list_length):
    folder, calls, turns = _resuming(repo, monkeypatch, sdk_data)
    names = [f"tests/test_{number:02d}_{'x' * 74}board.py" for number in range(20)]
    # The paths, backticks and separators total 1,998 characters before padding.
    names[-1] = names[-1].replace("board.py", "x" * (list_length - 1_998) + "board.py")
    inline_list = ", ".join(f"`{name}`" for name in names)
    assert len(inline_list) == list_length
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
        if list_length == 2_000:
            assert inline_list in brief
        else:
            reference = re.search(rf"{len(names)} files listed in `([^`]+)`", brief)
            assert reference, "the brief must give the count and the path to the full list"
            path = Path(reference[1])
            assert path.parent.resolve() == turns.parent.resolve()
            assert path.read_text(encoding="utf-8").splitlines() == names
            assert all(name not in brief for name in names)
