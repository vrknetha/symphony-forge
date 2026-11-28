"""Plans waiting for approval and approved plans can be dropped."""
import json

from test_start_sorts_ideas import (intake, _signed_off, _started, _plan,
                                    _checkout, _land_setup)  # noqa: F401
from test_close import env  # noqa: F401
from test_land import land  # noqa: F401
from test_story import DOC, approved_constitution, claude_plan

STORY = "FORGE-STORYHOLD-1"


def test_5_read_and_approved_plans_can_drop(intake, claude_payload, monkeypatch, tmp_path):
    repo, top, owner, *_ = intake
    # The ready SDK lets the plan reader use Codex, whose real trust check
    # needs this test's own project approval and isolated configuration.
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
    data["items"].extend({"key": key, "title": "Keep baskets for later"}
                         for key in ("WAITING", "APPROVED"))
    roadmap.write_text(json.dumps(data), "utf-8")
    _land_setup(repo, top, "record-roadmap")
    approved_doc = DOC.replace("| yes |", "| no |")
    for key in ("WAITING", "APPROVED"):
        _started(intake, f"Another saved basket {key}", _plan(key))
        where = _checkout(repo, top, f"story/{key}")
        (where / f"plans/{key}.md").write_text(approved_doc, "utf-8")
        read = owner.forge("read", key, cwd=where)
        assert read.returncode == 0, read.stdout + read.stderr
        if read.stdout.lstrip().startswith("{"):
            handout = json.loads(read.stdout)
            read = owner.forge("handback", key, "--round", str(handout["round"]),
                               "--subagent", "plan-reader", "--text", "No findings.", cwd=where)
            assert read.returncode == 0, read.stdout + read.stderr
        if key == "WAITING":
            dropped = repo.forge("story", "drop", key, "--because", "Park the plan", cwd=top)
            assert dropped.returncode == 0, dropped.stdout + dropped.stderr
            assert "Dropped plan WAITING." in dropped.stdout
            assert "The approval is dropped too." not in dropped.stdout
    approval = repo.forge("hook", "approval", input=json.dumps(claude_plan(
        claude_payload, approved_doc, cwd=where)), cwd=where)
    assert approval.returncode == 0, approval.stdout + approval.stderr
    # A plan on the default branch alone does not mean a part started.
    (top / "plans/APPROVED.md").write_text(approved_doc, "utf-8")
    _land_setup(repo, top, "publish-approved-plan")
    dropped = repo.forge("story", "drop", "APPROVED", "--because", "Keep it for later", cwd=top)
    assert dropped.returncode == 0, dropped.stdout + dropped.stderr
    assert "Its remote branch keeps the work." in dropped.stdout
    assert "The approval is dropped too." in dropped.stdout
    assert "forge story drop APPROVED --undo" in dropped.stdout
    assert "--later" in dropped.stdout
    assert repo.git("ls-remote", "origin", "refs/heads/story/APPROVED", cwd=top)
    assert repo.git("show", "origin/story/APPROVED:plans/APPROVED.md", cwd=top) == approved_doc.rstrip()
    assert "APPROVED" not in repo.forge("next", cwd=top).stdout
    board = repo.forge("board", "--json", cwd=top)
    assert board.returncode == 0, board.stdout + board.stderr
    assert "APPROVED" not in {row["id"] for row in json.loads(board.stdout)["items"]}
    assert json.loads(roadmap.read_text("utf-8")) == data
    # Revert the drop on its retained branch, as for an unapproved plan.
    repo.git("worktree", "add", "-q", "-b", "story/APPROVED", str(where),
             "origin/story/APPROVED", cwd=top)
    repo.git("revert", "--no-edit", "HEAD", cwd=where)
    repo.git("push", "-q", "origin", "story/APPROVED", cwd=where)
    assert "APPROVED" in repo.forge("next", cwd=top).stdout
    started = repo.forge("task", "start", "APPROVED/SAVE", cwd=top)
    assert started.returncode == 0, started.stdout + started.stderr
    # After a part merges, its record survives only on the default branch.
    part = _checkout(repo, top, "task/APPROVED-SAVE")
    repo.git("merge", "-q", "--no-ff", "task/APPROVED-SAVE", "-m", "Merge saved basket part", cwd=top)
    _land_setup(repo, top, "publish-merged-part")
    repo.git("worktree", "remove", str(part), cwd=top)
    repo.git("branch", "-d", "task/APPROVED-SAVE", cwd=top)
    repo.git("push", "origin", "--delete", "task/APPROVED-SAVE", cwd=top)
    refused = repo.forge("story", "drop", "APPROVED", "--because", "Keep it for later", cwd=top)
    assert refused.returncode == 1
    assert refused.stderr == ("APPROVED has started parts, so it cannot be dropped.\n"
                              "Next: forge close APPROVED/SAVE\n")
