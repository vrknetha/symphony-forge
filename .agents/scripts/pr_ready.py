#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess

from factory_lib import (
    decomposition_state_path,
    dump_json,
    head_sha,
    load_json,
    now_iso,
    repo_root,
    review_dir,
    run_state_path,
    tests_state_path,
    verify_state_path,
)
from forge_cli.assumptions import blocking_for_issue
from forge_cli.roadmap import mark_status

# Commits touching only these paths after evidence was recorded do not
# invalidate it: evidence/plan/doc records, harness machinery and adapters
# (e.g. a forge upgrade mid-task), canon docs, and the preserved prototype.
# Evidence attests to PRODUCT code; everything listed here is not that.
EVIDENCE_PATHS = (
    ".factory/", "plans/", "docs/", ".agents/", ".claude/", ".codex/",
    ".github/", "constitution/", "harness/", "prototype/", ".gstack/",
)
EVIDENCE_FILES = {"forge", "CLAUDE.md", "AGENTS.md", "WORKFLOW.md", "harness.yaml",
                  ".gitignore", ".gitattributes", ".envrc"}

root = repo_root()
run_state = load_json(run_state_path(root), default={})
# Idempotent rerun: after a ship, task-scoped state is archived AND removed
# (parallel branches must converge without .factory conflicts), and run.json
# holds only project fields + the last_shipped marker.
if run_state and not run_state.get("issue_key") and run_state.get("last_shipped"):
    print(f"PR_READY (already shipped {run_state['last_shipped']}; nothing active — "
          "start the next task with intake)")
    raise SystemExit(0)
decomposition = load_json(decomposition_state_path(root), default={})
verify = load_json(verify_state_path(root), default={})
tests = load_json(tests_state_path(root), default={})
missing: list[str] = []
if not run_state:
    missing.append(".factory/run.json")
else:
    if not run_state.get("client_signoff"):
        missing.append(
            "client sign-off (accepted docs/decisions/NNNN-client-signoff.md + record_signoff.py)"
        )
    if run_state.get("plan_status") != "approved":
        missing.append("approved plan status in .factory/run.json")
    if run_state.get("decomposition_status") != "recorded":
        missing.append("recorded decomposition status in .factory/run.json")
issue_key = run_state.get("issue_key", "")
plan_files = list((root / "plans" / "active").glob(f"{issue_key}-*.md")) if issue_key else []
archived_plans = (
    list((root / "plans" / "completed").glob(f"{issue_key}-*.md")) if issue_key else []
)
# Idempotent rerun: a task already gated pr-ready has its plan in plans/completed/.
if not plan_files and not (run_state.get("phase") == "pr-ready" and archived_plans):
    missing.append(
        f"plans/active/{issue_key or '<issue>'}-*.md (save the approved plan with "
        "`forge.py plan save`)"
    )
if not decomposition:
    missing.append(".factory/decomposition.json")
if not verify or not verify.get("ok"):
    missing.append("successful .factory/verify.json")
# The functional check is owed only to user-facing work; the decomposition's
# recorded flag decides — never the dev at gate time. Missing flag = required.
user_facing = bool(decomposition.get("user_facing", True)) if decomposition else True
for kind in ("automated", "functional"):
    entry = tests.get(kind, {}) if tests else {}
    blockers = entry.get("blocking_findings", []) if entry else []
    if not entry:
        if kind == "functional" and not user_facing:
            continue
        missing.append(f".factory/tests.json:{kind}")
    elif blockers or entry.get("status") == "failed":
        missing.append(f"{kind} testing must have no blockers and no failed status")
    elif kind == "functional" and entry.get("score", 0) < 8:
        missing.append("functional testing must have score >= 8")
for aspect in ("quality", "performance", "security"):
    path = review_dir(root) / f"{aspect}.json"
    data = load_json(path, default={})
    blockers = data.get("blocking_findings", []) if data else []
    if not data:
        missing.append(str(path.relative_to(root)))
    elif data.get("score", 0) < 8 or blockers:
        missing.append(f"{aspect} review must be >= 8 with no blockers")

# Assumptions are guided before shipping: the orchestrator confirms, demands
# a fix, or promotes each one — an unguided assumption is an unreviewed call.
unguided = blocking_for_issue(root, issue_key) if issue_key else []
if unguided:
    ids = ", ".join(f"{r['id']} ({r['status']})" for r in unguided)
    missing.append(
        f"orchestrator guidance on {len(unguided)} assumption(s): {ids} — "
        "resolve via `forge.py assumptions resolve <id> --status confirmed|promoted --notes ...`"
    )

# Provenance: every evidence artifact carries the commit it was recorded at;
# all must agree, and no code may have changed since (evidence-only commits ok).
# Decomposition is a plan-side artifact — recorded BEFORE implementation by
# design — so it must be stamped but is exempt from same-commit/freshness.
head = head_sha(root)
if decomposition and not decomposition.get("commit") and head:
    missing.append(
        "commit provenance on: decomposition (re-record with current tooling)"
    )
stamps: dict[str, str | None] = {}
for label, data in (
    ("verify", verify),
    ("tests", tests),
):
    if data:
        stamps[label] = data.get("commit")
for aspect in ("quality", "performance", "security"):
    data = load_json(review_dir(root) / f"{aspect}.json", default={})
    if data:
        stamps[f"review:{aspect}"] = data.get("commit")
unstamped = [label for label, sha in stamps.items() if not sha]
if unstamped and head:
    missing.append(
        f"commit provenance on: {', '.join(unstamped)} (re-record with current tooling — "
        "artifacts without a commit stamp are unverifiable evidence)"
    )
elif head and stamps:
    distinct = {sha for sha in stamps.values()}
    if len(distinct) > 1:
        missing.append(
            f"consistent evidence: artifacts span commits {sorted(s[:8] for s in distinct)} — "
            "re-record so all evidence reflects one code state"
        )
    else:
        stamp = distinct.pop()
        if stamp != head:
            proc = subprocess.run(
                ["git", "diff", "--name-only", f"{stamp}..{head}"],
                cwd=root, capture_output=True, text=True,
            )
            if proc.returncode != 0:
                missing.append(
                    f"evidence commit {stamp[:8]} is unknown to this repo — re-record"
                )
            else:
                code_changes = [
                    f for f in proc.stdout.splitlines()
                    if f and not f.startswith(EVIDENCE_PATHS) and f not in EVIDENCE_FILES
                ]
                if code_changes:
                    missing.append(
                        f"fresh evidence: code changed since it was recorded at {stamp[:8]} "
                        f"({', '.join(code_changes[:5])}) — rerun verify/tests/reviews"
                    )

if missing:
    print("PR not ready:")
    for item in missing:
        print(f"- {item}")
    raise SystemExit(1)

# Move the plan to plans/completed/ FIRST, so the run state we persist and
# archive references the plan's final location, not a path about to vanish.
completed = root / "plans" / "completed"
completed.mkdir(parents=True, exist_ok=True)
for plan_file in plan_files:
    shutil.move(str(plan_file), completed / plan_file.name)
    run_state["plan_file"] = (completed / plan_file.name).relative_to(root).as_posix()

run_state["phase"] = "pr-ready"
run_state["review_status"] = "passed"
run_state["tests_status"] = "passed"
run_state["updated_at"] = now_iso()
dump_json(run_state_path(root), run_state)

# Archive what was decided and built: run artifacts to .factory/history/<issue>.
# This is the durable "what was built" record.
history = root / ".factory" / "history" / issue_key
history.mkdir(parents=True, exist_ok=True)
for artifact in (run_state_path(root), decomposition_state_path(root),
                 verify_state_path(root), tests_state_path(root)):
    if artifact.exists():
        shutil.copy2(artifact, history / artifact.name)
if review_dir(root).is_dir():
    shutil.copytree(review_dir(root), history / "reviews", dirs_exist_ok=True)

# Archived means REMOVED from the working tree: task-scoped state left behind
# is exactly what conflicts when parallel story branches merge (decision 0002
# follow-up from the parallel pilot). History keeps the full record.
for artifact in (decomposition_state_path(root), verify_state_path(root),
                 tests_state_path(root), root / ".factory" / "grills" / "plan.json"):
    if artifact.exists():
        artifact.unlink()
if review_dir(root).is_dir():
    shutil.rmtree(review_dir(root))
project_state = {
    k: run_state[k]
    for k in ("project", "client_signoff", "client_signoff_record", "client_signoff_at")
    if k in run_state
}
project_state.update({"last_shipped": issue_key, "phase": "shipped", "updated_at": now_iso()})
dump_json(run_state_path(root), project_state)

if mark_status(root, issue_key, "done",
               completed_at=now_iso(), history=f".factory/history/{issue_key}/"):
    print(f"Roadmap: {issue_key} marked done")
print(f"PR_READY (archived to .factory/history/{issue_key}/, plan moved to plans/completed/, "
      "task-scoped .factory state cleaned)")
print(f"Now commit the archive — evidence that isn't committed isn't merged:")
print(f"  git add -A && git commit -m \"chore({issue_key}): ship — evidence archived\"")
