"""Native handback turns a Proof list in the worker's report into a commit when the round wrote none."""
import re

from test_conflicting_pull_requests_stop_check_waits import _publish_default
from test_tools_session_hold import Session
from test_workers_leave_settings_to_coordinator import client  # noqa: F401

STORY = "FIX-PROOF-LIST-FROM-HANDBACK"


def _round(client, monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    _publish_default(client, client.git("remote", "get-url", "origin"))
    assert client.forge("fix", "start", "Correct spelling", "--done", "Correct the spelling",
                        "--kind", "mechanical").returncode == 0
    folder = client.path.parent / f"{client.path.name}-fix-correct-spelling"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "without-claude-sdk"))
    host = Session(client, tmp_path / "host", "claude-session")
    number = re.search(r"--round (\d+)", host.forge("work", "correct-spelling").stdout)[1]
    return host, folder, number


def _back(host, number, text):
    done = host.forge("handback", "correct-spelling", "--round", number, "--subagent", "worker", "--text", text)
    assert done.returncode == 0, done.stdout + done.stderr


def test_2_keeps_functional_check_and_staged_edits_and_whole_report(client, monkeypatch, tmp_path):
    host, folder, number = _round(client, monkeypatch, tmp_path)
    try:
        (folder / "notes.txt").write_text("fixed\n", "utf-8")
        client.git("add", "notes.txt", cwd=folder)
        client.git("commit", "-qm", "Fix the spelling\n\nFunctional check: walked the page", cwd=folder)
        (folder / "staged.txt").write_text("x\n", "utf-8")
        client.git("add", "staged.txt", cwd=folder)
        report = "Proof list:\n- 1: tests/test_a.py::test_a\n\n- 2: tests/test_b.py::test_b\n\nBye."
        host.forge("handback", "correct-spelling", "--round", number, "--subagent", "worker", "--text", report)
        _back(host, number, "Committed.")
        message = client.git("log", "-1", "--format=%B", cwd=folder)
        assert "- 2: tests/test_b.py::test_b" in message
        assert "Functional check: walked the page" in message
        assert "staged.txt" not in client.git("show", "--stat", "--format=", "HEAD", cwd=folder)
    finally:
        host.close()


def test_4_check_line_between_entries_in_a_report_saved_before_the_nudge(client, monkeypatch, tmp_path):
    host, folder, number = _round(client, monkeypatch, tmp_path)
    try:
        (folder / "notes.txt").write_text("fixed\n", "utf-8")
        report = "Proof list:\n- 1: tests/test_a.py::test_a\n- check: lint passed\n- 2: tests/test_b.py::test_b\n"
        host.forge("handback", "correct-spelling", "--round", number, "--subagent", "worker", "--text", report)
        client.git("add", "notes.txt", cwd=folder)
        client.git("commit", "-qm", "Fix the spelling", cwd=folder)
        _back(host, number, "Committed.")
        message = client.git("log", "-1", "--format=%B", cwd=folder)
        assert "- check: lint passed\n- 2: tests/test_b.py::test_b" in message
    finally:
        host.close()


def test_3_earlier_proof_on_the_branch_is_not_replaced(client, monkeypatch, tmp_path):
    host, folder, number = _round(client, monkeypatch, tmp_path)
    try:
        client.git("commit", "-q", "--allow-empty", "-m", "Earlier\n\nProof list:\n- Done when: tests/test_z.py::test_z",
                   cwd=folder)
        _back(host, number, "Proof list:\n- Done when: tests/test_partial.py::test_p")
        assert "Earlier" in client.git("log", "-1", "--format=%B", cwd=folder)
    finally:
        host.close()


def test_1_handback_commits_the_proof_list_from_the_report(client, monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    _publish_default(client, client.git("remote", "get-url", "origin"))
    assert client.forge("fix", "start", "Correct spelling", "--done", "Correct the spelling",
                        "--kind", "mechanical").returncode == 0
    folder = client.path.parent / f"{client.path.name}-fix-correct-spelling"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "without-claude-sdk"))
    host = Session(client, tmp_path / "host", "claude-session")
    try:
        offered = host.forge("work", "correct-spelling")
        number = re.search(r"--round (\d+)", offered.stdout)[1]
        (folder / "notes.txt").write_text("fixed\n", "utf-8")
        client.git("add", "notes.txt", cwd=folder)
        client.git("commit", "-qm", "Fix the spelling", cwd=folder)
        report = "Done.\n\nProof list:\n- Done when: tests/test_spelling.py::test_spelling\n\nBye."
        returned = host.forge("handback", "correct-spelling", "--round", number,
                              "--subagent", "worker", "--text", report)
        assert returned.returncode == 0, returned.stdout + returned.stderr
        message = client.git("log", "-1", "--format=%B", cwd=folder)
        assert "Proof list:\n- Done when: tests/test_spelling.py::test_spelling" in message
        assert "Bye." not in message
    finally:
        host.close()
