"""Stuck items listed in one block by forge next with one next step each (FORGE-TIDYUP-1).

Test-audit: real `forge next` output owns this contract. Omitting stalled, closed-PR, or
stopped-builder items, offering `forge fix drop` for a story part, or listing a fresh
active fix makes this fail. Closest existing test: test_doctor_lists_unbuilt_fixes.py
(covers `forge doctor` on unbuilt fixes only, not `forge next`'s stuck-items block across
stalled, closed-PR, and stopped-builder items). Only GitHub is fake; real worktrees,
commits, and state files supply the evidence. No production seam.
"""
import json

from test_doctor_fix import FINISHED_PR_QUERY, _client, _prs
from test_story import worktree

STORY = "FORGE-TIDYUP-1"


def test_6_next_lists_stuck_items_with_one_next_step(repo, gh, tmp_path, monkeypatch):
    _client(repo)

    # 1. Stalled fix: started > 7 days ago, no PR, no work commits.
    monkeypatch.setenv("FORGE_NOW", "2026-10-01T12:00:00+00:00")
    started = repo.forge("fix", "start", "Repair the old greeting", "--done",
                         "Readers see the old greeting", "--slug", "old-fix")
    assert started.returncode == 0, started.stdout + started.stderr

    # 2. Fresh fix: started today, should NOT be listed as stuck.
    monkeypatch.setenv("FORGE_NOW", "2026-10-10T12:00:00+00:00")
    fresh = repo.forge("fix", "start", "Repair the fresh greeting", "--done",
                       "Readers see the fresh greeting", "--slug", "fresh-fix")
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr

    # 3. Fix with a closed PR whose branch is not on origin (kept by done-when 2).
    closed = repo.forge("fix", "start", "Repair the closed greeting", "--done",
                        "Readers see the closed greeting", "--slug", "closed-fix")
    assert closed.returncode == 0, closed.stdout + closed.stderr
    closed_tree = worktree(repo, "fix/closed-fix")
    (closed_tree / "closed.txt").write_text("work\n", encoding="utf-8")
    repo.git("add", "closed.txt", cwd=closed_tree)
    repo.git("commit", "-qm", "Add closed work", cwd=closed_tree)
    closed_head = repo.git("rev-parse", "HEAD", cwd=closed_tree)

    # 4. Story part with status "working" and no live builder.
    part_tree = tmp_path / "task-STORY-1-PART"
    repo.git("worktree", "add", "-q", "-b", "task/STORY-1-PART", str(part_tree), "main")
    state_path = part_tree / ".factory" / "stories" / "STORY-1" / "tasks" / "PART.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "kind": "task",
        "story": "STORY-1",
        "task": "PART",
        "branch": "task/STORY-1-PART",
        "base": repo.git("rev-parse", "main"),
        "status": "working",
        "round": 1,
        "steps": [{"step": "start", "at": "2026-10-10T12:00:00+00:00"}],
    }) + "\n", encoding="utf-8")
    repo.git("add", ".factory/stories/STORY-1/tasks/PART.json", cwd=part_tree)
    repo.git("commit", "-qm", "Start STORY-1/PART", cwd=part_tree)

    # GraphQL returns every requested branch alias; only fix/closed-fix has a PR.
    empty = {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
    pages = {f"head_{b.encode().hex()}": empty
             for b in ("fix/old-fix", "fix/fresh-fix", "task/STORY-1-PART")}
    pages[f"head_{b'fix/closed-fix'.hex()}"] = {
        "nodes": [{"headRefOid": closed_head, "state": "CLOSED"}],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
    _prs(gh, stdout=json.dumps({"data": {"repository": pages}}))

    done = repo.forge("next")
    assert done.returncode == 0, done.stdout + done.stderr
    out = done.stdout

    assert "Stuck items:" in out, out
    block = out.split("Stuck items:", 1)[1]

    # Stalled fix listed with land and drop options.
    assert "Repair the old greeting" in block, block
    assert 'Next: forge land old-fix, or forge fix drop old-fix --because "<reason>"' in block, block

    # Closed-PR fix kept by done-when 2 is listed with land and drop options.
    assert "Repair the closed greeting" in block, block
    assert 'Next: forge land closed-fix, or forge fix drop closed-fix --because "<reason>"' in block, block

    # Stopped-builder story part is listed with ONLY forge land (no drop command).
    assert "STORY-1/PART" in block, block
    assert "Next: forge land STORY-1/PART\n" in block or block.endswith("Next: forge land STORY-1/PART"), block
    assert "forge fix drop STORY-1/PART" not in block, block

    # Fresh fix is not stuck.
    assert "fresh-fix" not in block, block
    assert "Repair the fresh greeting" not in block, block

    # No duplicate GraphQL query for local branches.
    assert len(gh.calls(*FINISHED_PR_QUERY)) == 1
