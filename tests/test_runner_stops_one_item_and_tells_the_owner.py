from __future__ import annotations

STORY = "FORGE-RUNNER-1"
# Done-when 3 & 4: an item that needs the owner stops alone while other ready work keeps going,
# the owner gets one desktop notice with its question (worker question, review-limit question, or
# pull request link) and one summary notice at the end (excluding resolved items), Windows sends no
# pop-up, and repeated wakes or a restart send no duplicate notice and no summary when idle.

import json
import os
import sys
from pathlib import Path

import pytest

from conftest import _install
from test_close import CLEAN, env, finding, report  # noqa: F401
from test_land import _agent, land  # noqa: F401
from test_runner_moves_approved_work_to_merge import (  # noqa: F401
    _human_merge,
    _install_multi_gh,
    _runner_exited,
    _runner_log,
    _wait_for,
    runner_cleanup,
)
from test_worker import calls

NOTIFIER_STUB = """#!{python}
import json, pathlib, sys
log = pathlib.Path({log!r})
with log.open("a", encoding="utf-8") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
"""


def _install_notifier(land) -> Path:
    log = land.repo.bin / "notices.jsonl"
    if os.name != "nt":
        name = "osascript" if sys.platform == "darwin" else "notify-send"
        _install(land.repo.bin, name, NOTIFIER_STUB.format(python=sys.executable, log=str(log)))
    return log


def _notices(log: Path) -> list[list[str]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.platform
@pytest.mark.parametrize("case", [
    "worker_and_size_questions",
    "review_limit_and_resolved_summary",
])
def test_3_4_runner_stops_one_item_and_tells_the_owner(case, land, tmp_path, monkeypatch, request):
    if case == "review_limit_and_resolved_summary":
        request.getfixturevalue("fake_clock")
        _install_multi_gh(land, tmp_path)
        _agent(land, 'task_review_rounds = 1\n')
        notice_log = _install_notifier(land)
        monkeypatch.setenv("FORGE_RUNNER_TICK", "2")
        monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

        # Session 1: human-fix reaches ready for human merge and sends one notice with its PR link.
        land.reviews(CLEAN)
        s1 = land.repo.forge("fix", "start", "Human fix", "--done", "Human fix done", "--slug", "human-fix")
        assert s1.returncode == 0, s1.stderr
        _wait_for(lambda: "human-fix is ready; a human merges" in _runner_log(land), timeout=45.0)
        _human_merge(land, tmp_path, "fix/human-fix")
        _wait_for(lambda: not (tmp_path / "repo-fix-human-fix").exists() and _runner_exited(tmp_path), timeout=45.0)

        sent_after_first = _notices(notice_log)
        if os.name == "nt":
            assert sent_after_first == []
        else:
            human_notices = [a for a in sent_after_first if any("human-fix" in x for x in a)
                             and not any("Forge runner done" in x for x in a)]
            assert len(human_notices) == 1, sent_after_first
            assert any("https://" in x for x in human_notices[0]), human_notices[0]

        # Session 2: review-fix hits task_review_rounds = 1 with a blocking P1 finding;
        # summary must include review-fix and exclude already-resolved human-fix.
        p1 = finding("P1", "Missing error check on empty input", file="work-1.txt")
        land.reviews({"exit": 0, "report": report(p1)})
        s2 = land.repo.forge("fix", "start", "Review fix", "--done", "Review fix done", "--slug", "review-fix")
        assert s2.returncode == 0, s2.stderr
        _wait_for(lambda: "Stopped: review-fix needs you." in _runner_log(land) and _runner_exited(tmp_path), timeout=45.0)

        sent_after_review = _notices(notice_log)
        if os.name == "nt":
            assert sent_after_review == []
        else:
            review_notices = [a for a in sent_after_review if any("review-fix" in x for x in a)
                              and not any("Forge runner done" in x for x in a)]
            assert len(review_notices) == 1, sent_after_review
            body = " ".join(review_notices[0])
            assert "Missing error check on empty input" in body, body
            assert "more" in body.lower() and "split" in body.lower() and "accept" in body.lower(), body
            summaries = [a for a in sent_after_review if any("Forge runner done" in x for x in a)]
            last_summary = " ".join(summaries[-1])
            assert "review-fix" in last_summary, last_summary
            assert "human-fix" not in last_summary, last_summary
        return

    _install_multi_gh(land, tmp_path)
    _agent(land)
    notice_log = _install_notifier(land)
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.delenv("FORGE_NO_RUNNER", raising=False)

    # Make the builder ask a Question: when building ask-fix, and ask for allow-large on size-fix.
    module = land.repo.bin / "claude_agent_sdk" / "__init__.py"
    original = module.read_text(encoding="utf-8")
    patch = (
        '        if "ask-fix" in os.getcwd():\n'
        '            yield ResultMessage(result="Question: Should ask-fix keep the old default?", session_id="s1")\n'
        '            return\n'
        '        if "size-fix" in os.getcwd():\n'
        '            yield ResultMessage(result="Question: Allow this fix to change these code files: a.py, b.py, c.py, d.py, e.py, f.py?\\nThe coordinator can record the choice with forge fix allow-large \\"reason\\".", session_id="s1")\n'
        '            return\n'
        '        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n'
    )
    assert '        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n' in original
    module.write_text(
        original.replace('        Path(f"work-{done + 1}.txt").write_text("worked\\n", encoding="utf-8")\n', patch),
        encoding="utf-8",
    )

    s1 = land.repo.forge("fix", "start", "Ask fix", "--done", "Ask fix done", "--slug", "ask-fix")
    assert s1.returncode == 0, s1.stderr
    s2 = land.repo.forge("fix", "start", "Size fix", "--done", "Size fix done", "--slug", "size-fix")
    assert s2.returncode == 0, s2.stderr
    s3 = land.repo.forge("fix", "start", "Ok fix", "--done", "Ok fix done", "--slug", "ok-fix")
    assert s3.returncode == 0, s3.stderr

    _wait_for(lambda: (land.repo.bin / "merged-fix-ok-fix").exists() and _runner_exited(tmp_path), timeout=45.0)
    assert not (tmp_path / "repo-fix-ok-fix").exists()
    assert (tmp_path / "repo-fix-ask-fix").exists()
    assert (tmp_path / "repo-fix-size-fix").exists()

    sent = _notices(notice_log)
    if os.name == "nt":
        assert sent == []
    else:
        ask_notices = [args for args in sent if any("ask-fix" in a for a in args)
                       and not any("Forge runner done" in a for a in args)]
        size_notices = [args for args in sent if any("size-fix" in a for a in args)
                        and not any("Forge runner done" in a for a in args)]
        summary_notices = [args for args in sent if any("Forge runner done" in a for a in args)]

        assert len(ask_notices) == 1, sent
        assert any("Should ask-fix keep the old default?" in a for a in ask_notices[0]), ask_notices[0]
        assert len(size_notices) == 1, sent
        assert any("allow-large" in a for a in size_notices[0]), size_notices[0]
        assert len(summary_notices) == 1, sent
        summary_text = " ".join(summary_notices[0])
        assert "1 merged" in summary_text and "ask-fix" in summary_text and "size-fix" in summary_text, summary_text

    # Repeated wake / restart: no duplicate notice, no new build for parked items, and no summary when idle.
    calls_before = len(calls(land.repo.bin / "claude-sdk-calls.jsonl"))
    woke = land.repo.forge("next")
    assert woke.returncode == 0, woke.stderr
    _wait_for(lambda: _runner_exited(tmp_path), timeout=30.0)

    assert len(_notices(notice_log)) == len(sent), _notices(notice_log)
    assert len(calls(land.repo.bin / "claude-sdk-calls.jsonl")) == calls_before
