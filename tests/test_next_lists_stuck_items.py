"""Stuck items listed in one block by forge next with one next step each (FORGE-TIDYUP-1).

Test-audit: real `forge next` output owns this contract across the whole report. Listing a
stuck item twice with conflicting Next: lines, omitting closed-PR items (including those saved
as waiting for checks, run from their own checkout, or cleaned up while still on origin),
offering `forge fix drop` for a story part or `forge/` migrate branch, misclassifying completed
versus failed/interrupted worker rounds, surfacing a fix dropped on another machine, or
claiming an item is stuck when GitHub is unavailable all make this fail. Closest existing test:
test_doctor_lists_unbuilt_fixes.py (covers `forge doctor` on unbuilt fixes only). Only GitHub
is fake; real worktrees, commits, events, and state files supply the evidence. No seam.
"""
import json

import pytest

from test_doctor_fix import FINISHED_PR_QUERY, _client, _gone, _prs
from test_story import worktree

STORY = "FORGE-TIDYUP-1"


def _graphql_pages(entries: dict[str, list[dict]]) -> str:
    pages = {
        f"head_{branch.encode().hex()}": {
            "nodes": nodes,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
        for branch, nodes in entries.items()
    }
    return json.dumps({"data": {"repository": pages}})


def _write_events(repo, events: list[dict]) -> None:
    path = repo.path / ".git" / "forge" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


@pytest.mark.parametrize("mode", ["github-available", "github-unavailable"])
def test_6_next_lists_stuck_items_with_one_next_step(repo, gh, tmp_path, monkeypatch, mode):
    _client(repo)
    repo.git("push", "-q", "origin", "main")

    if mode == "github-unavailable":
        # A fix started > 7 days ago whose PR may already be merged on GitHub while GitHub is down.
        monkeypatch.setenv("FORGE_NOW", "2026-10-01T12:00:00+00:00")
        started = repo.forge("fix", "start", "Repair while offline", "--done",
                             "Offline check stays safe", "--slug", "maybe-merged")
        assert started.returncode == 0, started.stdout + started.stderr
        monkeypatch.setenv("FORGE_NOW", "2026-10-10T12:00:00+00:00")
        gh.respond(*FINISHED_PR_QUERY, exit=1, stderr="network down")
        gh.respond("pr", "list", exit=1, stderr="network down")

        done = repo.forge("next")
        assert done.returncode == 0, done.stdout + done.stderr
        assert "Stuck items:" not in done.stdout, done.stdout
        assert "forge land maybe-merged" not in done.stdout, done.stdout
        assert "forge fix drop maybe-merged" not in done.stdout, done.stdout
        return

    # 1. Stalled fix: started > 7 days ago, no PR, no work commits.
    monkeypatch.setenv("FORGE_NOW", "2026-10-01T12:00:00+00:00")
    assert repo.forge("fix", "start", "Repair the old greeting", "--done",
                      "Readers see the old greeting", "--slug", "old-fix").returncode == 0

    monkeypatch.setenv("FORGE_NOW", "2026-10-10T12:00:00+00:00")

    # 2. Fresh fix: started today, NOT stuck.
    assert repo.forge("fix", "start", "Repair the fresh greeting", "--done",
                      "Readers see the fresh greeting", "--slug", "fresh-fix").returncode == 0

    # 3. Closed-PR fix saved as "waiting for checks" with uncommitted file kept by done-when 2.
    assert repo.forge("fix", "start", "Repair the closed greeting", "--done",
                      "Readers see the closed greeting", "--slug", "closed-waiting").returncode == 0
    cw_tree = worktree(repo, "fix/closed-waiting")
    cw_state_path = cw_tree / ".factory" / "fixes" / "closed-waiting.json"
    cw_state = json.loads(cw_state_path.read_text(encoding="utf-8"))
    cw_state["status"] = "waiting for checks"
    cw_state_path.write_text(json.dumps(cw_state) + "\n", encoding="utf-8")
    (cw_tree / "work.txt").write_text("work\n", encoding="utf-8")
    repo.git("add", "work.txt", ".factory/fixes/closed-waiting.json", cwd=cw_tree)
    repo.git("commit", "-qm", "Close waiting work", cwd=cw_tree)
    cw_head = repo.git("rev-parse", "HEAD", cwd=cw_tree)
    (cw_tree / "dirty.txt").write_text("keep local\n", encoding="utf-8")

    # 4. Clean closed-PR fix pushed to origin: tidy_finished removes its folder, but origin stays unmerged.
    assert repo.forge("fix", "start", "Repair the remote closed greeting", "--done",
                      "Readers see remote closed", "--slug", "closed-remote").returncode == 0
    cr_tree = worktree(repo, "fix/closed-remote")
    (cr_tree / "remote.txt").write_text("work\n", encoding="utf-8")
    repo.git("add", "remote.txt", cwd=cr_tree)
    repo.git("commit", "-qm", "Add remote closed work", cwd=cr_tree)
    repo.git("push", "-q", "origin", "fix/closed-remote", cwd=cr_tree)
    cr_head = repo.git("rev-parse", "HEAD", cwd=cr_tree)

    # 5. forge/ migrate branch with a closed PR: cannot use `forge fix drop`, must get `forge land`.
    mig_tree = tmp_path / "forge-migrate-v1"
    repo.git("worktree", "add", "-q", "-b", "forge/migrate-v1", str(mig_tree), "main")
    mig_state_path = mig_tree / ".factory" / "fixes" / "migrate-v1.json"
    mig_state_path.parent.mkdir(parents=True, exist_ok=True)
    mig_state_path.write_text(json.dumps({
        "kind": "migrate", "branch": "forge/migrate-v1", "why": "Move repo to new Forge",
        "done_when": "Repo migrated", "base": repo.git("rev-parse", "main"),
        "status": "started", "steps": [{"step": "start", "at": "2026-10-10T12:00:00+00:00"}],
    }) + "\n", encoding="utf-8")
    repo.git("add", ".factory/fixes/migrate-v1.json", cwd=mig_tree)
    repo.git("commit", "-qm", "Start migrate", cwd=mig_tree)
    mig_head = repo.git("rev-parse", "HEAD", cwd=mig_tree)

    # 6. Fix dropped on another machine (origin has status=dropped) while local checkout is stale.
    assert repo.forge("fix", "start", "Repair dropped elsewhere", "--done",
                      "Dropped elsewhere", "--slug", "dropped-remote").returncode == 0
    dr_tree = worktree(repo, "fix/dropped-remote")
    dr_head = repo.git("rev-parse", "HEAD", cwd=dr_tree)
    # Push a dropped state directly to origin/fix/dropped-remote, leaving the local tree behind.
    dr_clone = tmp_path / "other-machine"
    repo.git("clone", "-q", str(repo.path.parent / "remote.git"), str(dr_clone))
    repo.git("push", "-q", "origin", "fix/dropped-remote", cwd=dr_tree)
    repo.git("fetch", "-q", "origin", cwd=dr_clone)
    repo.git("checkout", "-q", "-b", "fix/dropped-remote", "origin/fix/dropped-remote", cwd=dr_clone)
    dr_other_state = dr_clone / ".factory" / "fixes" / "dropped-remote.json"
    dropped_data = json.loads(dr_other_state.read_text(encoding="utf-8"))
    dropped_data["status"] = "dropped"
    dr_other_state.write_text(json.dumps(dropped_data) + "\n", encoding="utf-8")
    repo.git("add", ".factory/fixes/dropped-remote.json", cwd=dr_clone)
    repo.git("commit", "-qm", "Drop fix on other machine", cwd=dr_clone)
    repo.git("push", "-q", "origin", "fix/dropped-remote", cwd=dr_clone)
    repo.git("fetch", "-q", "origin")

    # 7. Repair round stopped on an open PR (status="fixing", latest worker run failed).
    assert repo.forge("fix", "start", "Repair interrupted fix round", "--done",
                      "Repair finishes", "--slug", "repair-stopped").returncode == 0
    rs_tree = worktree(repo, "fix/repair-stopped")
    rs_state_path = rs_tree / ".factory" / "fixes" / "repair-stopped.json"
    rs_state = json.loads(rs_state_path.read_text(encoding="utf-8"))
    rs_state["status"] = "fixing"
    rs_state["round"] = 2
    rs_state_path.write_text(json.dumps(rs_state) + "\n", encoding="utf-8")
    repo.git("add", ".factory/fixes/repair-stopped.json", cwd=rs_tree)
    repo.git("commit", "-qm", "repair-stopped is fixing", cwd=rs_tree)
    rs_head = repo.git("rev-parse", "HEAD", cwd=rs_tree)

    # 8. Completed initial worker (status="working", latest worker run completed): NOT stuck.
    assert repo.forge("fix", "start", "Repair completed worker", "--done",
                      "Completed worker closes", "--slug", "done-worker").returncode == 0
    dw_tree = worktree(repo, "fix/done-worker")
    dw_state_path = dw_tree / ".factory" / "fixes" / "done-worker.json"
    dw_state = json.loads(dw_state_path.read_text(encoding="utf-8"))
    dw_state["status"] = "working"
    dw_state["round"] = 1
    dw_state_path.write_text(json.dumps(dw_state) + "\n", encoding="utf-8")
    (dw_tree / "done.txt").write_text("built\n", encoding="utf-8")
    repo.git("add", "done.txt", ".factory/fixes/done-worker.json", cwd=dw_tree)
    repo.git("commit", "-qm", "Finish done-worker build", cwd=dw_tree)

    # 9. Story part whose builder stopped before finishing (unfinished run start).
    part_tree = tmp_path / "task-STORY-1-PART"
    repo.git("worktree", "add", "-q", "-b", "task/STORY-1-PART", str(part_tree), "main")
    part_state_path = part_tree / ".factory" / "stories" / "STORY-1" / "tasks" / "PART.json"
    part_state_path.parent.mkdir(parents=True, exist_ok=True)
    part_state_path.write_text(json.dumps({
        "kind": "task", "story": "STORY-1", "task": "PART",
        "branch": "task/STORY-1-PART", "base": repo.git("rev-parse", "main"),
        "status": "working", "round": 1,
        "steps": [{"step": "start", "at": "2026-10-10T12:00:00+00:00"}],
    }) + "\n", encoding="utf-8")
    repo.git("add", ".factory/stories/STORY-1/tasks/PART.json", cwd=part_tree)
    repo.git("commit", "-qm", "STORY-1/PART is working", cwd=part_tree)

    _write_events(repo, [
        {"event": "run start", "id": "r-rs-1", "item": "repair-stopped", "kind": "work", "round": 1, "at": "2026-10-10T10:00:00+00:00"},
        {"event": "run end", "run_id": "r-rs-1", "item": "repair-stopped", "kind": "work", "round": 1, "outcome": "completed", "at": "2026-10-10T10:05:00+00:00"},
        {"event": "run start", "id": "r-rs-rev", "item": "repair-stopped", "kind": "review", "at": "2026-10-10T10:06:00+00:00"},
        {"event": "run end", "run_id": "r-rs-rev", "item": "repair-stopped", "kind": "review", "outcome": "completed", "at": "2026-10-10T10:07:00+00:00"},
        {"event": "run start", "id": "r-rs-2", "item": "repair-stopped", "kind": "work", "round": 2, "at": "2026-10-10T10:10:00+00:00"},
        {"event": "run end", "run_id": "r-rs-2", "item": "repair-stopped", "kind": "work", "round": 2, "outcome": "failed", "at": "2026-10-10T10:11:00+00:00"},
        {"event": "run start", "id": "r-dw-1", "item": "done-worker", "kind": "work", "round": 1, "at": "2026-10-10T10:00:00+00:00"},
        {"event": "run end", "run_id": "r-dw-1", "item": "done-worker", "kind": "work", "round": 1, "outcome": "completed", "at": "2026-10-10T10:05:00+00:00"},
        {"event": "run start", "id": "r-part-1", "item": "STORY-1/PART", "kind": "work", "round": 1, "at": "2026-10-10T10:00:00+00:00"},
    ])

    gh.respond("pr", "list", "--state", "open", stdout=json.dumps([
        {"headRefName": "fix/repair-stopped", "headRefOid": rs_head, "body": "",
         "url": "https://github.com/example/repo/pull/7", "isDraft": False},
    ]))
    gh.respond("pr", "list", "--state", "merged", stdout="[]")
    _prs(gh, stdout=_graphql_pages({
        "fix/old-fix": [],
        "fix/fresh-fix": [],
        "fix/closed-waiting": [{"headRefOid": cw_head, "state": "CLOSED"}],
        "fix/closed-remote": [{"headRefOid": cr_head, "state": "CLOSED"}],
        "forge/migrate-v1": [{"headRefOid": mig_head, "state": "CLOSED"}],
        "fix/dropped-remote": [{"headRefOid": dr_head, "state": "CLOSED"}],
        "fix/repair-stopped": [{"headRefOid": rs_head, "state": "OPEN"}],
        "fix/done-worker": [],
        "task/STORY-1-PART": [],
    }))

    done = repo.forge("next")
    assert done.returncode == 0, done.stdout + done.stderr
    out = done.stdout
    before, sep, after = out.partition("Stuck items:")
    assert sep == "Stuck items:", out

    # Clean closed-remote worktree was tidied, yet still listed in Stuck items because origin holds it.
    assert _gone(repo, cr_tree, "fix/closed-remote")
    assert "Removed 1 finished folders." in out, out

    # Every stuck item appears ONCE (only inside Stuck items, never duplicated in routine output) with ONE next step.
    expected_stuck = [
        ("old-fix", "- Repair the old greeting: no pull request and no commit for more than 7 days.\n  Next: forge land old-fix\n"),
        ("closed-waiting", '- Repair the closed greeting: its pull request was closed without a merge.\n  Next: forge fix drop closed-waiting --because "<reason>"\n'),
        ("closed-remote", '- Repair the remote closed greeting: its pull request was closed without a merge.\n  Next: forge fix drop closed-remote --because "<reason>"\n'),
        ("migrate-v1", "- Move repo to new Forge: its pull request was closed without a merge.\n  Next: forge land migrate-v1\n"),
        ("repair-stopped", "- Repair interrupted fix round: its builder stopped before it finished.\n  Next: forge land repair-stopped\n"),
        ("STORY-1/PART", "- STORY-1/PART: its builder stopped before it finished.\n  Next: forge land STORY-1/PART\n"),
    ]
    for item, snippet in expected_stuck:
        assert snippet in after, f"missing {item}:\n{after}"
        assert item not in before, f"{item} duplicated before Stuck items:\n{before}"
        assert out.count(f"Next: forge land {item}") + out.count(f"Next: forge fix drop {item}") == 1, out

    # Never offer forge fix drop for story parts or forge/ branches.
    assert "forge fix drop STORY-1/PART" not in out
    assert "forge fix drop migrate-v1" not in out

    # Non-stuck items stay out of Stuck items; completed worker still gets forge close.
    for not_stuck in ("fresh-fix", "done-worker", "dropped-remote"):
        assert not_stuck not in after, f"{not_stuck} should not be stuck:\n{after}"
    assert "Next: forge work fresh-fix" in before, before
    assert "Next: forge close done-worker" in before, before
    assert "dropped-remote" not in out, out

    # No duplicate GraphQL query for local branches.
    assert len(gh.calls(*FINISHED_PR_QUERY)) == 1

    # Running forge next from inside a closed-PR checkout still lists both it and the already-cleaned remote closed fix.
    from_closed = repo.forge("next", cwd=cw_tree)
    assert from_closed.returncode == 0, from_closed.stdout + from_closed.stderr
    assert '- Repair the closed greeting: its pull request was closed without a merge.\n  Next: forge fix drop closed-waiting --because "<reason>"' in from_closed.stdout, from_closed.stdout
    assert '- Repair the remote closed greeting: its pull request was closed without a merge.\n  Next: forge fix drop closed-remote --because "<reason>"' in from_closed.stdout, from_closed.stdout
