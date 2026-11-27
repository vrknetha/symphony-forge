"""Long-running tests can use a longer timeout on Windows."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.platform

STORY = "windows-rerun-flakes"
ROOT = Path(__file__).resolve().parents[1]


def test_2_known_slow_tests_get_more_time_only_on_windows():
    targets = [
        ("test_queue_land_all.py", "test_3_a_failed_check_naming_none_of_the_files_runs_again_once"),
    ]
    for file, name in targets:
        tree = ast.parse((ROOT / "tests" / file).read_text(encoding="utf-8"))
        test = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        timeout = next((mark.args[0] for mark in test.decorator_list if isinstance(mark, ast.Call)
                        and isinstance(mark.func, ast.Attribute) and mark.func.attr == "timeout"), None)
        assert timeout is not None, f"{file}::{name} needs a Windows timeout"
        for platform, seconds in [("win32", 600), ("linux", 150), ("darwin", 150)]:
            assert eval(compile(ast.Expression(timeout), file, "eval"),
                        {"sys": SimpleNamespace(platform=platform)}) == seconds
