"""Gate regression suite.

Every case here is either the factory happy path or a defect found and fixed
during review (autoreview rounds 1-8, architecture review, forge-next
walk-through). Tests run against a fresh `forge init` scaffold — the vendored
artifact client repos actually receive. Pure stdlib + pytest; scripts are
exercised through their real CLI surface.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]


def run(repo: Path, script: str, *args: str, stdin: str | None = None):
    proc = subprocess.run(
        [sys.executable, str(repo / ".agents" / "scripts" / script), *args],
        cwd=repo, capture_output=True, text=True, input=stdin,
    )
    return proc.returncode, proc.stdout + proc.stderr


GIT_ID = ["-c", "user.email=test@caw.dev", "-c", "user.name=Gate Tests"]

# Minimal payload satisfying .agents/schemas/decomposition.json
DECOMP = {"status": "recorded", "generated_by": "docs-decomposer",
          "user_facing": True, "tasks": []}


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *GIT_ID, *args], cwd=repo,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "app"
    proc = subprocess.run(
        [sys.executable, str(HARNESS / ".agents" / "scripts" / "forge.py"),
         "init", "--name", "app", "--target", str(target)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", "scaffold")
    return target


def sign_off(repo: Path) -> None:
    code, out = run(repo, "forge.py", "decision", "new", "client-signoff", "--repo", str(repo))
    assert code == 0, out
    record = next((repo / "docs" / "decisions").glob("*-client-signoff.md"))
    record.write_text(
        record.read_text()
        .replace("status: proposed", "status: accepted")
        .replace('confirmed_by: ""', 'confirmed_by: "Client PM"')
    )
    code, out = run(repo, "record_signoff.py")
    assert code == 0, out


def intake(repo: Path, key: str = "ENG-1", title: str = "Invoices", *extra: str) -> tuple[int, str]:
    return run(repo, "intake.py", "--issue", key, "--title", title, *extra)


def save_plan(repo: Path, tmp_path: Path) -> tuple[int, str]:
    plan = tmp_path / "plan.md"
    plan.write_text("## Decisions\nNo new decisions\n")
    return run(repo, "forge.py", "plan", "save", "--from", str(plan))


def write_passing_artifacts(repo: Path, commit: str | None = None) -> None:
    sha = commit or head(repo)
    f = repo / ".factory"
    (f / "decomposition.json").write_text(
        json.dumps({**DECOMP, "commit": sha}))
    (f / "verify.json").write_text(json.dumps({"ok": True, "commit": sha}))
    (f / "tests.json").write_text(json.dumps({
        "automated": {"status": "passed", "generated_by": "implementer"},
        "functional": {"status": "passed", "score": 9,
                       "generated_by": "functional-checker"},
        "commit": sha,
    }))
    (f / "reviews").mkdir(exist_ok=True)
    for aspect in ("quality", "performance", "security"):
        (f / "reviews" / f"{aspect}.json").write_text(
            json.dumps({"score": 9, "blocking_findings": [],
                        "generated_by": "autoreview", "commit": sha})
        )


def run_state(repo: Path) -> dict:
    return json.loads((repo / ".factory" / "run.json").read_text())


# ---------------------------------------------------------------- happy path

def test_full_lifecycle_and_archive(repo, tmp_path):
    sign_off(repo)
    assert run_state(repo)["client_signoff"] is True
    code, _ = intake(repo)
    assert code == 0
    code, out = save_plan(repo, tmp_path)
    assert code == 0, out
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps(DECOMP))
    assert code == 0, out
    write_passing_artifacts(repo)
    code, out = run(repo, "update_run.py", "--decomposition-status", "recorded")
    assert code == 0, out
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out
    # Archive: history bundle + plan moved + plan_file consistent (autoreview r8)
    history = repo / ".factory" / "history" / "ENG-1"
    for name in ("run.json", "decomposition.json", "verify.json", "tests.json"):
        assert (history / name).exists()
    assert (history / "reviews" / "quality.json").exists()
    completed = repo / "plans" / "completed" / "ENG-1-invoices.md"
    assert completed.exists()
    assert not list((repo / "plans" / "active").glob("ENG-1-*.md"))
    for state in (run_state(repo), json.loads((history / "run.json").read_text())):
        assert state["plan_file"] == "plans/completed/ENG-1-invoices.md"
    # Idempotent rerun (autoreview r2)
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


# ---------------------------------------------------------- sign-off gating

def test_plan_save_refused_before_signoff(repo, tmp_path):
    intake(repo)
    code, out = save_plan(repo, tmp_path)
    assert code != 0 and "sign-off" in out


def test_plan_save_refused_without_run_state(repo, tmp_path):
    (repo / ".factory" / "run.json").unlink()
    plan = tmp_path / "plan.md"
    plan.write_text("x\n")
    code, out = run(repo, "forge.py", "plan", "save", "--issue", "ENG-9", "--from", str(plan))
    assert code != 0 and "sign-off" in out  # autoreview r6


def test_decomposition_refused_before_signoff(repo):
    intake(repo)
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps(DECOMP))
    assert code != 0 and "sign-off" in out


def test_decomposition_refused_before_approved_plan(repo):
    sign_off(repo)
    intake(repo)
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps(DECOMP))
    assert code != 0 and "approved" in out  # autoreview r10


def test_pr_ready_refused_before_signoff(repo):
    intake(repo)
    code, out = run(repo, "pr_ready.py")
    assert code != 0 and "sign-off" in out


def test_update_run_phase_gated_before_signoff(repo):
    intake(repo)
    code, out = run(repo, "update_run.py", "--phase", "planning")
    assert code != 0 and "sign-off" in out


def test_intake_starts_discovery_before_signoff_and_planning_after(repo, tmp_path):
    intake(repo)
    assert run_state(repo)["phase"] == "discovery"
    sign_off(repo)
    intake(repo, "ENG-2", "Refunds")
    state = run_state(repo)
    assert state["phase"] == "planning" and state["client_signoff"] is True


def test_record_signoff_requires_accepted_and_confirmed(repo):
    code, out = run(repo, "record_signoff.py")
    assert code != 0
    run(repo, "forge.py", "decision", "new", "client-signoff", "--repo", str(repo))
    code, out = run(repo, "record_signoff.py")
    assert code != 0 and "status" in out  # proposed, not accepted


# ------------------------------------------------------- plan approval gates

def test_update_run_approved_requires_plan_file(repo):
    sign_off(repo)
    intake(repo)
    code, out = run(repo, "update_run.py", "--plan-status", "approved")
    assert code != 0 and "plan save" in out


def test_pr_ready_requires_saved_plan(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    (repo / ".factory" / "run.json").write_text(
        json.dumps({**run_state(repo), "plan_status": "approved"})
    )
    write_passing_artifacts(repo)
    code, out = run(repo, "pr_ready.py")
    assert code != 0 and "plans/active" in out


# ------------------------------------------------------ pending-context gate

def test_plan_save_blocked_by_pending_ledgered_context(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    (repo / "docs" / "context" / "note.md").write_text("client email\n")
    run(repo, "forge.py", "context", "scan")
    code, out = save_plan(repo, tmp_path)
    assert code != 0 and "unharvested" in out  # autoreview r3


def test_plan_save_blocked_by_unscanned_drop(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    (repo / "docs" / "context" / "drop.md").write_text("raw\n")
    code, out = save_plan(repo, tmp_path)
    assert code != 0 and "unscanned" in out  # autoreview r4


def test_plan_save_blocked_when_harvested_file_changes(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    ctx = repo / "docs" / "context" / "spec.md"
    ctx.write_text("v1\n")
    run(repo, "forge.py", "context", "scan")
    run(repo, "forge.py", "context", "mark", "spec.md", "--ignored", "--notes", "noise")
    ctx.write_text("v1\nv2 addendum\n")
    code, out = save_plan(repo, tmp_path)
    assert code != 0 and "unscanned" in out  # autoreview r4


def test_plan_save_passes_after_harvest(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    (repo / "docs" / "context" / "note.md").write_text("client email\n")
    run(repo, "forge.py", "context", "scan")
    run(repo, "forge.py", "context", "mark", "note.md", "--ignored", "--notes", "irrelevant")
    code, out = save_plan(repo, tmp_path)
    assert code == 0, out


def test_next_counts_unscanned_context(repo):
    (repo / "docs" / "context" / "drop.md").write_text("raw\n")
    code, out = run(repo, "forge.py", "next")
    assert code == 0 and "Harvest 1 pending" in out  # autoreview r6


# ------------------------------------------------------------- context inbox

def test_scan_check_fails_on_drift_and_scan_registers(repo):
    (repo / "docs" / "context" / "a.md").write_text("x\n")
    code, out = run(repo, "forge.py", "context", "scan", "--check")
    assert code != 0  # drift detected, nothing written
    code, out = run(repo, "forge.py", "context", "scan")
    assert code == 0 and "pending: 1" in out
    code, out = run(repo, "forge.py", "context", "scan", "--check")
    assert code == 0


def test_subdirectory_readme_is_tracked(repo):
    sub = repo / "docs" / "context" / "client-call"
    sub.mkdir()
    (sub / "README.md").write_text("call notes\n")
    code, out = run(repo, "forge.py", "context", "scan")
    assert "client-call/README.md" in out  # autoreview r7


def test_mark_ignored_requires_notes(repo):
    (repo / "docs" / "context" / "a.md").write_text("x\n")
    run(repo, "forge.py", "context", "scan")
    code, out = run(repo, "forge.py", "context", "mark", "a.md", "--ignored")
    assert code != 0 and "--notes" in out  # autoreview r7


def test_mark_harvested_requires_real_in_repo_outputs(repo):
    (repo / "docs" / "context" / "a.md").write_text("x\n")
    run(repo, "forge.py", "context", "scan")
    code, out = run(repo, "forge.py", "context", "mark", "a.md", "--harvested")
    assert code != 0 and "--outputs" in out
    code, out = run(repo, "forge.py", "context", "mark", "a.md",
                    "--harvested", "--outputs", "docs/decisions/9999-phantom.md")
    assert code != 0 and "do not exist" in out
    for escaping in ("/etc/passwd", "../escape.md"):
        code, out = run(repo, "forge.py", "context", "mark", "a.md",
                        "--harvested", "--outputs", escaping)
        assert code != 0 and "inside the repo" in out  # autoreview r8


# ------------------------------------------------------------ intake safety

def test_intake_preserves_signoff_and_refuses_to_clobber_evidence(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    code, _ = run(repo, "record_decomposition_from_json.py",
                  stdin=json.dumps(DECOMP))
    assert code == 0
    # Mid-task second intake must refuse (autoreview r3)
    code, out = intake(repo, "ENG-2", "Refunds")
    assert code != 0 and "unarchived" in out
    assert (repo / ".factory" / "decomposition.json").exists()
    # Deliberate abandonment works and preserves sign-off (intake fix, r1 of first review)
    code, out = intake(repo, "ENG-2", "Refunds", "--discard-active")
    assert code == 0, out
    state = run_state(repo)
    assert state["client_signoff"] is True and state["phase"] == "planning"
    assert not (repo / ".factory" / "decomposition.json").exists()


def test_intake_guards_orphaned_approved_plan(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)  # plan approved, nothing else yet
    code, out = intake(repo, "ENG-2", "Refunds")
    assert code != 0 and "active plan" in out  # autoreview r9
    code, out = intake(repo, "ENG-2", "Refunds", "--discard-active")
    assert code == 0
    assert (repo / "plans" / "debt" / "ENG-1-invoices.md").exists()
    assert not list((repo / "plans" / "active").glob("ENG-1-*.md"))


def test_phase_implementing_requires_approved_saved_plan(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    code, out = run(repo, "update_run.py", "--phase", "implementing",
                    "--decomposition-status", "recorded")
    assert code != 0 and "approved" in out  # autoreview r9
    save_plan(repo, tmp_path)
    # Plan approved but decomposition artifact still missing (autoreview r11)
    code, out = run(repo, "update_run.py", "--phase", "implementing",
                    "--decomposition-status", "recorded")
    assert code != 0 and "decomposition" in out
    code, _ = run(repo, "record_decomposition_from_json.py",
                  stdin=json.dumps(DECOMP))
    assert code == 0
    code, out = run(repo, "update_run.py", "--phase", "implementing")
    assert code == 0, out


def test_decomposition_refused_without_run_state(repo):
    (repo / ".factory" / "run.json").unlink()
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps(DECOMP))
    assert code != 0 and "run.json" in out  # autoreview r11
    assert not (repo / ".factory" / "decomposition.json").exists()


def test_evidence_recorders_gated_on_preconditions(repo):
    # The whole writer family shares gate(): verify + test/review recorders
    # refuse before sign-off/plan/decomposition exist.
    intake(repo)
    for script, args, stdin in (
        ("verify.py", ("--print-only",), None),
        ("record_test_from_json.py", ("--kind", "automated"),
         json.dumps({"status": "passed"})),
        ("record_review_from_json.py", ("--aspect", "quality"),
         json.dumps({"score": 9})),
    ):
        code, out = run(repo, script, *args, stdin=stdin)
        assert code != 0 and "sign-off" in out, f"{script}: {out}"


# ----------------------------------------------------- provenance and upgrade

def ready_task(repo: Path, tmp_path: Path) -> None:
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    write_passing_artifacts(repo)
    run(repo, "update_run.py", "--decomposition-status", "recorded")


def test_pr_ready_rejects_unstamped_evidence(repo, tmp_path):
    ready_task(repo, tmp_path)
    verify = repo / ".factory" / "verify.json"
    verify.write_text(json.dumps({"ok": True}))  # no commit stamp
    code, out = run(repo, "pr_ready.py")
    assert code != 0 and "provenance" in out


def test_pr_ready_rejects_stale_evidence_after_code_change(repo, tmp_path):
    ready_task(repo, tmp_path)
    (repo / "app.py").write_text("print('changed after evidence')\n")
    git(repo, "add", "app.py")
    git(repo, "commit", "-q", "-m", "code change after evidence")
    code, out = run(repo, "pr_ready.py")
    assert code != 0 and "fresh evidence" in out
    # Re-recording at the new commit clears it
    write_passing_artifacts(repo)
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


def test_pr_ready_accepts_decomposition_recorded_before_implementation(repo, tmp_path):
    # Found by the pilot simulation: decomposition is stamped at planning time,
    # code lands after, evidence is stamped at the implementation commit.
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    code, _ = run(repo, "record_decomposition_from_json.py",
                  stdin=json.dumps(DECOMP))
    assert code == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "plan + decomposition")
    (repo / "src.py").write_text("VALUE = 1\n")
    git(repo, "add", "src.py")
    git(repo, "commit", "-q", "-m", "implementation")
    write_passing_artifacts(repo)  # evidence stamped at the new HEAD
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


def test_pr_ready_tolerates_evidence_only_commits(repo, tmp_path):
    ready_task(repo, tmp_path)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "record evidence")  # touches .factory/plans only
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


def test_pr_ready_tolerates_harness_upgrade_commits(repo, tmp_path):
    # Found by the pilot simulation: a forge upgrade mid-task touches .agents/
    # machinery — that is not product code and must not invalidate evidence.
    ready_task(repo, tmp_path)
    (repo / ".agents" / "scripts" / "extra_helper.py").write_text("# upgraded\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: forge upgrade")
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


def test_upgrade_replaces_machinery_preserves_project(repo, tmp_path):
    # Degrade machinery, add project-owned content + a proposed skill
    (repo / ".agents" / "scripts" / "verify.py").unlink()
    proposed = repo / ".agents" / "skills" / "proposed"
    proposed.mkdir(parents=True, exist_ok=True)
    (proposed / "keep-me.md").write_text("status: proposed\n")
    run(repo, "forge.py", "decision", "new", "keep-decision", "--repo", str(repo))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "project state")
    proc = subprocess.run(
        [sys.executable, str(HARNESS / ".agents" / "scripts" / "forge.py"),
         "upgrade", "--target", str(repo)],
        cwd=HARNESS, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / ".agents" / "scripts" / "verify.py").exists()  # machinery restored
    assert (proposed / "keep-me.md").exists()  # evolution state preserved
    assert list((repo / "docs" / "decisions").glob("*keep-decision.md"))  # project-owned untouched
    assert head(repo) in (repo / "constitution" / "VENDORED_FROM").read_text() or \
        "symphony-forge @" in (repo / "constitution" / "VENDORED_FROM").read_text()


def test_upgrade_refuses_dirty_target(repo):
    (repo / "dirty.txt").write_text("uncommitted\n")
    proc = subprocess.run(
        [sys.executable, str(HARNESS / ".agents" / "scripts" / "forge.py"),
         "upgrade", "--target", str(repo)],
        cwd=HARNESS, capture_output=True, text=True,
    )
    assert proc.returncode != 0 and "uncommitted" in proc.stdout + proc.stderr


# --------------------------------------------------------- misc deterministic

def test_decision_accept_and_plain_issue_keys(repo):
    code, out = run(repo, "forge.py", "decision", "new", "client-signoff", "--repo", str(repo))
    assert code == 0
    code, out = run(repo, "forge.py", "decision", "accept", "client-signoff", "--by", "Client PM")
    assert code == 0 and "Accepted" in out
    code, out = run(repo, "record_signoff.py")
    assert code == 0, out
    # Linear-style keys are NOT mandatory (GitHub/Jira/plain all work)
    for key in ("42", "gh-42", "PROJ_9.1"):
        code, out = intake(repo, key, f"Task {key}", "--discard-active")
        assert code == 0, out
        assert run_state(repo)["issue_key"] == key


def test_decision_numbering_allocates_sequentially(repo):
    run(repo, "forge.py", "decision", "new", "first", "--repo", str(repo))
    run(repo, "forge.py", "decision", "new", "second", "--repo", str(repo))
    names = sorted(p.name for p in (repo / "docs" / "decisions").glob("00*.md"))
    assert names == ["0001-first.md", "0002-second.md"]


def test_plan_assume_requires_active_plan_then_appends(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    code, out = run(repo, "forge.py", "plan", "assume", "guessing")
    assert code != 0 and "no active plan" in out
    save_plan(repo, tmp_path)
    code, out = run(repo, "forge.py", "plan", "assume", "IDs are UUIDv7")
    assert code == 0, out
    plan = next((repo / "plans" / "active").glob("ENG-1-*.md")).read_text()
    assert "## Implementation Assumptions" in plan and "IDs are UUIDv7" in plan


def test_dual_runtime_linter_clean_on_scaffold_and_catches_phantom_ref(repo):
    code, out = run(repo, "check_dual_runtime.py", str(repo))
    assert code == 0, out
    (repo / "plans" / "active").mkdir(parents=True, exist_ok=True)
    (repo / "plans" / "active" / "X-1-x.md").write_text(
        "see docs/decisions/0042-phantom.md\n"
    )
    code, out = run(repo, "check_dual_runtime.py", str(repo))
    assert code != 0 and "phantom" in out


# ------------------------------------------------------------------- roadmap

ROADMAP = {"generated_by": "human", "items": [
    {"key": "ENG-1", "title": "Invoices", "epic": "billing"},
    {"key": "ENG-2", "title": "Payments", "epic": "billing"},
]}


def import_roadmap(repo: Path, tmp_path: Path, payload=None) -> tuple[int, str]:
    src = tmp_path / "roadmap-input.json"
    src.write_text(json.dumps(payload if payload is not None else ROADMAP))
    return run(repo, "forge.py", "roadmap", "import", "--input", str(src))


def roadmap_items(repo: Path) -> dict:
    data = json.loads((repo / "plans" / "roadmap.json").read_text())
    return {item["key"]: item for item in data["items"]}


def test_roadmap_lifecycle(repo, tmp_path):
    sign_off(repo)
    code, out = import_roadmap(repo, tmp_path)
    assert code == 0 and "2 added" in out, out
    # forge next suggests the first pending item with the exact intake command
    code, out = run(repo, "forge.py", "next")
    assert code == 0 and "ENG-1" in out and "roadmap" in out.lower()
    # intake activates the matching item
    code, out = intake(repo)
    assert code == 0 and "marked active" in out
    assert roadmap_items(repo)["ENG-1"]["status"] == "active"
    # drive to pr-ready: item completed with a history link
    save_plan(repo, tmp_path)
    run(repo, "record_decomposition_from_json.py", stdin=json.dumps(DECOMP))
    write_passing_artifacts(repo)
    run(repo, "update_run.py", "--decomposition-status", "recorded")
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out
    items = roadmap_items(repo)
    assert items["ENG-1"]["status"] == "done"
    assert items["ENG-1"]["history"] == ".factory/history/ENG-1/"
    assert items["ENG-2"]["status"] == "pending"
    # next now suggests ENG-2 after the archived task
    code, out = run(repo, "intake.py", "--issue", "ENG-2", "--title", "Payments")
    assert code == 0
    assert roadmap_items(repo)["ENG-2"]["status"] == "active"


def test_roadmap_reimport_preserves_lifecycle_and_kept_items(repo, tmp_path):
    sign_off(repo)
    import_roadmap(repo, tmp_path)
    intake(repo)  # ENG-1 -> active
    # Refined roadmap: retitles ENG-1, drops ENG-2, adds ENG-3
    code, out = import_roadmap(repo, tmp_path, {"generated_by": "human", "items": [
        {"key": "ENG-1", "title": "Invoices v2", "epic": "billing"},
        {"key": "ENG-3", "title": "Reports", "epic": "insights"},
    ]})
    assert code == 0 and "kept" in out, out
    items = roadmap_items(repo)
    assert items["ENG-1"]["status"] == "active"  # lifecycle survives re-import
    assert items["ENG-1"]["title"] == "Invoices v2"
    assert items["ENG-3"]["status"] == "pending"
    assert "ENG-2" in items  # absent from input, kept — removal is a PR edit


def test_roadmap_import_and_add_validation(repo, tmp_path):
    code, out = import_roadmap(repo, tmp_path, {"items": [{"key": "A", "title": "x"}]})
    assert code != 0 and "generated_by" in out  # schema: unattributed import refused
    code, out = import_roadmap(repo, tmp_path,
                               {"generated_by": "human", "items": [{"key": "A"}]})
    assert code != 0 and "title" in out
    code, out = import_roadmap(repo, tmp_path, {"generated_by": "human", "items": [
        {"key": "A", "title": "x"}, {"key": "A", "title": "y"},
    ]})
    assert code != 0 and "duplicate" in out
    code, out = run(repo, "forge.py", "roadmap", "add", "ENG-9", "Reports")
    assert code == 0, out
    code, out = run(repo, "forge.py", "roadmap", "add", "ENG-9", "Reports")
    assert code != 0 and "already" in out


# ------------------------------------------------- determinism contract (schemas)

def test_recorders_refuse_nonconforming_payloads(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    # decomposition: missing required field
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps({"generated_by": "docs-decomposer", "tasks": []}))
    assert code != 0 and "user_facing" in out
    # decomposition: unpinned generator, message routes to the harness PR
    code, out = run(repo, "record_decomposition_from_json.py",
                    stdin=json.dumps({"generated_by": "ponytail",
                                      "user_facing": True, "tasks": []}))
    assert code != 0 and "not pinned" in out and "harness PR" in out
    # valid decomposition opens the downstream gates
    code, out = run(repo, "record_decomposition_from_json.py", stdin=json.dumps(DECOMP))
    assert code == 0, out
    # review: legacy 'blocking' alias no longer accepted as blocking_findings
    code, out = run(repo, "record_review_from_json.py", "--aspect", "quality",
                    stdin=json.dumps({"generated_by": "autoreview", "score": 9,
                                      "summary": "ok", "blocking": []}))
    assert code != 0 and "blocking_findings" in out
    # review: wrong type
    code, out = run(repo, "record_review_from_json.py", "--aspect", "quality",
                    stdin=json.dumps({"generated_by": "autoreview", "score": "9",
                                      "summary": "ok", "blocking_findings": []}))
    assert code != 0 and "'score' must be int" in out
    # review: unpinned generator (the old subagent name is retired)
    code, out = run(repo, "record_review_from_json.py", "--aspect", "quality",
                    stdin=json.dumps({"generated_by": "quality-reviewer", "score": 9,
                                      "summary": "ok", "blocking_findings": []}))
    assert code != 0 and "not pinned" in out
    # happy path: recorded, attested, no legacy keys written
    code, out = run(repo, "record_review_from_json.py", "--aspect", "quality",
                    stdin=json.dumps({"generated_by": "autoreview", "score": 9,
                                      "summary": "ok", "blocking_findings": []}))
    assert code == 0, out
    recorded = json.loads((repo / ".factory" / "reviews" / "quality.json").read_text())
    assert recorded["generated_by"] == "autoreview" and "blocking" not in recorded
    # testing artifact via the recorder
    code, out = run(repo, "record_test_from_json.py", "--kind", "automated",
                    stdin=json.dumps({"generated_by": "implementer", "status": "passed",
                                      "summary": "unit suite", "blocking_findings": [],
                                      "commands_run": ["pytest"]}))
    assert code == 0, out


def test_linter_catches_schema_allowlist_divergence(repo):
    schema = repo / ".agents" / "schemas" / "review.json"
    data = json.loads(schema.read_text())
    data["generated_by"].append("rogue-tool")
    schema.write_text(json.dumps(data))
    code, out = run(repo, "check_dual_runtime.py", str(repo))
    assert code != 0 and "rogue-tool" in out


def test_functional_check_conditional_on_user_facing(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    run(repo, "update_run.py", "--decomposition-status", "recorded")
    # user_facing: false — gate passes without a functional artifact
    write_passing_artifacts(repo)
    f = repo / ".factory"
    decomp = json.loads((f / "decomposition.json").read_text())
    decomp["user_facing"] = False
    (f / "decomposition.json").write_text(json.dumps(decomp))
    tests = json.loads((f / "tests.json").read_text())
    del tests["functional"]
    (f / "tests.json").write_text(json.dumps(tests))
    code, out = run(repo, "pr_ready.py")
    assert code == 0, out


def test_functional_check_required_when_user_facing(repo, tmp_path):
    sign_off(repo)
    intake(repo)
    save_plan(repo, tmp_path)
    run(repo, "update_run.py", "--decomposition-status", "recorded")
    write_passing_artifacts(repo)  # user_facing: true via DECOMP
    f = repo / ".factory"
    tests = json.loads((f / "tests.json").read_text())
    del tests["functional"]
    (f / "tests.json").write_text(json.dumps(tests))
    code, out = run(repo, "pr_ready.py")
    assert code != 0 and "functional" in out


# --------------------------------------------------------------------- adopt

def existing_repo(tmp_path: Path) -> Path:
    """A pre-harness, agent-built repo: own code, own CLAUDE.md, own CI."""
    repo = tmp_path / "legacy"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.js").write_text("console.log('prototype')\n")
    (repo / "README.md").write_text("# Legacy prototype\n")
    (repo / "CLAUDE.md").write_text("# Legacy agent instructions\nAlways use tabs.\n")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "their-ci.yml").write_text("name: theirs\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "pre-harness state")
    return repo


def adopt(repo: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(HARNESS / ".agents" / "scripts" / "forge.py"),
         "adopt", "--target", str(repo), "--name", "legacy"],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_adopt_vendors_harness_and_preserves_project(tmp_path):
    repo = existing_repo(tmp_path)
    code, out = adopt(repo)
    assert code == 0, out
    # machinery is in; project content untouched; their CI survived the merge
    assert (repo / ".agents" / "scripts" / "forge.py").exists()
    assert (repo / "src" / "app.js").read_text() == "console.log('prototype')\n"
    assert (repo / "README.md").read_text() == "# Legacy prototype\n"
    assert (repo / ".github" / "workflows" / "their-ci.yml").exists()
    # old CLAUDE.md preserved for harvest; shim installed
    kept = repo / "docs" / "context" / "migrated-CLAUDE.md"
    assert kept.exists() and "tabs" in kept.read_text()
    assert "@AGENTS.md" in (repo / "CLAUDE.md").read_text()
    # sign-off gate armed, project-owned files created
    state = json.loads((repo / ".factory" / "run.json").read_text())
    assert state["client_signoff"] is False
    assert (repo / "harness.yaml").exists()
    # the adopted repo passes the same checks as a scaffold
    code, out = run(repo, "check_dual_runtime.py", str(repo))
    assert code == 0, out
    code, out = run(repo, "check_factory_scaffold.py", str(repo))
    assert code == 0, out
    # adopting twice routes to upgrade instead
    code, out = adopt(repo)
    assert code != 0 and "upgrade" in out


def test_adopt_refuses_dirty_tree(tmp_path):
    repo = existing_repo(tmp_path)
    (repo / "wip.txt").write_text("uncommitted\n")
    code, out = adopt(repo)
    assert code != 0 and "uncommitted" in out


# ------------------------------------------------------- project-local gstack

def test_scaffold_pins_gstack_into_the_repo(repo):
    envrc = repo / ".envrc"
    assert envrc.exists() and 'GSTACK_HOME="$PWD/.gstack"' in envrc.read_text()
    attrs = repo / ".gitattributes"
    assert attrs.exists() and "merge=jsonl-append" in attrs.read_text()
    assert ".gstack/sessions/" in (repo / ".gitignore").read_text()


def test_gstack_migrate_unions_personal_store(repo, tmp_path):
    # A personal ~/.gstack with history for this project (slug = dirname "app")
    personal = tmp_path / "home-gstack"
    store = personal / "projects" / "app"
    store.mkdir(parents=True)
    (store / "dev-main-design-1.md").write_text("# Approved design\n")
    (store / "learnings.jsonl").write_text('{"ts":"2026-07-01","note":"a"}\n')
    # Repo store already has one overlapping and one different learning line
    repo_store = repo / ".gstack" / "projects" / "app"
    repo_store.mkdir(parents=True)
    (repo_store / "learnings.jsonl").write_text('{"ts":"2026-07-02","note":"b"}\n')
    code, out = run(repo, "forge.py", "gstack", "migrate",
                    "--source", str(personal), "--repo", str(repo))
    assert code == 0, out
    assert (repo_store / "dev-main-design-1.md").read_text() == "# Approved design\n"
    lines = (repo_store / "learnings.jsonl").read_text().splitlines()
    assert '{"ts":"2026-07-01","note":"a"}' in lines
    assert '{"ts":"2026-07-02","note":"b"}' in lines  # union, no clobber
    # Second run is idempotent: nothing new to merge
    code, out = run(repo, "forge.py", "gstack", "migrate",
                    "--source", str(personal), "--repo", str(repo))
    assert code == 0 and "0 jsonl line(s) merged" in out and "0 file(s) copied" in out


def test_gstack_migrate_fails_clearly_without_store(repo, tmp_path):
    empty = tmp_path / "empty-gstack"
    empty.mkdir()
    code, out = run(repo, "forge.py", "gstack", "migrate",
                    "--source", str(empty), "--repo", str(repo))
    assert code != 0 and "no personal gstack store" in out
