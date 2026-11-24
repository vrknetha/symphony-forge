"""Forge tells builders to map each Done-when item to its test and checks that mapping."""

import json
import sys
from pathlib import Path

import pytest

from test_close import env  # noqa: F401
from test_close import GREEN, STORY_DOC, body, run
from test_worker import calls, install_claude

STORY = "FORGE-TESTQUAL-1-PROOF"


def _local_close_without_test_command(env):
    repo = env.repo
    config = repo.path / "forge.toml"
    lines = [line for line in config.read_text("utf-8").splitlines()
             if not line.partition("=")[0].strip() in ("checks", "test_place")]
    lines.extend(['test_place = "local"', 'checks = ["forge-pr-check"]'])
    env.commit(repo.path, "forge.toml", "\n".join(lines) + "\n", "Run close tests locally")
    repo.git("push", "-q", "origin", "main")


def _local_close_with_pytest(env, *, ignore_python_cache=True, directory=None):
    repo = env.repo
    config = repo.path / "forge.toml"
    lines = [line for line in config.read_text("utf-8").splitlines()
             if line.partition("=")[0].strip() not in ("checks", "test", "fast_test", "test_place")]
    python = Path(sys.executable).as_posix()
    command = f'"{python}" -m pytest -q -p no:cacheprovider'
    if directory:
        command = f"cd {directory} && {command}"
    lines.extend([f"test = {json.dumps(command)}", 'test_place = "local"',
                  'checks = ["forge-pr-check"]'])
    env.commit(repo.path, "forge.toml", "\n".join(lines) + "\n", "Run close tests locally")
    if ignore_python_cache:
        ignore = repo.path / ".gitignore"
        kept = [line for line in ignore.read_text("utf-8").splitlines()
                if "__pycache__" not in line] if ignore.exists() else []
        kept.append("__pycache__/")
        env.commit(repo.path, ".gitignore", "\n".join(kept) + "\n", "Ignore Python test cache")
    repo.git("push", "-q", "origin", "main")


def _local_close_with_picker(env):
    _local_close_with_pytest(env)
    repo = env.repo
    config = repo.path / "forge.toml"
    command = 'forge test --pytest {base}'
    env.commit(repo.path, "forge.toml", config.read_text("utf-8")
               + f"fast_test = {json.dumps(command)}\n", "Select related tests")
    repo.git("push", "-q", "origin", "main")


def _ci_close(env):
    repo = env.repo
    config = repo.path / "forge.toml"
    lines = [line for line in config.read_text("utf-8").splitlines()
             if line.partition("=")[0].strip() not in ("checks", "test", "fast_test", "test_place")]
    python = Path(sys.executable).as_posix()
    command = f'"{python}" -m pytest -q -p no:cacheprovider'
    lines.extend([f"test = {json.dumps(command)}", 'test_place = "ci"',
                  'checks = ["build", "forge-pr-check"]'])
    env.commit(repo.path, "forge.toml", "\n".join(lines) + "\n", "Use the CI test check")
    repo.git("push", "-q", "origin", "main")


def _start_fix_without_proof(env, changes, *, done_when="The readme opens with a greeting"):
    env.approve_working_build()
    where = env.tmp / "fix-tidy-readme"
    env.repo.git("worktree", "add", "-q", "-b", "fix/tidy-readme", str(where))
    env.commit(where, ".factory/fixes/tidy-readme.json",
               json.dumps({"branch": "fix/tidy-readme", "status": "working", "kind": "fix",
                           "why": "Readme greets new readers", "done_when": done_when}), "Start")
    for path, text in changes.items():
        env.commit(where, path, text, "Work")
    return "tidy-readme", where


def _proof(env, where, item_line):
    env.repo.git("commit", "--allow-empty", "-q", "-m", "Record Done-when proof", "-m",
                 "Proof list:\n" + item_line, cwd=where)


def _greeting_files(test="def test_1_greets():\n    assert greet('Ada') == 'Hello, Ada!'\n"):
    return {
        "app.py": "def greet(name):\n    return f'Hello, {name}!'\n",
        "tests/test_greeting.py": "from app import greet\n\n" + test,
    }


def _new_test_line(name="tests/test_greeting.py::test_1_greets"):
    return (f"- Done when: {name} (new; closest none; "
            "proves the greeting includes the reader's name)")


def test_1_the_brief_asks_for_the_closest_test_and_the_review_checks_the_choice(env):
    log = install_claude(env.repo)
    item, where = env.start_approved_task(
        STORY_DOC,
        changes={
            "app.py": "def save_basket(items):\n    return list(items)\n",
            "tests/test_app.py": "from app import save_basket\n\n"
            "def test_1_saves_basket():\n    assert save_basket(['tea']) == ['tea']\n",
        },
    )

    built = env.repo.forge("work", item)
    assert built.returncode == 0, built.stdout + built.stderr
    brief = " ".join(calls(log)[-1]["brief"].split())
    assert "Name the closest existing test; the brief lists the tests that name your Scope." in brief
    assert ("Choose reuse when it already proves the outcome, extend when a new case or assertion "
            "in it can prove it, or new.") in brief
    assert ('A new test names the outcome that no existing test proves; write "closest none" '
            "when no test is near it. Record the choice on the test's Proof list line.") in brief
    assert "`- <n>: <test> (<decision>)`" in brief
    assert ("When CI treats a change as docs only and skips tests, forge-pr-check checks only "
            "that each named test is on the branch and says so.") in brief

    env.repo.git(
        "commit", "--allow-empty", "-q", "-m", "Record the test choice", "-m",
        "Proof list:\n- 1: tests/test_app.py::test_1_saves_basket "
        "(new; closest none; proves the selected items are saved for the shopper)",
        cwd=where,
    )
    closed = env.close(item)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    prompt = " ".join(env.prompt().split())
    assert ("For each line, read the named test: report a test whose assertions would still pass "
            "if the line were false as a P1 `Test: <the line>`, and a `check:` entry for an item "
            "that changes runtime behaviour the same way. A new test's line names the closest "
            "existing test, or none, and the outcome no existing test proves; a missing choice is "
            "part of `Gate: proof list`, and a new test whose outcome the closest test already "
            "proves is a P2 `Follow-up: duplicate test`.") in prompt


@pytest.mark.parametrize("case", [
    "pytest-passes", "no-line", "not-on-branch", "fails", "skipped", "task-item-missing",
    "reused-not-selected", "reused-after-main-advance",
    pytest.param("retry-recovered", marks=pytest.mark.skipif(
        sys.platform == "win32", reason="pytest-timeout signal recovery needs POSIX")),
    "uncommitted-edit", "proof-only-commit",
    "javascript-name", "javascript-missing", "ci", "own-ci-missing", "own-ci-valid",
    "review-prompt-local", "review-prompt-own-ci", "settings-only", "no-test-command",
    "docs-only", "docs-pytest-not-run", "closest-is-not-proof", "untracked-cache", "two-app-wrong-root",
    "two-app-correct-root", "named-proof-keeps-related-tests", "stacked-fix-own-proof",
    "generated-client-needs-proof", "ci-branch-of-another-repo",
    "ci-dirty-checkout-reruns", "ci-clone-without-default-branch-ref",
], ids=[
    "pytest-passes", "no-line", "not-on-branch", "fails", "skipped", "task-item-missing",
    "reused-not-selected", "reused-after-main-advance", "retry-recovered", "uncommitted-edit", "proof-only-commit",
    "javascript-name", "javascript-missing", "ci", "own-ci-missing", "own-ci-valid",
    "review-prompt-local", "review-prompt-own-ci", "settings-only", "no-test-command",
    "docs-only", "docs-pytest-not-run", "closest-is-not-proof", "untracked-cache", "two-app-wrong-root",
    "two-app-correct-root", "named-proof-keeps-related-tests", "stacked-fix-own-proof",
    "generated-client-needs-proof", "ci-branch-of-another-repo",
    "ci-dirty-checkout-reruns", "ci-clone-without-default-branch-ref",
])
@pytest.mark.platform
def test_2_close_refuses_a_done_when_line_without_a_passing_test(env, monkeypatch, case):
    if case == "no-line":
        _local_close_with_pytest(env)
        item, _ = _start_fix_without_proof(env, {"app.py": "def greet(name): return name\n"})
        expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
    elif case == "no-test-command":
        _local_close_without_test_command(env)
        item, _ = _start_fix_without_proof(env, {"app.py": "def greet(name): return name\n"})
        expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
    elif case == "not-on-branch":
        _local_close_without_test_command(env)
        item, where = _start_fix_without_proof(env, _greeting_files())
        _proof(env, where, _new_test_line("tests/test_missing.py::test_1_greets"))
        expected = "Done-when proof: tests/test_missing.py::test_1_greets is not on this branch."
    elif case in ("pytest-passes", "fails", "skipped"):
        _local_close_with_pytest(env)
        test = _greeting_files()["tests/test_greeting.py"]
        if case == "fails":
            test = "from app import greet\n\ndef test_1_greets():\n    assert greet('Ada') == 'Welcome, Ada!'\n"
        elif case == "skipped":
            test += ("\nimport pytest\n\n@pytest.mark.skip(reason='not ready')\n"
                     "def test_2_waits():\n    assert greet('Ada') == 'Hello, Ada!'\n")
        item, where = env.start_fix(_greeting_files(test), done_when="A greeting includes the reader's name")
        _proof(env, where, (_new_test_line("tests/test_greeting.py") if case == "skipped"
                            else _new_test_line()))
        expected = ("Done-when proof: tests/test_greeting.py::test_1_greets failed in this test run."
                    if case == "fails" else
                    "Done-when proof: tests/test_greeting.py was skipped in this test run."
                    if case == "skipped" else "Ready:")
    elif case == "task-item-missing":
        _local_close_without_test_command(env)
        story = STORY_DOC.replace("| T1 | Save a basket | Shoppers can save their basket with one click | 1 |",
                                 "| T1 | Save a basket | Shoppers can save their basket with one click | 1, 2 |")
        story = story.replace("| T2 | Show a saved basket | A saved basket shows again after sign-in | 2 | `show.py` | `tests/test_show.py` | T1 | yes |\n", "")
        item, where = env.start_approved_task(
            story, changes={"app.py": "def save_basket(items): return list(items)\n",
                            "tests/test_app.py": "from app import save_basket\n\ndef test_1_saves_basket():\n    assert save_basket(['tea']) == ['tea']\n"})
        _proof(env, where, "- 1: tests/test_app.py::test_1_saves_basket "
                            "(new; closest none; proves a shopper can save a basket)")
        expected = "Done-when proof: Done-when 2 names no test in the Proof list."
    elif case in ("reused-not-selected", "reused-after-main-advance"):
        _local_close_with_picker(env)
        env.commit(env.repo.path, "tests/test_independent.py",
                   "def test_1_independent():\n    assert 2 + 2 == 4\n", "Add an independent test")
        env.repo.git("push", "-q", "origin", "main")
        base = env.repo.git("rev-parse", "HEAD")
        item, where = env.start_fix({"app.py": "def greet(name): return 'Hello, ' + name\n"}, base=base)
        _proof(env, where, _new_test_line("tests/test_independent.py::test_1_independent"))
        if case == "reused-after-main-advance":
            # Selection must keep this fix's proof when a newer task's proof arrives from main.
            date = int(env.repo.git("show", "-s", "--format=%ct", "HEAD", cwd=where)) + 60
            with monkeypatch.context() as incoming:
                incoming.setenv("GIT_COMMITTER_DATE", f"@{date} +0000")
                env.commit(env.repo.path, "incoming.py", "value = 1\n",
                           "Another task\n\nProof list:\n- 1: check: The incoming value is present.")
            env.repo.git("push", "-q", "origin", "main")
            env.repo.git("fetch", "-q", "origin", "main", cwd=where)
            env.repo.git("merge", "-q", "--no-edit", "origin/main", cwd=where)
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        assert closed.returncode == 0, output
        assert "tests/test_independent.py::test_1_independent (passed in close's run)" in body(
            env.gh_calls("pr", "edit")[-1])
        return
    elif case == "retry-recovered":
        _local_close_with_pytest(env)
        count = (env.tmp / "attempts.txt").as_posix()
        test = ("import threading\nfrom pathlib import Path\nimport pytest\n\n"
                f"@pytest.mark.timeout(0.2, method='signal')\n"
                "def test_1_greets():\n"
                f"    path = Path({count!r})\n"
                "    attempts = int(path.read_text() if path.exists() else '0') + 1\n"
                "    path.write_text(str(attempts))\n"
                "    if attempts == 1:\n        threading.Event().wait()\n"
                "    assert attempts == 2\n")
        item, where = env.start_fix({"app.py": "def greet(): return 'hello'\n",
                                     "tests/test_greeting.py": test,
                                     "tests/test_other.py": "from app import greet\n\n"
                                     "def test_1_other():\n    assert greet() == 'hello'\n"},
                                   done_when="The greeting is available")
        _proof(env, where, _new_test_line() + "\n" + _new_test_line("tests/test_other.py::test_1_other"))
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        assert closed.returncode == 0, output
        published = body(env.gh_calls("pr", "edit")[-1])
        assert "test_greeting.py::test_1_greets (passed in close's run)" in published
        assert "test_other.py::test_1_other (passed in close's run)" in published
        return
    elif case == "uncommitted-edit":
        _local_close_with_pytest(env)
        item, where = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        (where / "app.py").write_text("def greet(name):\n    return 'not committed'\n", encoding="utf-8")
        expected = "Done-when proof: app.py is not committed."
    elif case == "proof-only-commit":
        _local_close_with_picker(env)
        env.commit(env.repo.path, "tests/test_greeting.py",
                   "from app import greet\n\ndef test_1_greets():\n    assert greet('Ada') == 'Hello, Ada!'\n",
                   "Add a test for greetings")
        fail_marker = (env.tmp / "fail_named_test.txt").as_posix()
        monkeypatch.setenv("FAIL_NAMED_TEST", fail_marker)
        env.commit(env.repo.path, "tests/test_other.py",
                   "import os\nfrom pathlib import Path\n\ndef test_1_fails_when_named():\n"
                   f"    assert not Path(os.environ['FAIL_NAMED_TEST']).exists()\n",
                   "Add another independent test")
        env.repo.git("push", "-q", "origin", "main")
        item, where = env.start_fix({"app.py": "def greet(name): return f'Hello, {name}!'\n"},
                                   done_when="The greeting includes a reader's name")
        _proof(env, where, _new_test_line())
        first = env.close(item)
        assert first.returncode == 0, first.stdout + first.stderr
        (env.tmp / "fail_named_test.txt").write_text("fail\n", encoding="utf-8")
        monkeypatch.setenv("FAIL_NAMED_TEST", fail_marker)
        _proof(env, where, _new_test_line("tests/test_other.py::test_1_fails_when_named"))
        second = env.close(item)
        output = second.stdout + second.stderr
        assert "Done-when proof: tests/test_other.py::test_1_fails_when_named failed in this test run." in output
        assert second.returncode == 1, output
        return
    elif case in ("javascript-name", "javascript-missing"):
        _local_close_without_test_command(env)
        files = {"app.py": "print('greeting')\n"}
        if case == "javascript-name":
            files["web/a.test.ts"] = "test('adds', () => { expect(1 + 1).toBe(2); });\n"
        item, where = env.start_fix(files)
        _proof(env, where, "- Done when: `web/a.test.ts::adds` "
                            "(new; closest none; proves addition returns the sum)")
        if case == "javascript-name":
            closed = env.close(item)
            assert closed.returncode == 0, closed.stdout + closed.stderr
            assert "Ready:" in closed.stdout
            return
        expected = "Done-when proof: web/a.test.ts::adds is not on this branch."
    elif case == "ci":
        _ci_close(env)
        skipped = ("import pytest\n\n@pytest.mark.skip(reason='not ready')\n"
                   "def test_1_greeting_is_pending():\n    pass\n")
        item, where = _start_fix_without_proof(
            env, {"app.py": "print('greeting')\n", "tests/test_greeting.py": skipped})
        _proof(env, where, _new_test_line("tests/test_greeting.py::test_1_greeting_is_pending"))
        env.repo.git("switch", "--detach", "HEAD", cwd=where)
        monkeypatch.setenv("GITHUB_HEAD_REF", "fix/tidy-readme")
        checked = env.repo.forge("test", "--change", cwd=where)
        output = checked.stdout + checked.stderr
        assert ("Done-when proof: tests/test_greeting.py::test_1_greeting_is_pending was skipped "
                "in this test run.") in output
        assert checked.returncode == 1, output
        return
    elif case == "own-ci-missing":
        _ci_close(env)
        item, where = _start_fix_without_proof(env, {"app.py": "print('greeting')\n"})
        base = env.repo.git("rev-parse", "origin/main")
        head = env.repo.git("rev-parse", "HEAD", cwd=where)
        checked = env.repo.forge("hook", "pr-check", "--base", base, "--head", head,
                                 "--branch", "fix/tidy-readme")
        output = checked.stdout + checked.stderr
        assert "Done-when proof: The fix's Done-when line names no test in the Proof list." in output
        assert checked.returncode == 1, output
        return
    elif case in ("own-ci-valid", "review-prompt-own-ci"):
        _ci_close(env)
        env.checks(GREEN + [run("build")])
        item, where = env.start_fix(_greeting_files())
        _proof(env, where, _new_test_line())
        base = env.repo.git("rev-parse", "origin/main")
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        assert closed.returncode == 0, output
        if case == "review-prompt-own-ci":
            prompt = " ".join(env.prompt().split())
            assert "Close checks only that each Done-when line names a test on the branch." in prompt
            assert "When its test run finishes" not in prompt
            return
        head = env.repo.git("rev-parse", "HEAD", cwd=where)
        checked = env.repo.forge("hook", "pr-check", "--base", base, "--head", head,
                                 "--branch", "fix/tidy-readme")
        assert checked.returncode == 0, checked.stdout + checked.stderr
        return
    elif case == "review-prompt-local":
        _local_close_with_pytest(env)
        item, where = env.start_fix(_greeting_files())
        _proof(env, where, _new_test_line())
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        assert closed.returncode == 0, output
        prompt = " ".join(env.prompt().split())
        assert "When its test run finishes, close refuses a Done-when line with no test" in prompt
        assert "Close checks only that each Done-when line names a test on the branch" not in prompt
        return
    elif case == "settings-only":
        _local_close_without_test_command(env)
        item, where = _start_fix_without_proof(env, {}, done_when="Update forge.toml setting")
        with (where / "forge.toml").open("a", encoding="utf-8") as settings:
            settings.write("\n# proof-only settings change\n")
        env.repo.git("add", "forge.toml", cwd=where)
        env.repo.git("commit", "-q", "-m", "Change the setting", cwd=where)
        closed = env.close(item)
        assert closed.returncode == 0, closed.stdout + closed.stderr
        assert "Forge's own settings or generated files only; no Done-when test needed." in (
            closed.stdout + closed.stderr)
        return
    elif case == "docs-only":
        _local_close_without_test_command(env)
        item, _ = _start_fix_without_proof(env, {"README.md": "Hello, readers.\n"})
        expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
    elif case == "docs-pytest-not-run":
        _local_close_with_pytest(env)
        for path, text in _greeting_files().items():
            env.commit(env.repo.path, path, text, "Add the greeting before this change")
        env.repo.git("push", "-q", "origin", "main")
        item, where = env.start_fix({"README.md": "Hello, readers.\n"})
        _proof(env, where, "- Done when: tests/test_greeting.py::test_1_greets "
                            "(reuse; closest tests/test_greeting.py::test_1_greets)")
        expected = "Done-when proof: tests/test_greeting.py::test_1_greets did not run in this test run."
    elif case == "closest-is-not-proof":
        _local_close_without_test_command(env)
        item, where = _start_fix_without_proof(
            env, {"app.py": "print('greeting')\n",
                  "tests/test_other.py": "def test_1_saved():\n"
                  "    saved = {'greeting': 'hello'}\n"
                  "    assert saved['greeting'] == 'hello'\n"})
        _proof(env, where, "- Done when: new; closest tests/test_other.py::test_1_saved; "
                            "proves the reader sees a greeting")
        expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
    elif case == "untracked-cache":
        _local_close_with_pytest(env, ignore_python_cache=False)
        item, where = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        first = env.close(item)
        assert first.returncode == 0, first.stdout + first.stderr
        assert "Ready:" in first.stdout
        second = env.close(item)
        assert second.returncode == 0, second.stdout + second.stderr
        assert "uncommitted changes" not in second.stdout + second.stderr
        assert "already passed on this machine" in second.stdout
        return
    elif case in ("two-app-wrong-root", "two-app-correct-root"):
        directory = "apps/two" if case == "two-app-wrong-root" else "apps/one"
        _local_close_with_pytest(env, directory=directory)
        if case == "two-app-wrong-root":
            # A custom command chooses its own app. Forge still checks the pytest results it emits.
            runner = ("import subprocess, sys\n"
                      "raise SystemExit(subprocess.call([sys.executable, '-m', 'pytest', '-q', "
                      "'-p', 'no:cacheprovider'], cwd='apps/two'))\n")
            env.commit(env.repo.path, "run_tests.py", runner, "Run the second app tests")
            config = env.repo.path / "forge.toml"
            lines = [line for line in config.read_text("utf-8").splitlines()
                     if line.partition("=")[0].strip() != "test"]
            command = f'"{Path(sys.executable).as_posix()}" run_tests.py'
            env.commit(env.repo.path, "forge.toml", "\n".join(lines)
                       + f"\ntest = {json.dumps(command)}\n", "Use the app test runner")
        app_test = ("def test_1_greeting_is_present():\n"
                    "    greeting = {'message': 'hello'}\n"
                    "    assert greeting['message'] == 'hello'\n")
        env.commit(env.repo.path, "apps/one/tests/test_greeting.py", app_test,
                   "Add the first app test")
        env.commit(env.repo.path, "apps/two/tests/test_greeting.py", app_test,
                   "Add the second app test")
        env.repo.git("push", "-q", "origin", "main")
        item, where = env.start_fix({"apps/one/app.py": "greeting = 'hello'\n"},
                                   done_when="The first app can greet its readers")
        name = "apps/one/tests/test_greeting.py::test_1_greeting_is_present"
        _proof(env, where, _new_test_line(name))
        closed = env.close(item)
        output = closed.stdout + closed.stderr
        if case == "two-app-wrong-root":
            assert (f"Done-when proof: {name} did not run in this test run.") in output
            assert closed.returncode == 1, output
            return
        assert closed.returncode == 0, output
        assert f"{name} (passed in close's run)" in body(env.gh_calls("pr", "edit")[-1])
        return
    elif case == "named-proof-keeps-related-tests":
        # The named test adds to the related tests; it must not replace the command's own test paths.
        _local_close_with_picker(env)
        env.commit(env.repo.path, "app.py", "def greet(name):\n    return f'Hello, {name}!'\n", "Add the app")
        env.commit(env.repo.path, "tests/test_welcome.py",
                   "from app import greet\n\ndef test_1_welcomes():\n    assert greet('Ada') == 'Hello, Ada!'\n",
                   "Test the welcome")
        env.repo.git("push", "-q", "origin", "main")
        item, where = env.start_fix(
            {"app.py": "def greet(name):\n    return f'Hi, {name}!'\n",
             "tests/test_greeting.py": "from app import greet\n\n"
             "def test_1_greets():\n    assert greet('Ada') == 'Hi, Ada!'\n"},
            done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        expected = "- tests/test_welcome.py::test_1_welcomes"
    elif case == "stacked-fix-own-proof":
        _ci_close(env)
        _, parent = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, parent, _new_test_line())
        tip = env.repo.git("rev-parse", "HEAD", cwd=parent)
        child = env.tmp / "fix-follow-up"
        env.repo.git("worktree", "add", "-q", "-b", "fix/follow-up", str(child), "fix/tidy-readme")
        env.commit(child, ".factory/fixes/follow-up.json",
                   json.dumps({"branch": "fix/follow-up", "status": "working", "kind": "fix",
                               "why": "Readers see a farewell", "done_when": "A farewell follows the greeting",
                               "base": tip, "stacked_on": "tidy-readme"}), "Start")
        head = env.commit(child, "farewell.py", "FAREWELL = 'Goodbye'\n", "Work")
        checked = env.repo.forge("hook", "pr-check", "--base", env.repo.git("rev-parse", "origin/main"),
                                 "--head", head, "--branch", "fix/follow-up")
        output = checked.stdout + checked.stderr
        assert "Done-when proof: The fix's Done-when line names no test in the Proof list." in output
        assert checked.returncode == 1, output
        return
    elif case == "generated-client-needs-proof":
        _local_close_without_test_command(env)
        env.commit(env.repo.path, ".gitattributes", "client/api.py linguist-generated=true\n",
                   "Mark the API client as generated")
        env.repo.git("push", "-q", "origin", "main")
        item, _ = _start_fix_without_proof(env, {"client/api.py": "def greet(name):\n    return name\n"})
        expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
    elif case == "ci-branch-of-another-repo":
        # Pull-request CI sets GITHUB_HEAD_REF for its own run; a test that runs inside it inherits
        # the name. It names no item of the repo under test, so it must not name that repo's item.
        _ci_close(env)
        _, where = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        env.repo.git("switch", "--detach", "HEAD", cwd=where)
        monkeypatch.setenv("GITHUB_HEAD_REF", "task/ELSEWHERE-1-PART")
        checked = env.repo.forge("test", "--change", cwd=where)
        assert checked.returncode == 0, checked.stdout + checked.stderr
        return
    elif case == "ci-dirty-checkout-reruns":
        # A run that leaves an untracked file, as a client's retry probe does, is not a run of
        # the committed files: the next run must not reuse the earlier pass.
        _ci_close(env)
        _, where = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        env.repo.git("switch", "--detach", "HEAD", cwd=where)
        monkeypatch.setenv("GITHUB_HEAD_REF", "fix/tidy-readme")
        monkeypatch.setenv("FORGE_GROUPS", "1")
        monkeypatch.setenv("FORGE_GROUP", "1")
        first = env.repo.forge("test", "--change", cwd=where)
        assert first.returncode == 0, first.stdout + first.stderr
        (where / "attempts.txt").write_text("1", encoding="utf-8")
        second = env.repo.forge("test", "--change", cwd=where)
        assert second.returncode == 0, second.stdout + second.stderr
        assert "already passed on this machine" not in second.stdout
        (where / "attempts.txt").unlink()
        third = env.repo.forge("test", "--change", cwd=where)
        assert "already passed on this machine" in third.stdout, third.stdout + third.stderr
        return
    elif case == "ci-clone-without-default-branch-ref":
        # A pull-request checkout has the item and its commits but no origin/main ref. The picker
        # reads the Proof list from the base it was given, not from a ref it has to find.
        _local_close_with_picker(env)
        _, where = env.start_fix(_greeting_files(), done_when="A greeting includes the reader's name")
        _proof(env, where, _new_test_line())
        base = env.repo.git("rev-parse", "origin/main")
        clone = env.tmp / "pull-request-checkout"
        env.repo.git("clone", "-q", "--no-hardlinks", str(env.repo.path), str(clone))
        env.repo.git("switch", "-q", "--detach", "origin/fix/tidy-readme", cwd=clone)
        env.repo.git("update-ref", "-d", "refs/remotes/origin/main", cwd=clone)
        env.repo.git("branch", "-q", "-D", "main", cwd=clone)
        monkeypatch.setenv("GITHUB_HEAD_REF", "fix/tidy-readme")
        checked = env.repo.forge("test", "--pytest", base, cwd=clone)
        assert checked.returncode == 0, checked.stdout + checked.stderr
        assert "passed" in checked.stdout, checked.stdout
        return
    else:  # every case belongs to this named proof contract
        pytest.fail(f"No command scenario for {case}")

    closed = env.close(item)
    output = closed.stdout + closed.stderr
    if case == "pytest-passes":
        assert closed.returncode == 0, output
        assert "tests/test_greeting.py::test_1_greets (passed in close's run)" in body(
            env.gh_calls("pr", "edit")[-1])
        return
    assert expected in output
    assert closed.returncode == 1, output
