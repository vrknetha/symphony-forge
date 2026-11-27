"""A close refuses every uncommitted file that .gitignore does not cover, including test output.

The closest test is test_done_when_tests.py::test_2_close_refuses_a_done_when_line_without_a_passing_test.
It checks an uncommitted edit before close; this covers the files the run itself leaves, and
the files a test may read but nobody committed.
"""

import json
import tomllib

import pytest

from test_close import body, env  # noqa: F401
from test_done_when_tests import _greeting_files, _local_close_with_pytest, _new_test_line, _proof

STORY = "FORGE-TESTQUAL-1-PROOF"


def _local_close_with_junitxml(env):
    _local_close_with_pytest(env)
    repo = env.repo
    config = repo.path / "forge.toml"
    settings = tomllib.loads(config.read_text("utf-8"))
    lines = [line for line in config.read_text("utf-8").splitlines()
             if line.partition("=")[0].strip() != "test"]
    lines.append(f"test = {json.dumps(settings['test'] + ' --junitxml=report.xml')}")
    env.commit(repo.path, "forge.toml", "\n".join(lines) + "\n", "Write pytest's JUnit report")
    ignore = repo.path / ".gitignore"
    env.commit(repo.path, ".gitignore", ignore.read_text("utf-8") + "report.xml\n.coverage\n",
               "Ignore the test output")
    repo.git("push", "-q", "origin", "main")


@pytest.mark.parametrize("case", [
    "repeat", "coverage-data", "retest-after-fix", "ignored-report", "unignored-report",
    "untracked-script", "untracked-fixture"])
def test_4_close_reuses_its_test_run_with_only_its_unchanged_report(env, case):
    _local_close_with_junitxml(env)
    files = _greeting_files()
    leftover = {"coverage-data": ".coverage", "ignored-report": "report.html",
                "unignored-report": "report.html"}.get(case)
    if leftover:
        # What pytest-cov and pytest-html do: they write a file in the root when the session ends.
        files["conftest.py"] = ("from pathlib import Path\n\n\n"
                                "def pytest_sessionfinish(session):\n"
                                f"    Path(session.config.rootpath, {leftover!r}).write_text('test output')\n")
    if case == "ignored-report":
        files[".gitignore"] = (env.repo.path / ".gitignore").read_text("utf-8") + "report.html\n"
    item, where = env.start_fix(files, done_when="A greeting includes the reader's name")
    _proof(env, where, _new_test_line())

    if case in ("untracked-script", "untracked-fixture"):
        # Code or data that a test may use, never committed: close names it and refuses.
        name = "scripts/greet.sh" if case == "untracked-script" else "tests/fixture.json"
        (where / name).parent.mkdir(exist_ok=True)
        (where / name).write_text("greeting\n", encoding="utf-8")
        refused = env.close(item)
        output = refused.stdout + refused.stderr
        assert f"Done-when proof: {name} is not committed." in output
        assert "Commit it, delete it, or add it to .gitignore if it is test output" in output
        assert refused.returncode == 1, output
        return

    first = env.close(item)
    assert first.returncode == 0, first.stdout + first.stderr
    assert (where / "report.xml").is_file()  # the run's output, ignored by the repo

    if case == "retest-after-fix":
        # A fix after review changes the files, so the tests run again; the ignored output they
        # leave must not block the close that follows.
        (where / "app.py").write_text(
            "def greet(name):\n    return f'Greetings, {name}!'\n", encoding="utf-8")
        (where / "tests/test_greeting.py").write_text(
            "from app import greet\n\n"
            "def test_1_greets():\n    assert greet('Ada') == 'Greetings, Ada!'\n",
            encoding="utf-8")
        env.repo.git("add", "app.py", "tests/test_greeting.py", cwd=where)
        env.repo.git("commit", "-q", "-m", "Change the greeting", "-m",
                     "Proof list:\n- Done when: tests/test_greeting.py::test_1_greets "
                     "(extend; closest tests/test_greeting.py::test_1_greets; "
                     "proves the greeting includes the reader's name)", cwd=where)
        retested = env.close(item)
        assert retested.returncode == 0, retested.stdout + retested.stderr
        assert "already passed on this machine" not in retested.stdout
        assert "tests/test_greeting.py::test_1_greets (passed in close's run)" in body(
            env.gh_calls("pr", "edit")[-1])

    second = env.close(item)
    if case == "unignored-report":
        # The first close left report.html in a repo that does not ignore it.
        output = second.stdout + second.stderr
        assert "Done-when proof: report.html is not committed." in output
        assert "Commit it, delete it, or add it to .gitignore if it is test output" in output
        assert second.returncode == 1, output
        return
    assert second.returncode == 0, second.stdout + second.stderr
    assert "already passed on this machine" in second.stdout
    if leftover:
        assert (where / leftover).is_file()
