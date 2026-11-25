"""Close runs a fix's new pytest test on the code before the fix: it must fail there."""
import json
import os
import sys
from pathlib import Path

import pytest

from conftest import machine_cores
from test_close import env  # noqa: F401

STORY = "FORGE-TESTQUAL-1"
PYTHON = Path(sys.executable).as_posix()
PYTEST = f'"{PYTHON}" -m pytest -q -p no:cacheprovider tests'
OLD = 'def greet():\n    return "hello"\n'
NEW = 'def greet():\n    return "hello, reader"\n'
PROOF = "Proof list:\n- Done when: {name}"
GREETS = "import app\n\n\ndef test_greets_a_reader():\n    assert app.greet() == \"hello, reader\"\n"
BEFORE = "passed on the code before the fix, so it does not prove the fix"
COULD_NOT = "could not run on the code before the fix"
TEST = "tests/test_greet.py::test_greets_a_reader"
MIXED = ("import app\n\n\ndef test_changed():\n    assert app.greet() == \"hello, reader\"\n\n\n"
         "def test_unrelated():\n    assert app.greet()\n")
SLOW = ("import time\n\nimport app\nimport pytest\n\n\n@pytest.mark.timeout(1)\n"
        "def test_greets_a_reader():\n    while app.greet() != \"hello, reader\":\n"
        "        time.sleep(0.1)\n    assert app.greet() == \"hello, reader\"\n")
SHOUT = "from app import shout\n\n\ndef test_shout():\n    assert shout() == \"HELLO\"\n"
FIXTURE = "import pytest\n\n\n@pytest.fixture\ndef reader():\n    return \"hello, reader\"\n"
WITH_FIXTURE = "import app\n\n\ndef test_greets_a_reader(reader):\n    assert app.greet() == reader\n"
HANGS = ("import time\n\nimport app\n\n\ndef test_greets_a_reader():\n"
         "    while app.greet() != \"hello, reader\":\n        time.sleep(0.1)\n"
         "    assert app.greet() == \"hello, reader\"\n")
STILL = "import app\n\n\ndef test_greets_a_reader():\n    assert app.greet() == \"hello\"\n"

CASES_PASSING = {"app.py": OLD + "\n\ndef bye():\n    return \"bye\"\n", "tests/test_greet.py": STILL}

# id: base files, fix files, files the fix deletes, the proof's name, exit, text close prints
CASES = {
    "fails-then-passes": ({"app.py": OLD}, {"app.py": NEW, "tests/test_greet.py": GREETS}, [],
                          TEST, 0, None),
    "passes-before": ({"app.py": OLD},
                      CASES_PASSING, [], TEST, 1, BEFORE),
    "import-error": ({"app.py": OLD},
                     {"app.py": OLD + "\n\ndef shout():\n    return \"HELLO\"\n",
                      "tests/test_shout.py": SHOUT},
                     [], "tests/test_shout.py::test_shout", 0, COULD_NOT),
    "deletes-a-file": ({"app.py": "import old\n\n\ndef greet():\n    return old.WORD\n",
                        "old.py": "WORD = \"hello\"\n"},
                       {"app.py": NEW, "tests/test_greet.py": GREETS}, ["old.py"], TEST, 0, None),
    "test-only": ({"app.py": OLD, "tests/test_greet.py": STILL},
                  {"tests/test_greet.py": STILL + "\n\ndef test_again():\n    assert app.greet()\n"},
                  [], "tests/test_greet.py::test_again", 0, None),
    "mixed-file": ({"app.py": OLD, "tests/test_greet.py": MIXED.replace("hello, reader", "hello")},
                   {"app.py": NEW, "tests/test_greet.py": MIXED}, [], "tests/test_greet.py", 1,
                   "has passing and failing cases on the code before the fix"),
    "timeout": ({"app.py": OLD}, {"app.py": NEW, "tests/test_greet.py": SLOW}, [], TEST, 0,
                "it timed out"),
    "root-fixture": ({"app.py": OLD, "conftest.py": FIXTURE.replace("reader", "old_word")},
                     {"app.py": NEW, "conftest.py": FIXTURE, "tests/test_greet.py": WITH_FIXTURE},
                     [], TEST, 0, None),
    "hang": ({"app.py": OLD}, {"app.py": NEW, "tests/test_greet.py": HANGS}, [], TEST, 0,
             "it timed out"),
    # The fix's only other change is an ignore rule, which changes no runtime code.
    "ignore-rule-only": ({"app.py": OLD, "tests/test_greet.py": MIXED.replace("hello, reader", "hello")},
                         {".gitignore": "__pycache__/\n.pytest_cache/\n",
                          "tests/test_greet.py": STILL}, [], TEST, 0, None),
    "base-moves": ({"app.py": OLD}, {"app.py": NEW, "extra.py": "WORD = 1\n", "tests/test_greet.py": GREETS},
                   [], TEST, 1, BEFORE),
    "forge-command": ({"app.py": OLD}, CASES_PASSING, [], TEST, 1, BEFORE),
}


def _worktrees(env) -> int:
    return len(env.repo.git("worktree", "list").splitlines())


@pytest.mark.platform
@pytest.mark.parametrize("case", list(CASES))
def test_5_close_refuses_a_fix_whose_test_passes_before_the_fix(env, case, monkeypatch):
    monkeypatch.setenv("FORGE_OLD_CODE_SECONDS", "3")  # a hang gives its warning fast
    if case == "timeout" and os.name == "nt":
        pytest.skip("pytest-timeout ends the whole process on Windows")
    base, fix, deleted, name, status, said = CASES[case]
    repo = env.repo
    forge_command = case == "forge-command"
    if forge_command:
        machine_cores(repo, 1)
    repo.write("forge.toml", (repo.path / "forge.toml").read_text("utf-8")
               + f"test = {json.dumps(PYTEST)}\ntest_place = \"local\"\n"
               + ('fast_test = "forge test --pytest {base}"\n' if forge_command else "")
               # A command without {base} keeps its text when the fix's base moves.
               + (f"fast_test = {json.dumps(PYTEST)}\n" if case == "base-moves" else ""))
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "Run the tests")
    for path, text in {".gitignore": "__pycache__/\n", **base}.items():
        env.commit(repo.path, path, text, "Add the app")
    repo.git("push", "-q", "origin", "main")
    item, where = env.start_fix(fix)
    for path in deleted:
        repo.git("rm", "-q", path, cwd=where)
        repo.git("commit", "-q", "-m", "Remove the old file", cwd=where)
    repo.git("commit", "--allow-empty", "-q", "-m", "List the proof", "-m",
             PROOF.format(name=name), cwd=where)
    before = _worktrees(env)
    if case == "base-moves":
        assert repo.forge("close", item, timeout=120).returncode == 0
        env.commit(repo.path, "app.py", NEW, "Main fixes the same thing")
        repo.git("push", "-q", "origin", "main")
        repo.git("fetch", "-q", "origin", cwd=where)
        repo.git("merge", "-q", "--no-edit", "origin/main", cwd=where)
    closed = repo.forge("close", item, timeout=120)
    text = closed.stdout + closed.stderr
    assert closed.returncode == status, text
    if said:
        assert said in text, text
    if case == "deletes-a-file":
        assert COULD_NOT not in text and not (where / "old.py").exists(), text
    if case in ("fails-then-passes", "deletes-a-file", "test-only", "root-fixture", "ignore-rule-only"):
        assert BEFORE not in text and COULD_NOT not in text, text
    assert _worktrees(env) == before
