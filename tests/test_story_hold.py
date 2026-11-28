"""Holding a story stops its started work and closes its open pull requests."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import _install
from test_close import env  # noqa: F401
from test_fix_drop import _github, _pr
from test_land import RUNS, _agent
from test_runner_moves_approved_work_to_merge import (
    TWO_PART_PLAN,
    _approve,
    _human_merge,
    _install_multi_gh,
    _mark_installed_before,
    _runner_exited,
    _runner_log,
    _setup_two_part_story,
    _wait_for,
    land,
    runner_cleanup,
)
from test_story import claude_plan, codex_question
from test_worker import calls

STORY = "FORGE-STORYHOLD-1"
INDEPENDENT_PARTS_PLAN = TWO_PART_PLAN.replace(
    "| TWO | Second part | Second change | 2 | `two.txt` | none | ONE | no | |",
    "| TWO | Second part | Second change | 2 | `two.txt` | none | | no | |",
)


def _start_one(land, tmp_path, monkeypatch, claude_payload, plan=TWO_PART_PLAN):
    _agent(land)
    _mark_installed_before(tmp_path)
    folder = _setup_two_part_story(land, key=STORY, plan=plan)
    monkeypatch.setenv("FORGE_NO_RUNNER", "1")
    _approve(land, folder, plan, claude_payload, monkeypatch)
    started = land.repo.forge("task", "start", f"{STORY}/ONE", cwd=land.repo.path)
    assert started.returncode == 0, started.stdout + started.stderr
    return folder, Path(started.stdout.splitlines()[0].rsplit(" in ", 1)[1])


@pytest.mark.platform
def test_1_dropped_story_does_not_run_its_started_part(land, tmp_path, monkeypatch, claude_payload):
    """A dropped story's started part must not reach the background runner."""
    _install_multi_gh(land, tmp_path)
    folder, part = _start_one(land, tmp_path, monkeypatch, claude_payload, INDEPENDENT_PARTS_PLAN)
    land.repo.git("push", "-q", "origin", f"story/{STORY}", cwd=folder)
    peer = land.repo.path.parent / "hold-observer"
    remote = land.repo.git("remote", "get-url", "origin", cwd=land.repo.path)
    land.repo.git("clone", "-q", remote, str(peer), cwd=land.repo.path)
    next_before = land.repo.forge("next", cwd=peer)
    assert next_before.returncode == 0, next_before.stdout + next_before.stderr
    offered_before = [line for line in next_before.stdout.splitlines() if line.startswith("Next: forge ")]
    assert any(f"{STORY}/ONE" in line for line in offered_before), next_before.stdout
    assert any(line.startswith(f"Next: forge task start {STORY}/TWO")
               for line in offered_before), next_before.stdout
    held = land.repo.forge("story", "drop", STORY, "--later", cwd=land.repo.path)
    assert held.returncode == 0, held.stdout + held.stderr
    owner_next = land.repo.forge("next", cwd=land.repo.path)
    assert owner_next.returncode == 0, owner_next.stdout + owner_next.stderr
    owner_suggestions = [line for line in owner_next.stdout.splitlines()
                         if line.startswith("Next: forge ")]
    part_ids = (f"{STORY}/ONE", f"{STORY}/TWO")
    assert not any(part in line for part in part_ids for line in owner_suggestions), owner_next.stdout

    monkeypatch.delenv("FORGE_NO_RUNNER")
    monkeypatch.setenv("FORGE_RUNNER_TICK", "0.05")
    monkeypatch.setenv("FORGE_NETWORK_RETRY_WAIT", "0")
    woke = land.repo.forge("lanes", cwd=land.repo.path)
    assert woke.returncode == 0, woke.stdout + woke.stderr
    _wait_for(lambda: _runner_exited(tmp_path), detail=lambda: _runner_log(land))

    assert not calls(land.repo.bin / "claude-sdk-calls.jsonl")
    log = _runner_log(land)
    assert f"[{STORY}/ONE]" not in log, log
    assert f"[{STORY}/TWO]" not in log, log
    assert f"[task start {STORY}/" not in log, log
    assert not list(part.glob("work-*.txt"))
    assert not (land.repo.bin / f"merged-task-{STORY}-ONE").exists()
    assert not (land.repo.bin / f"merged-task-{STORY}-TWO").exists()
    land.repo.git("fetch", "-q", "origin", cwd=peer)
    next_result = land.repo.forge("next", cwd=peer)
    assert next_result.returncode == 0, next_result.stdout + next_result.stderr
    peer_suggestions = [line for line in next_result.stdout.splitlines()
                        if line.startswith("Next: forge ")]
    assert not any(part in line for part in part_ids for line in peer_suggestions), next_result.stdout


@pytest.mark.platform
@pytest.mark.parametrize("phase", [
    "started", "merged", "approval", "approval-codex-shared", "approval-claude-shared",
    "approval-request-changes", "approval-stop", "create", "ready", "merge",
])
def test_3_later_holds_started_parts_and_refuses_part_commands(
    land, tmp_path, monkeypatch, claude_payload, codex_payload, phase,
):
    """Hold preserves work and stops approval and part commands at their boundaries."""
    if phase.startswith("approval"):
        return _hold_refuses_approval(land, monkeypatch, claude_payload, codex_payload, phase)
    if phase not in ("started", "merged"):
        return _hold_interrupts_command(land, tmp_path, monkeypatch, claude_payload, phase)

    plan = INDEPENDENT_PARTS_PLAN if phase == "started" else TWO_PART_PLAN
    _start_one(land, tmp_path, monkeypatch, claude_payload, plan)
    branch = f"task/{STORY}-ONE"
    branches = [branch]
    if phase == "started":
        second = land.repo.forge("task", "start", f"{STORY}/TWO")
        assert second.returncode == 0, second.stdout + second.stderr
        branches.append(f"task/{STORY}-TWO")
    if phase == "merged":
        _human_merge(land, tmp_path, branch)
    main = land.repo.git("ls-remote", "origin", "refs/heads/main")
    prs = _github(land.repo, [
        _pr("MERGED" if phase == "merged" else "OPEN")
        | {"number": number, "headRefName": head}
        for number, head in enumerate(branches, start=7)
    ])
    held = land.repo.forge("story", "drop", STORY, "--later", cwd=land.repo.path)
    assert held.returncode == 0, held.stdout + held.stderr
    assert f"Held story {STORY}." in held.stdout
    story_branch = f"refs/heads/story/{STORY}"
    saved = land.repo.git("ls-remote", "origin", story_branch)
    assert saved
    assert land.repo.git("ls-remote", "origin", f"refs/heads/{branch}")
    repeated = land.repo.forge("story", "drop", STORY, "--later", "--because", "Another reason")
    assert repeated.returncode == 0 and f"{STORY} is already held." in repeated.stdout
    assert land.repo.git("ls-remote", "origin", story_branch) == saved
    pull_requests = json.loads(prs.read_text("utf-8"))
    if phase == "merged":
        [pull_request] = pull_requests
        assert pull_request["state"] == "MERGED"
        assert land.repo.git("ls-remote", "origin", "refs/heads/main") == main
    else:
        assert {pull["number"]: pull["state"] for pull in pull_requests} == {
            7: "CLOSED", 8: "CLOSED",
        }
        assert all(pull["comments"] == ["The owner wants it later"] for pull in pull_requests)
        assert all(land.repo.git("ls-remote", "origin", f"refs/heads/{head}")
                   for head in branches)

    commands = [("task", "start", f"{STORY}/TWO")]
    if phase == "started":
        commands.extend((command, f"{STORY}/ONE") for command in ("land", "close", "merge"))
    for command in commands:
        refused = land.repo.forge(*command)
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert f"{STORY} is dropped" in refused.stderr, refused.stderr


def _hold_refuses_approval(land, monkeypatch, claude_payload, codex_payload, phase):
    monkeypatch.setenv("FORGE_NO_RUNNER", "1")
    folder = _setup_two_part_story(land, key=STORY)
    next_step = land.repo.forge("next", cwd=folder)
    digest = re.search(r"approve_plan_([0-9a-f]{64})", next_step.stdout)
    assert digest, next_step.stdout + next_step.stderr
    declined = {"approval-request-changes": "Request changes", "approval-stop": "Stop"}.get(phase)
    if phase == "approval-claude-shared":
        submitted = claude_plan(claude_payload, TWO_PART_PLAN, cwd=folder)
    else:
        submitted = codex_question(codex_payload, digest[1], answer=declined or "Approve plan", cwd=folder)
    other = None
    if phase.endswith("-shared"):
        other = _setup_two_part_story(land, key="OTHER", plan=TWO_PART_PLAN.replace(
            "# Two-part story", "# A different story"))
        other_head = land.repo.git("rev-parse", "HEAD", cwd=other)
    held = land.repo.forge("story", "drop", STORY, "--later")
    assert held.returncode == 0, held.stdout + held.stderr
    head = land.repo.git("rev-parse", "HEAD", cwd=folder)
    refused = land.repo.forge("hook", "approval", input=json.dumps(submitted), cwd=folder)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    if other:
        assert "The approved plan matches 2 story docs" in refused.stderr
        assert land.repo.git("rev-parse", "HEAD", cwd=other) == other_head
    elif declined:
        assert f'The answer was "{declined}"' in refused.stderr
    else:
        assert f"{STORY} is dropped" in refused.stderr
        assert f"Next: forge story drop {STORY} --undo" in refused.stderr
    assert land.repo.git("rev-parse", "HEAD", cwd=folder) == head
    assert not land.repo.git("status", "--porcelain", "--untracked-files=all", cwd=folder)


def _hold_during(land, trigger):
    gh = land.repo.bin / "gh"
    script = gh.read_text("utf-8")
    action = f'''
if args[:len({trigger!r})] == {trigger!r} and not (here / "held-during-command").exists():
    (here / "held-during-command").touch()
    hold = subprocess.run([sys.executable, str(here / "forge"), "story", "drop",
                           {STORY!r}, "--later"], cwd={json.dumps(land.repo.path.as_posix())},
                          capture_output=True, text=True)
    assert hold.returncode == 0, hold.stdout + hold.stderr
'''
    line = "args = sys.argv[1:]\n"
    _install(land.repo.bin, "gh", script.replace(line, line + action, 1))


def _hold_interrupts_command(land, tmp_path, monkeypatch, claude_payload, phase):
    _folder, part = _start_one(land, tmp_path, monkeypatch, claude_payload)
    land.approve_working_build()
    land.commit(part, "one.txt", "First part\n", "Build first part\n\nProof list:\n- 1: check: First part")
    branch = f"task/{STORY}-ONE"
    item = f"{STORY}/ONE"
    opened = _pr() | {"headRefName": branch}
    _github(land.repo, [] if phase == "create" else [opened])
    if phase == "merge":
        ready = land.repo.forge("close", item)
        assert ready.returncode == 0 and "Ready:" in ready.stdout, ready.stdout + ready.stderr
    trigger = ["pr", "list", "--head", branch, "--state", "all"] if phase == "create" else RUNS
    _hold_during(land, trigger)
    stopped = land.repo.forge("merge" if phase == "merge" else "close", item)
    assert (land.repo.bin / "held-during-command").exists(), stopped.stdout + stopped.stderr
    assert stopped.returncode == 1, stopped.stdout + stopped.stderr
    assert f"{STORY} is dropped" in stopped.stderr, stopped.stdout + stopped.stderr
    assert "Ready:" not in stopped.stdout
    assert not land.gh_calls("pr", "create")
    assert not land.gh_calls("pr", "ready")
    assert not land.gh_calls("pr", "merge")
