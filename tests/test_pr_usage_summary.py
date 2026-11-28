"""Pull request 'How it went' shows builder model and effort, tokens, change size and cost status.

Test-audit: protects the end-to-end PR 'How it went' usage summary contract through real Forge
commands (`forge work`, `forge read`, `forge close`, `forge board --json`) with external provider
CLIs faked only at their process edge. A change to run recording, token aggregation, PR history
refresh, diff size calculation, exclusions, or PR rendering could omit the build model/effort,
corrupt round lines, place lines outside How it went, double-count tokens on refresh, drop review
retries or plan reads, misclassify change size or boundaries, or leak token/cost fields onto the
board. Closest existing tests are `tests/test_effort_records.py` and
`tests/test_item_time_history.py`; no existing test asserts these PR lines. No production seam is
added.
"""
import json
import os
import re
import sys

import pytest

from conftest import ROOT, _install
from test_close import (CLEAN, FAILED, GREEN, STORY_DOC, approve_story, blocked, body, env,  # noqa: F401
                        finding, report, run)
from test_item_time_history import row
from test_story import worktree

STORY = "FORGE-PRUSAGE-1"
pytestmark = pytest.mark.platform

CODEX_EDGE_STUB = '''#!{python}
import json, os, pathlib, runpy, sys

args = sys.argv[1:]
if "exec" in args:
    print(json.dumps({{"type": "thread.started", "thread_id": "rev-thread-1"}}), flush=True)
    if not os.environ.get("STUB_REVIEW_NO_USAGE"):
        print(json.dumps({{
            "type": "turn.completed",
            "usage": {{"input_tokens": 5000, "cached_input_tokens": 2000, "output_tokens": 400}},
        }}), flush=True)
    sys.exit(0)
runpy.run_path(str(pathlib.Path(__file__).resolve().with_name("codex-app-server")), run_name="__main__")
'''


def _configure_codex(env, tmp_path, monkeypatch):
    """Install external-edge Codex stub for both app-server (work/read) and exec (review)."""
    _install(env.repo.bin, "codex-app-server", (ROOT / "tests/stubs/codex-app-server").read_text("utf-8"))
    _install(env.repo.bin, "codex", CODEX_EDGE_STUB.format(python=sys.executable))
    program = env.repo.bin / ("codex.cmd" if os.name == "nt" else "codex")
    monkeypatch.setenv("CODEX_BIN", str(program))
    home = tmp_path / "codex-home"
    home.mkdir(exist_ok=True)
    (home / "config.toml").write_text(
        f'[projects.{json.dumps(str(env.repo.path))}]\ntrust_level = "trusted"\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("CODEX_THREAD_ID", "coordinator")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    version = env.repo.forge("--version").stdout.split()[-1]
    env.repo.write(
        "forge.toml",
        f'version = "{version}"\n'
        'tools = "codex"\n'
        'workers = "codex"\n'
        'test_place = "ci"\n'
        'checks = ["tests", "forge-pr-check"]\n'
        'interfaces = ["**/routes/**"]\n'
        'models.build = { model = "gpt-6.1-sol", effort = "low" }\n'
        'models.fix = { model = "gpt-6.1-sol", effort = "low" }\n'
        'models.lite = { model = "gpt-6.1-sol", effort = "low" }\n'
        'models.grill.codex = { model = "gpt-6.1-terra", effort = "max" }\n'
        'models.review.codex = { model = "gpt-6.1-terra", effort = "max" }\n',
    )
    env.repo.git("add", "forge.toml")
    env.repo.git("commit", "-q", "-m", "Configure Codex builder and reviewer")
    env.repo.git("push", "-q", "origin", "main")


def _pr_body(env):
    calls = [c for c in env.gh_calls("pr") if "--body-file" in c]
    return body(calls[-1])


def _how_it_went(pr_body: str) -> str:
    managed = re.search(r"<!-- forge:begin -->(.*?)<!-- forge:end -->", pr_body, re.S)
    assert managed, "PR body missing managed forge block"
    section = re.search(r"## How it went\n\n(.*?)\n<!-- forge:history ", managed[1], re.S)
    assert section, "PR body missing '## How it went' section"
    return section[1]


def _new_fix(env, slug="usage-fix", changes=None):
    env.gh.respond("pr", "list", stdout="[]")
    fix, where = env.start(slug, f"fix/{slug}", f".factory/fixes/{slug}.json",
                           {"why": "Test usage", "done_when": "Usage is shown"},
                           changes=changes or {"feature.py": "print('hello')\n"})
    env.checks(GREEN)
    return fix, where


def test_1_pr_how_it_went_shows_build_model_and_effort(env, tmp_path, monkeypatch):
    _configure_codex(env, tmp_path, monkeypatch)
    fix, where = _new_fix(env, "build-model")
    worked = env.repo.forge("work", fix)
    assert worked.returncode == 0, worked.stdout + worked.stderr
    env.commit(where, "feature.py", "print('built')\n", "Implement fix\n\nProof list:\n- Done when: check: synthetic fixture")
    env.reviews({"exit": 0, "report": report(finding("P2", "Clarify the usage label", "feature.py"))})
    closed = env.close(fix)
    assert closed.returncode == 0, closed.stdout + closed.stderr

    section = _how_it_went(_pr_body(env))
    elapsed = r"(?:unknown|\d+ (?:seconds?|minutes?|hours?))"
    assert re.search(
        rf"^working: {elapsed}; waiting: {elapsed}; unmeasured time: {elapsed}\n\n"
        rf"building: {elapsed}; own tests: {elapsed}; reviewing: {elapsed}; fixing findings: {elapsed}; "
        rf"waiting for CI: {elapsed}; waiting in line: {elapsed}; waiting for the owner: {elapsed}\n\n"
        rf"Round 1: built at low; building completed \({elapsed}\); review clean \({elapsed}\); "
        rf"CI passed \({elapsed}\); (?:in line {elapsed}; )?"
        r"waiting for the owner \(ongoing\); findings: 1 new, 0 repeated — P2 Clarify the usage label \(feature\.py\)\n\n"
        r"Build: gpt-6\.1-sol at low$", section, re.M
    ), section
    assert sum(line.startswith("Round 1: ") for line in section.splitlines()) == 1, section
    assert sum(line.startswith("Build: ") for line in section.splitlines()) == 1, section


def test_2_pr_how_it_went_shows_token_totals_coverage_and_shortened_history(env, tmp_path, monkeypatch):
    _configure_codex(env, tmp_path, monkeypatch)

    # Case A: 3 real build runs (2 with tokens, 1 without), review retry with tokens,
    # and a real PR refresh through gh pr list -> gh pr edit without double-counting.
    fix, where = _new_fix(env, "token-coverage")
    # Build run 1: low effort, reports 1,200 / 1,000 / 300.
    assert env.repo.forge("work", fix).returncode == 0
    env.commit(where, "feature.py", "print('v1')\n", "Round 1\n\nProof list:\n- Done when: check: synthetic fixture")
    # Close 1: Autoreview fails attempt 1 after running codex exec, then passes attempt 2; CI fails so effort rises.
    env.reviews(FAILED, CLEAN)
    env.checks([run("tests", "failure"), run("forge-pr-check")])
    env.gh.respond("pr", "checks", stdout=json.dumps([
        {"name": "tests", "bucket": "fail", "link": "https://github.com/acme/shop/actions/runs/1/job/1"},
        {"name": "forge-pr-check", "bucket": "pass", "link": "https://github.com/acme/shop/actions/runs/1/job/2"},
    ]))
    env.gh.respond("run", "view", stdout="failed check output\n")
    first_close = env.close(fix)
    assert first_close.returncode == 1, first_close.stdout + first_close.stderr
    env.open_pr(_pr_body(env))

    # Build run 2: high effort, reports 1,200 / 1,000 / 300, pauses with a question.
    monkeypatch.setenv("STUB_CODEX_TEXT", "Question: Keep the existing fallback?")
    assert env.repo.forge("work", fix).returncode == 0
    monkeypatch.delenv("STUB_CODEX_TEXT")

    # Build run 3: high effort, reports NO tokens.
    monkeypatch.setenv("STUB_CODEX_NO_USAGE", "1")
    assert env.repo.forge("work", fix, "--note", "Yes, keep it.").returncode == 0
    monkeypatch.delenv("STUB_CODEX_NO_USAGE")

    env.commit(where, "feature.py", "print('v2')\n", "Round 2\n\nProof list:\n- Done when: check: synthetic fixture")
    env.checks(GREEN)
    env.reviews(CLEAN)
    second_close = env.close(fix)
    assert second_close.returncode == 0, second_close.stdout + second_close.stderr
    ready_body = _pr_body(env)
    ready_section = _how_it_went(ready_body)
    assert "Build: gpt-6.1-sol at low, gpt-6.1-sol at high" in ready_section
    assert "Build tokens: input 2,400 (cached 2,000), output 600; 2 of 3 runs reported tokens" in ready_section
    # 2 review runs from Close 1 (retry + pass) + 1 review run from Close 2 = 3 runs x (5000, 2000, 400).
    assert "Review tokens: input 15,000 (cached 6,000), output 1,200" in ready_section

    # Real PR refresh: return ready_body from gh pr list and close again.
    edits_before = len(env.gh_calls("pr", "edit"))
    env.open_pr(ready_body)
    third_close = env.close(fix)
    assert third_close.returncode == 0, third_close.stdout + third_close.stderr
    assert len(env.gh_calls("pr", "edit")) > edits_before
    refreshed_body = _pr_body(env)
    refreshed_section = _how_it_went(refreshed_body)
    assert "Build tokens: input 2,400 (cached 2,000), output 600; 2 of 3 runs reported tokens" in refreshed_section
    assert "Review tokens: input 15,000 (cached 6,000), output 1,200" in refreshed_section

    # Case B: all runs report no tokens -> "no tokens recorded" and no zero totals.
    fix_none, where_none = _new_fix(env, "no-tokens")
    monkeypatch.setenv("STUB_CODEX_NO_USAGE", "1")
    monkeypatch.setenv("STUB_REVIEW_NO_USAGE", "1")
    assert env.repo.forge("work", fix_none).returncode == 0
    env.commit(where_none, "feature.py", "print('none')\n", "Work\n\nProof list:\n- Done when: check: synthetic fixture")
    env.reviews(CLEAN)
    assert env.close(fix_none).returncode == 0
    monkeypatch.delenv("STUB_CODEX_NO_USAGE")
    monkeypatch.delenv("STUB_REVIEW_NO_USAGE")
    none_section = _how_it_went(_pr_body(env))
    assert "Build tokens: no tokens recorded" in none_section
    assert "Review tokens: no tokens recorded" in none_section
    assert "input 0" not in none_section

    # Case C: shortened history through real compaction adds the notice sentence inside How it went.
    env.open_pr(refreshed_body)
    env.commit(where, "feature.py", "print('v3')\n", "Round 3\n\nProof list:\n- Done when: check: synthetic fixture")
    many = [finding("P1", "Main blocker", "feature.py"),
            *(finding("P2", f"Detailed note {i} " + "x" * 160, "feature.py") for i in range(110))]
    env.reviews(blocked(*many))
    blocked_close = env.close(fix)
    assert blocked_close.returncode == 1, blocked_close.stdout + blocked_close.stderr
    compact_section = _how_it_went(_pr_body(env))
    assert "Earlier history was shortened; its models and tokens are not shown." in compact_section

    # Case D: an existing story PR gets its own real plan read when close retries the history rebuild.
    with monkeypatch.context() as reader:
        reader.delenv("CODEX_THREAD_ID", raising=False)
        reader.setenv("CLAUDECODE", "1")
        reader.setenv("STUB_CODEX_TEXT", "No findings.")
        approve_story(env.repo, STORY_DOC)
    story_path = worktree(env.repo, "story/SHOP")
    env.repo.git("push", "-q", "origin", "HEAD:refs/pull/8/head", cwd=story_path)
    env.gh.respond("pr", "list", "--state", "open", stdout=json.dumps([
        {"number": 8, "state": "OPEN", "headRefName": "story/SHOP", "body": ""},
    ]))
    env.gh.respond("pr", "list", "--head", stdout="[]")
    env.gh.respond("api", "graphql", "--paginate", stdout="")
    (env.repo.path / ".git/forge/backfill-pending").touch()
    env.reviews(CLEAN)
    task, _ = env.start_task()
    task_close = env.close(task)
    assert task_close.returncode == 0, task_close.stdout + task_close.stderr
    story_edits = env.gh_calls("pr", "edit", "8")
    assert story_edits, task_close.stdout + task_close.stderr
    read_lines = [line for line in _how_it_went(body(story_edits[-1])).splitlines()
                  if line.startswith("Plan read tokens:")]
    assert read_lines == ["Plan read tokens: input 1,200 (cached 1,000), output 300"]
    task_pr = env.gh_calls("pr", "create", path="task/SHOP-T1")
    assert task_pr, task_close.stdout + task_close.stderr
    assert "Plan read tokens:" not in _how_it_went(body(task_pr[-1]))


def test_3_pr_how_it_went_shows_change_size_for_fix_and_task(env):
    # Pre-seed an existing product file (for deletions) and .gitattributes (for generated exclusion) on main.
    env.repo.write("existing.py", "".join(f"old_{i} = {i}\n" for i in range(15)))
    env.repo.write(".gitattributes", "gen.lock linguist-generated=true\n")
    env.repo.git("add", "existing.py", ".gitattributes")
    env.repo.git("commit", "-q", "-m", "Add baseline file and generated attribute")
    env.repo.git("push", "-q", "origin", "main")

    # S upper boundary (100 lines) across 3 product files (10 removed + 40 added + 50 added),
    # while ignoring test, doc, and generated files in the same change.
    fix_s, _ = _new_fix(env, "size-s", {
        "existing.py": "".join(f"old_{i} = {i}\n" for i in range(5)),  # 10 lines removed
        "part_a.py": "".join(f"a_{i} = {i}\n" for i in range(40)),     # 40 lines added
        "part_b.py": "".join(f"b_{i} = {i}\n" for i in range(50)),     # 50 lines added
        "tests/test_extra.py": "".join(f"t_{i} = {i}\n" for i in range(25)),
        "docs/notes.md": "# Notes\n" * 15,
        "gen.lock": "".join(f"pkg-{i}=1.0\n" for i in range(50)),
    })
    env.reviews(CLEAN)
    assert env.close(fix_s).returncode == 0
    assert "Size: S (100 lines in 3 files)" in _how_it_went(_pr_body(env))

    # Only a test file and a generated file -> no product lines.
    fix_test_only, _ = _new_fix(env, "size-test-only", {
        "tests/test_only.py": "def test_ok():\n    assert True\n",
        "gen.lock": "pkg-1=2.0\n",
    })
    env.reviews(CLEAN)
    assert env.close(fix_test_only).returncode == 0
    assert "Size: no product lines" in _how_it_went(_pr_body(env))

    # Only docs -> no product lines.
    fix_doc, _ = _new_fix(env, "size-doc", {"docs/guide.md": "# Guide\nSome docs.\n"})
    env.reviews(CLEAN)
    assert env.close(fix_doc).returncode == 0
    assert "Size: no product lines" in _how_it_went(_pr_body(env))

    # M lower boundary: 101 product lines in 1 file.
    fix_m_low, _ = _new_fix(env, "size-m-low", {"feature.py": "".join(f"m{i} = {i}\n" for i in range(101))})
    env.reviews(CLEAN)
    assert env.close(fix_m_low).returncode == 0
    assert "Size: M (101 lines in 1 file)" in _how_it_went(_pr_body(env))

    # M upper boundary: 400 product lines in 2 files.
    fix_m_high, _ = _new_fix(env, "size-m-high", {
        "feature_a.py": "".join(f"a{i} = {i}\n" for i in range(200)),
        "feature_b.py": "".join(f"b{i} = {i}\n" for i in range(200)),
    })
    env.reviews(CLEAN)
    assert env.close(fix_m_high).returncode == 0
    assert "Size: M (400 lines in 2 files)" in _how_it_went(_pr_body(env))

    # L lower boundary: 401 product lines.
    fix_l, _ = _new_fix(env, "size-l", {"feature.py": "".join(f"l{i} = {i}\n" for i in range(401))})
    env.reviews(CLEAN)
    assert env.close(fix_l).returncode == 0
    assert "Size: L (401 lines in 1 file)" in _how_it_went(_pr_body(env))

    # Blocked close has no ready record -> no Size line.
    fix_blocked, _ = _new_fix(env, "size-blocked")
    env.reviews(blocked(finding("P0", "Crash on load", "feature.py")))
    assert env.close(fix_blocked).returncode == 1
    assert "Size:" not in _how_it_went(_pr_body(env))

    # Task item shows the same Size line.
    env.gh.respond("pr", "list", stdout="[]")
    task_item, _ = env.start_task(changes={"feature.py": "".join(f"t{i} = {i}\n" for i in range(12))})
    env.checks(GREEN)
    env.reviews(CLEAN)
    assert env.close(task_item).returncode == 0
    assert "Size: S (12 lines in 1 file)" in _how_it_went(_pr_body(env))


def test_4_pr_how_it_went_shows_cost_unavailable_and_board_unchanged(env):
    fix, _ = _new_fix(env, "cost-check")
    env.reviews(CLEAN)
    assert env.close(fix).returncode == 0
    section = _how_it_went(_pr_body(env))
    assert "Cost: unavailable" in section
    assert not re.search(r"\$\d", section)
    item_row = row(env.repo, fix)
    for forbidden in ("cost", "tokens", "input_tokens", "output_tokens", "build_tokens", "size"):
        assert forbidden not in item_row
