"""Close checks each test a worker names in its proof list against close's own test run."""
import json
import shutil
import sys
from pathlib import Path

import pytest

from conftest import ROOT
from test_close import env  # noqa: F401

STORY = "forge-writes-proof-list"
PROOF = ("Proof list:\n- Done when: tests/test_greeting.py::test_returning "
         "(including empty names)\n"
         "- Done when: tests/test_greeting.py::test_role[staff,active]\n"
         "- Done when: tests/test_greeting.py::test_later\n"
         "- Done when: tests/test_other.py::test_other\n"
         "- Done when: tests/test_greeting.py::test_case[new]\n"
         "- Done when: tests/test_greeting.py::test_case[back]\n"
         "- Done when: `src/greet.test.ts`\n"
         "- Done when: `__tests__/greeting.js`\n"
         "- Done when: tests/test_greeting.py\n"
         "- Done when: `tests/test_greeting.py::test_returning`\n"
         "- Done when: tests/test_greeting.py::test_case")
# A test whose call passes and whose teardown fails.
TEARDOWN = ("\n\n@pytest.fixture\ndef broken():\n    yield\n    raise RuntimeError(\"teardown\")\n\n\n"
            "def test_cleanup(broken):\n    pass\n")
GREETING = ("import pytest\n\n\ndef test_returning():\n    assert True\n\n\n"
            "@pytest.mark.parametrize(\"who\", [\"new\", \"back\"])\ndef test_case(who):\n"
            "    assert who == \"new\"\n\n\n"
            "@pytest.mark.parametrize(\"role\", [\"staff\"], ids=[\"staff,active\"])\n"
            "def test_role(role):\n    assert role\n\n\n"
            "@pytest.mark.skip(reason=\"later\")\ndef test_later():\n    pass\n")


def _close(env, adopted, command, red=True, greeting=GREETING, docs_only=False, proof=PROOF):
    repo = env.repo
    if adopted:
        shutil.copytree(ROOT / "tests/fixtures/adopted-v1.2.2/client", repo.path, dirs_exist_ok=True)
    version = repo.forge("--version").stdout.split()[-1]
    text = (repo.path / "forge.toml").read_text("utf-8").replace('version = "v1.2.2"',
                                                                  f'version = "{version}"')
    kept = [line for line in text.splitlines()
            if line.partition("=")[0].strip() not in ("test", "fast_test", "checks", "test_place")]
    env.commit(repo.path, "forge.toml", f"test = {json.dumps(command)}\ntest_place = \"local\"\n"
               f"checks = [\"forge-pr-check\"]\n"
               + "\n".join(kept) + "\n", "Run the tests")
    # Named skipped, missing-run and failing tests now refuse close, while its published list
    # still reports each result. Missing branch names have their own Done-when refusal cases.
    files = {".gitignore": "__pycache__/\n", "tests/test_greeting.py": greeting,
             "tests/test_other.py": "def test_other():\n    assert True\n",
             "src/greet.test.ts": "test('greets', () => {});\n",
             "__tests__/greeting.js": "test('greets', () => {});\n"}
    if docs_only:  # the tests are already on the default branch; the fix changes only a readme
        for path, text in files.items():
            env.commit(repo.path, path, text, "Add the tests")
        files = {"README.md": "Hello, readers.\n"}
    repo.git("push", "-q", "origin", "main")
    item, where = env.start_fix(files)
    repo.git("commit", "--allow-empty", "-q", "-m", "List the proof", "-m", proof, cwd=where)
    for _ in range(1 if red else 2):  # a second close reuses the passing run on the same files
        closed = env.close(item)
        assert (closed.returncode != 0) == red, closed.stdout + closed.stderr
        if red:
            assert "Done-when proof:" in closed.stdout + closed.stderr
    # The body as gh received it on the last publish, before any later rewrite of its file.
    sent = (env.repo.bin / "gh-bodies.jsonl").read_text("utf-8").splitlines()
    assert env.gh_calls("pr", "edit"), "close never refreshed the pull request after its run"
    return env.prompt(), json.loads(sent[-1])


@pytest.mark.parametrize("adopted, red, options, teardown", [
    (False, False, "", False), (False, True, "", False),
    (False, False, " -ra", False), (False, False, " && {run} tests/test_other.py", False),
    (False, True, "", True)], ids=["new-client", "failed-test",
                                   "own-report-options", "two-pytest-runs", "teardown-error"])
def test_1_close_writes_the_proof_list_from_the_tests_it_ran(env, adopted, red, options, teardown):
    run = f'"{Path(sys.executable).as_posix()}" -m pytest -q -p no:cacheprovider'
    # The client's own report options, such as -ra, cannot hide close's per-test results, and a
    # second pytest in the command keeps the first one's results.
    command = f'{run} tests/test_greeting.py' + ("" if red else ' -k "not back"')
    proof = PROOF + ("\n- Done when: tests/test_greeting.py::test_cleanup" if teardown else "")
    prompt, published = _close(env, adopted, command + options.format(run=run), True,
                               GREETING + TEARDOWN if teardown else GREETING, proof=proof)
    # The second pytest has no name filter, so it also runs the named returning-reader case.
    failed_case = red or "test_other" in options
    # A name in a code span matches without its backtick.
    assert "`tests/test_greeting.py::test_returning (passed in close's run)`" in published
    # A test has one result, the worst of its phases: a failed teardown is an error.
    if teardown:
        assert "- Done when: tests/test_greeting.py::test_cleanup (error in close's run)" in published
    # Close keeps the worker's words and adds each named test's result next to it.
    assert ("- Done when: tests/test_greeting.py::test_returning "
            "(passed in close's run) (including empty names)") in published
    # A parameter id runs to its closing bracket, commas and all.
    assert ("- Done when: tests/test_greeting.py::test_role[staff,active] "
            "(passed in close's run)") in published
    assert ("- Done when: tests/test_other.py::test_other (passed in close's run)"
            if red or "test_other" in options else "- Done when: not run") in published
    # A name that matches several cases counts the cases that ran.
    assert ("- Done when: tests/test_greeting.py (3 passed, 1 failed, 1 error, 1 skipped in close's run)"
            if teardown else
            "- Done when: tests/test_greeting.py (3 passed, 1 failed, 1 skipped in close's run)"
            if failed_case else "- Done when: tests/test_greeting.py (3 passed, 1 skipped in close's run)"
            ) in published
    # A test name without its parameter id counts the cases that ran.
    assert ("- Done when: tests/test_greeting.py::test_case (1 passed, 1 failed in close's run)"
            if failed_case else "- Done when: tests/test_greeting.py::test_case (1 passed in close's run)"
            ) in published
    # A named case matches only itself; a case that failed shows as failed.
    assert "- Done when: tests/test_greeting.py::test_case[new] (passed in close's run)" in published
    assert ("- Done when: tests/test_greeting.py::test_case[back] (failed in close's run)"
            if failed_case else "- Done when: not run") in published
    assert "- Done when: tests/test_greeting.py::test_later (skipped in close's run)" in published
    # A test close cannot match to its run's results is never copied as proof.
    assert "`src/greet.test.ts (not checked)`" in published
    assert "`__tests__/greeting.js (not checked)`" in published
    # The review runs alongside the tests, so its list names only the tests the branch has.
    assert "tests/test_greeting.py::test_returning (in the branch; close's test run gives its result)" in prompt


def test_2_a_runner_without_test_results_shows_named_tests_as_not_checked(env):
    python = Path(sys.executable).as_posix()
    _, published = _close(env, False, f'"{python}" -c "print(1)"')
    assert ("- Done when: tests/test_greeting.py::test_returning (not checked) "
            "(including empty names)") in published
    assert "not checked" in published


def test_3_a_change_close_runs_no_tests_for_shows_named_tests_as_not_run(env):
    python = Path(sys.executable).as_posix()
    _, published = _close(env, False, f'"{python}" -m pytest -q -p no:cacheprovider tests',
                          docs_only=True)
    assert ("- Done when: not run (close ran no tests for this change) "
            "(including empty names)") in published
    assert "test_returning" not in published


# A client test that starts its own pytest with its own import path and root directory.
NESTED = ("import os, pathlib, subprocess, sys\n\n\ndef test_returning(tmp_path):\n"
          "    (tmp_path / \"test_inner.py\").write_text(\"def test_inner():\\n    pass\\n\")\n"
          "    run = subprocess.run([sys.executable, \"-m\", \"pytest\", \"-q\", \"-p\", \"no:cacheprovider\",\n"
          "                          \"test_inner.py\"], cwd=tmp_path, capture_output=True, text=True,\n"
          "                         env={**os.environ, \"PYTHONPATH\": str(tmp_path)})\n"
          "    assert run.returncode == 0, run.stdout + run.stderr\n")


@pytest.mark.parametrize("adopted, options", [(False, ""), (False, " -n 2")],
                         ids=["new-client", "xdist"])
def test_4_a_test_that_starts_its_own_pytest_passes_under_close(env, adopted, options):
    run = f'"{Path(sys.executable).as_posix()}" -m pytest -q -p no:cacheprovider'
    proof = "Proof list:\n- Done when: tests/test_greeting.py::test_returning (including empty names)"
    _, published = _close(env, adopted, f"{run} tests/test_greeting.py{options}", red=False,
                          greeting=NESTED, proof=proof)
    assert ("- Done when: tests/test_greeting.py::test_returning "
            "(passed in close's run) (including empty names)") in published
