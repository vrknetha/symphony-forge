"""CI checks named pytest proof when its test job does not run."""

import json
import sys
from pathlib import Path

import pytest

from test_close import GREEN, body, env, run  # noqa: F401
from test_done_when_tests import (
    _ci_close,
    _new_test_line,
    _proof,
    _start_fix_without_proof,
)

STORY = "FORGE-TESTQUAL-1-PROOF"
CI_DOCS_ONLY = ("CI treats this change as docs only and skips tests; "
                "only test names on the branch are checked.")


def _ci_config(env, *, forge_tests, command=True):
    _ci_close(env)
    repo = env.repo
    config = repo.path / "forge.toml"
    lines = [line for line in config.read_text("utf-8").splitlines()
             if line.partition("=")[0].strip() not in ("checks", "test", "fast_test", "test_place")]
    lines.extend(['test_place = "ci"',
                  'checks = ["build", "tests", "forge-pr-check"]' if forge_tests else
                  'checks = ["build", "forge-pr-check"]'])
    if command:
        test = f'"{Path(sys.executable).as_posix()}" -m pytest -q -p no:cacheprovider'
        lines.append(f"test = {json.dumps(test)}")
    else:
        lines.extend(['test = ""', 'fast_test = ""'])
    env.commit(repo.path, "forge.toml", "\n".join(lines) + "\n", "Set CI proof checks")
    repo.git("push", "-q", "origin", "main")


def _add_base_test(env):
    env.commit(env.repo.path, "app.py", "def greet():\n    return 'Hello'\n", "Add greeting")
    env.commit(env.repo.path, "tests/test_greeting.py",
               "from pathlib import Path\nfrom app import greet\n\ndef test_1_greets():\n"
               "    assert greet() == 'Hello'\n"
               f"    Path({str(env.tmp / 'named-pytest-ran')!r}).write_text('ran')\n",
               "Add greeting test")
    env.commit(env.repo.path, "requirements.txt", "pytest-split==0.11.0\n", "Use pytest groups")
    env.repo.git("push", "-q", "origin", "main")


@pytest.mark.parametrize("case", [
    "docs-missing-proof", "docs-name-only", "docs-name-missing", "docs-check", "record-only",
    "docs-only-custom-ci", "settings-and-docs", "settings-and-docs-one-group",
    "settings-and-docs-always", "no-command",
])
@pytest.mark.platform
def test_3_ci_skips_do_not_hide_named_pytest_proof(env, monkeypatch, case):
    # Test-audit:
    # 1. Docs-only CI checks names and reports that no run is proved, including settings changes.
    # 2. The check can disagree with jobs, including a matrix reduced to one group,
    #    or claim outcomes after those jobs skipped.
    # 3. test_done_when_tests::test_2 covers close's normal test run, not the separate
    #    pr-check head-data path or forge test --change's no-command return. This extends
    #    that contract at each affected command boundary; record-only reuse stays covered by
    #    test_record_only_failed_results::test_6.
    # 4. These invoke Forge commands against real commit data; no production seam is needed.
    if case == "no-command":
        _ci_config(env, forge_tests=True, command=False)
        item, where = _start_fix_without_proof(
            env,
            {"app.py": "def greet(): return 'Hello'\n",
             "tests/test_greeting.py": "from app import greet\n\n"
             "def test_1_greets():\n    assert greet() == 'Hello'\n"},
            done_when="The greeting is available",
        )
        _proof(env, where, _new_test_line())
        env.repo.git("switch", "--detach", "HEAD", cwd=where)
        monkeypatch.setenv("GITHUB_HEAD_REF", "fix/tidy-readme")
        checked = env.repo.forge("test", "--change", cwd=where)
        output = checked.stdout + checked.stderr
        assert "Done-when proof: tests/test_greeting.py::test_1_greets did not run in this test run." in output
        assert checked.returncode == 1, output
        return

    forge_tests = case != "docs-only-custom-ci"
    _ci_config(env, forge_tests=forge_tests)
    _add_base_test(env)
    if case == "record-only":
        item, where = _start_fix_without_proof(
            env,
            {"app.py": "def greet(): return 'Hello'\n",
             "tests/test_greeting.py": "from app import greet\n\n"
             "def test_1_greets():\n    assert greet() == 'Hello'\n"},
            done_when="The greeting is available",
        )
        _proof(env, where, _new_test_line())
        state_path = ".factory/fixes/tidy-readme.json"
        state = json.loads((where / state_path).read_text("utf-8"))
        state["round"] = 2
        env.commit(where, state_path, json.dumps(state), "Save close records")
        expected = ""
    elif case.startswith("settings-and-docs"):
        item, where = _start_fix_without_proof(
            env, {"README.md": "Hello, readers.\n"},
            done_when="The readme opens with a greeting and forge.toml sets always_test and groups",
        )
        config = where / "forge.toml"
        always = '["tests/test_greeting.py::test_1_greets"]' if case.endswith("-always") else "[]"
        env.commit(where, "forge.toml", config.read_text("utf-8") +
                   f"always_test = {always}\ngroups = 2\n", "Configure grouped change tests")
        _proof(env, where, _new_test_line())
        expected = ""
    else:
        item, where = _start_fix_without_proof(
            env, {"README.md": "Hello, readers.\n"},
        )
        if case == "docs-missing-proof":
            expected = "Done-when proof: The fix's Done-when line names no test in the Proof list."
        elif case in {"docs-name-only", "docs-name-missing"}:
            name = "tests/test_missing.py::test_1_greets" if case == "docs-name-missing" else "tests/test_greeting.py::test_1_greets"
            _proof(env, where, _new_test_line(name))
            expected = f"Done-when proof: {name} is not on this branch." if case == "docs-name-missing" else ""
        elif case == "docs-check":
            _proof(env, where, "- Done when: check: documentation is reviewed")
            expected = ""
        else:
            _proof(env, where, _new_test_line())
            expected = ""

    skipped = forge_tests and case in {
        "docs-name-only", "docs-check", "settings-and-docs", "settings-and-docs-one-group"}
    if case.startswith("settings-and-docs"):
        env.repo.git("switch", "--detach", "HEAD", cwd=where)
        with monkeypatch.context() as ci:
            ci.setenv("GITHUB_HEAD_REF", "fix/tidy-readme")
            groups = 1 if case.endswith("-one-group") else 2
            ci.setenv("FORGE_GROUPS", str(groups))
            for group in range(1, groups + 1):
                ci.setenv("FORGE_GROUP", str(group))
                tested = env.repo.forge("test", "--change", cwd=where)
                output = tested.stdout + tested.stderr
                assert tested.returncode == 0, output
                assert ("docs only: tests skipped" in output) == (not case.endswith("-always")), output
        env.repo.git("switch", "fix/tidy-readme", cwd=where)
        assert (env.tmp / "named-pytest-ran").exists() == case.endswith("-always")

    if not expected:
        env.checks(GREEN + [run("build")] + ([run("tests")] if forge_tests else []))
        closed = env.close(item)
        assert closed.returncode == 0, closed.stdout + closed.stderr
        if skipped:
            prompt = " ".join(env.prompt().split())
            assert CI_DOCS_ONLY in prompt
            assert "When its test run finishes, close refuses" not in prompt
            published = body(env.gh_calls("pr", "edit")[-1])
            assert CI_DOCS_ONLY in published
            assert "passed in close's run" not in published

    base = env.repo.git("rev-parse", "origin/main")
    head = env.repo.git("rev-parse", "HEAD", cwd=where)
    checked = env.repo.forge("hook", "pr-check", "--base", base, "--head", head,
                             "--branch", "fix/tidy-readme")
    output = checked.stdout + checked.stderr
    if expected:
        assert expected in output
        assert checked.returncode == 1, output
    else:
        assert checked.returncode == 0, output
        assert output.splitlines().count(f"Done-when proof: {CI_DOCS_ONLY}") == int(skipped), output
        assert "did not run in this test run" not in output
