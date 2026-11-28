"""Pull request 'How it went' shows builder model and effort, tokens, change size and cost status.

Test-audit: protects the end-to-end PR 'How it went' usage summary contract through `forge close`.
A change to event reading, token aggregation, diff size calculation or PR rendering could omit the
build model/effort, double-count tokens, hide partial token coverage, misclassify change size, or
leak cost/token fields onto the board. No existing test asserts these PR lines; closest are
`tests/test_effort_records.py` and `tests/test_item_time_history.py`. No production seam is added.
"""
import json
import re

from test_close import CLEAN, GREEN, blocked, body, env, finding, report  # noqa: F401
from test_item_time_history import row

STORY = "FORGE-PRUSAGE-1"


def _append_events(repo, events):
    path = repo.path / ".git/forge/events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def _pr_body(env):
    calls = [c for c in env.gh_calls("pr") if "--body-file" in c]
    return body(calls[-1])


def _new_fix(env, slug="usage-fix", changes=None):
    fix, where = env.start(slug, f"fix/{slug}", f".factory/fixes/{slug}.json",
                           {"why": "Test usage", "done_when": "Usage is shown"},
                           changes=changes or {"feature.py": "print('hello')\n"})
    env.checks(GREEN)
    return fix, where


def test_1_pr_how_it_went_shows_build_model_and_effort(env):
    fix, _ = _new_fix(env, "build-model")
    _append_events(env.repo, [
        {"id": "run-1", "item": fix, "event": "run start", "kind": "worker",
         "round": 1, "at": "2026-11-28T01:00:00Z", "model": "gpt-6.2-sol", "effort": "low"},
        {"id": "end-1", "run_id": "run-1", "item": fix, "event": "run end", "kind": "worker",
         "round": 1, "at": "2026-11-28T01:01:00Z", "model": "gpt-6.2-sol", "effort": "low",
         "input_tokens": 12000, "cached_input_tokens": 8000, "output_tokens": 500},
    ])
    env.reviews(CLEAN)
    closed = env.close(fix)
    assert closed.returncode == 0, closed.stdout + closed.stderr
    text = _pr_body(env)
    assert "Build: gpt-6.2-sol at low" in text
    assert "built at low" in text


def test_2_pr_how_it_went_shows_token_totals_coverage_and_shortened_history(env):
    # Case A: 2 of 3 build runs reported tokens, plus a review run with tokens, and repeated close.
    fix, where = _new_fix(env, "token-coverage")
    _append_events(env.repo, [
        {"id": "b1", "item": fix, "event": "run start", "kind": "worker",
         "round": 1, "at": "2026-11-28T01:00:00Z", "model": "gpt-6.2-sol", "effort": "low"},
        {"id": "b1-end", "run_id": "b1", "item": fix, "event": "run end", "kind": "worker",
         "round": 1, "at": "2026-11-28T01:01:00Z", "model": "gpt-6.2-sol", "effort": "low",
         "input_tokens": 100000, "cached_input_tokens": 75000, "output_tokens": 3000},
        {"id": "b2", "item": fix, "event": "run start", "kind": "worker",
         "round": 2, "at": "2026-11-28T01:02:00Z", "model": "gpt-6.2-sol", "effort": "high"},
        {"id": "b2-end", "run_id": "b2", "item": fix, "event": "run end", "kind": "worker",
         "round": 2, "at": "2026-11-28T01:03:00Z", "model": "gpt-6.2-sol", "effort": "high",
         "input_tokens": 20000, "cached_input_tokens": 15000, "output_tokens": 1000},
        {"id": "b3", "item": fix, "event": "run start", "kind": "worker",
         "round": 3, "at": "2026-11-28T01:04:00Z", "model": "gpt-6.2-sol", "effort": "high"},
        {"id": "b3-end", "run_id": "b3", "item": fix, "event": "run end", "kind": "worker",
         "round": 3, "at": "2026-11-28T01:05:00Z", "model": "gpt-6.2-sol", "effort": "high"},
        {"id": "r1", "item": fix, "event": "run start", "kind": "review",
         "round": 3, "at": "2026-11-28T01:06:00Z", "model": "gpt-6.1-terra", "effort": "max"},
        {"id": "r1-end", "run_id": "r1", "item": fix, "event": "run end", "kind": "review",
         "round": 3, "at": "2026-11-28T01:07:00Z", "model": "gpt-6.1-terra", "effort": "max",
         "input_tokens": 5000, "cached_input_tokens": 2000, "output_tokens": 400},
    ])
    env.reviews(CLEAN)
    assert env.close(fix).returncode == 0
    first_body = _pr_body(env)
    assert "Build: gpt-6.2-sol at low, gpt-6.2-sol at high" in first_body
    assert "Build tokens: input 120,000 (cached 90,000), output 4,000; 2 of 3 runs reported tokens" in first_body
    assert "Review tokens: input 5,000 (cached 2,000), output 400" in first_body
    # A repeated close does not double-count any run.
    assert env.close(fix).returncode == 0
    second_body = _pr_body(env)
    assert "Build tokens: input 120,000 (cached 90,000), output 4,000; 2 of 3 runs reported tokens" in second_body
    assert "Review tokens: input 5,000 (cached 2,000), output 400" in second_body

    # Case B: no build runs reported tokens -> "no tokens recorded" and no zero totals.
    fix_none, _ = _new_fix(env, "no-tokens")
    _append_events(env.repo, [
        {"id": "nb1", "item": fix_none, "event": "run start", "kind": "worker",
         "round": 1, "at": "2026-11-28T02:00:00Z", "model": "claude-sonnet-5-5", "effort": "low"},
        {"id": "nb1-end", "run_id": "nb1", "item": fix_none, "event": "run end", "kind": "worker",
         "round": 1, "at": "2026-11-28T02:01:00Z"},
    ])
    env.reviews(CLEAN)
    assert env.close(fix_none).returncode == 0
    none_body = _pr_body(env)
    assert "Build: claude-sonnet-5-5 at low requested" in none_body
    assert "Build tokens: no tokens recorded" in none_body
    assert "Build tokens: input 0" not in none_body

    # Case C: shortened history adds the notice sentence.
    filler = [
        {"id": f"fill-{i}", "item": fix, "event": "work phase", "phase": "building",
         "round": i, "at": f"2026-11-28T03:{i // 60:02d}:{i % 60:02d}Z",
         "note": "x" * 200}
        for i in range(1, 160)
    ]
    _append_events(env.repo, filler)
    env.commit(where, "app.py", "print('hello 2')\n", "Trigger refresh")
    env.reviews(CLEAN)
    assert env.close(fix).returncode == 0
    assert "Earlier history was shortened; its models and tokens are not shown." in _pr_body(env)


def test_3_pr_how_it_went_shows_change_size_for_fix_and_task(env):
    # S: 30 product lines in 1 file.
    fix_s, _ = _new_fix(env, "size-s", {"feature.py": "".join(f"x{i} = {i}\n" for i in range(30))})
    env.reviews(CLEAN)
    assert env.close(fix_s).returncode == 0
    assert "Size: S (30 lines in 1 file)" in _pr_body(env)

    # Only docs / tests -> no product lines.
    fix_doc, _ = _new_fix(env, "size-doc", {"docs/guide.md": "# Guide\nSome docs.\n"})
    env.reviews(CLEAN)
    assert env.close(fix_doc).returncode == 0
    assert "Size: no product lines" in _pr_body(env)

    # M: 101 product lines.
    fix_m, _ = _new_fix(env, "size-m", {"feature.py": "".join(f"m{i} = {i}\n" for i in range(101))})
    env.reviews(CLEAN)
    assert env.close(fix_m).returncode == 0
    assert "Size: M (101 lines in 1 file)" in _pr_body(env)

    # L: 401 product lines.
    fix_l, _ = _new_fix(env, "size-l", {"feature.py": "".join(f"l{i} = {i}\n" for i in range(401))})
    env.reviews(CLEAN)
    assert env.close(fix_l).returncode == 0
    assert "Size: L (401 lines in 1 file)" in _pr_body(env)

    # Blocked close has no ready record -> no Size line.
    fix_blocked, _ = _new_fix(env, "size-blocked")
    env.reviews(blocked(finding("P0", "Crash on load", "feature.py")))
    assert env.close(fix_blocked).returncode == 1
    assert "Size:" not in _pr_body(env)

    # Task item shows the same Size line.
    task_item, _ = env.start_task(changes={"feature.py": "".join(f"t{i} = {i}\n" for i in range(12))})
    env.checks(GREEN)
    env.reviews(CLEAN)
    assert env.close(task_item).returncode == 0
    assert "Size: S (12 lines in 1 file)" in _pr_body(env)


def test_4_pr_how_it_went_shows_cost_unavailable_and_board_unchanged(env):
    fix, _ = _new_fix(env, "cost-check")
    env.reviews(CLEAN)
    assert env.close(fix).returncode == 0
    text = _pr_body(env)
    assert "Cost: unavailable" in text
    assert not re.search(r"\$\d", text)
    item_row = row(env.repo, fix)
    for forbidden in ("cost", "tokens", "input_tokens", "output_tokens", "build_tokens", "size"):
        assert forbidden not in item_row
