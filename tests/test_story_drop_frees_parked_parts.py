"""Dropping a story parks its unmerged parts: their pull requests close and their files are free."""
import json

from test_start_sorts_ideas import (intake, _signed_off, _started, _plan,
                                    _checkout, _land_setup)  # noqa: F401
from test_close import env  # noqa: F401
from test_land import land  # noqa: F401
from test_story import DOC, approved_constitution, claude_plan

STORY = "FIX-STORY-DROP-PARKS-PARTS"


def _approved(intake, claude_payload, key, tmp_path, monkeypatch):
    repo, top, owner, *_ = intake
    where = _checkout(repo, top, f"story/{key}")
    doc = DOC.replace("| yes |", "| no |")
    (where / f"plans/{key}.md").write_text(doc, "utf-8")
    read = owner.forge("read", key, cwd=where)
    assert read.returncode == 0, read.stdout + read.stderr
    if read.stdout.lstrip().startswith("{"):
        handout = json.loads(read.stdout)
        read = owner.forge("handback", key, "--round", str(handout["round"]),
                           "--subagent", "plan-reader", "--text", "No findings.", cwd=where)
        assert read.returncode == 0, read.stdout + read.stderr
    approval = repo.forge("hook", "approval", input=json.dumps(claude_plan(
        claude_payload, doc, cwd=where)), cwd=where)
    assert approval.returncode == 0, approval.stdout + approval.stderr


def test_1_dropped_story_with_an_unmerged_part_frees_its_files(intake, claude_payload, monkeypatch, tmp_path):
    repo, top, owner, *_ = intake
    from test_fix_drop import _github
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        f'[projects.{json.dumps(str(top))}]\ntrust_level = "trusted"\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("STUB_CODEX_TEXT", "No findings.")
    _signed_off(intake)
    approved_constitution(repo, where=top)
    roadmap = top / "plans/roadmap.json"
    data = json.loads(roadmap.read_text("utf-8")) if roadmap.exists() else {"items": []}
    data["items"] += [{"key": "PARKED", "title": "Keep baskets for later"},
                      {"key": "OTHER", "title": "Keep baskets elsewhere"}]
    roadmap.write_text(json.dumps(data), "utf-8")
    _land_setup(repo, top, "record-roadmap")
    for key in ("PARKED", "OTHER"):
        _started(intake, f"Another saved basket {key}", _plan(key))
        _approved(intake, claude_payload, key, tmp_path, monkeypatch)
    database = _github(repo)
    started = repo.forge("task", "start", "PARKED/SAVE", cwd=top)
    assert started.returncode == 0, started.stdout + started.stderr
    # Both SAVE parts own src/basket.py, so the second waits for the first.
    held = repo.forge("task", "start", "OTHER/SAVE", cwd=top)
    assert held.returncode == 1 and "PARKED/SAVE" in held.stderr, held.stderr
    pull = lambda number, head: {"number": number, "headRefName": head, "state": "OPEN",
                                 "title": "Part", "body": "", "isDraft": False, "baseRefName": "main",
                                 "url": f"https://github.com/acme/shop/pull/{number}"}
    # A longer story key shares the branch prefix but is another story.
    database.write_text(json.dumps([pull(8, "task/PARKED-SAVE"), pull(9, "task/PARKED-MORE-SAVE")]), "utf-8")
    # A teammate's clone from before the drop has not fetched it yet.
    peer = top.parent / "drop-observer"
    repo.git("clone", "-q", repo.git("remote", "get-url", "origin", cwd=top), str(peer), cwd=top)
    dropped = repo.forge("story", "drop", "PARKED", "--because", "Park it", cwd=top)
    assert dropped.returncode == 0, dropped.stdout + dropped.stderr
    states = {row["number"]: row["state"] for row in json.loads(database.read_text("utf-8"))}
    assert states == {8: "CLOSED", 9: "OPEN"}
    board = repo.forge("board", "--json", cwd=top)
    assert board.returncode == 0, board.stdout + board.stderr
    names = {row["id"] for row in json.loads(board.stdout)["items"]}
    assert "OTHER" in names and not {name for name in names if name.startswith("PARKED")}
    assert "PARKED" not in repo.forge("next", cwd=top).stdout
    # The released file starts; the parked story's parts stay stopped.
    freed = repo.forge("task", "start", "OTHER/SAVE", cwd=top)
    assert freed.returncode == 0, freed.stdout + freed.stderr
    for command, where in ((("task", "start", "PARKED/SHOW"), top), (("close", "PARKED/SAVE"), top),
                           (("close", "PARKED/SAVE"), peer)):
        refused = repo.forge(*command, cwd=where)
        assert refused.returncode == 1 and "PARKED is dropped" in refused.stderr, refused.stderr
