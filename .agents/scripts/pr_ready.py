#!/usr/bin/env python3
from __future__ import annotations

import shutil

from factory_lib import (
    decomposition_state_path,
    dump_json,
    load_json,
    now_iso,
    repo_root,
    review_dir,
    run_state_path,
    tests_state_path,
    verify_state_path,
)

root = repo_root()
run_state = load_json(run_state_path(root), default={})
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
for kind in ("automated", "functional"):
    entry = tests.get(kind, {}) if tests else {}
    blockers = entry.get("blocking_findings", []) if entry else []
    if not entry:
        missing.append(f".factory/tests.json:{kind}")
    elif blockers or entry.get("status") == "failed":
        missing.append(f"{kind} testing must have no blockers and no failed status")
    elif kind == "functional" and entry.get("score", 0) < 8:
        missing.append("functional testing must have score >= 8")
for aspect in ("quality", "performance", "security"):
    path = review_dir(root) / f"{aspect}.json"
    data = load_json(path, default={})
    blockers = data.get("blocking_findings", data.get("blocking", [])) if data else []
    if not data:
        missing.append(str(path.relative_to(root)))
    elif data.get("score", 0) < 8 or blockers:
        missing.append(f"{aspect} review must be >= 8 with no blockers")

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
    run_state["plan_file"] = str((completed / plan_file.name).relative_to(root))

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
print(f"PR_READY (archived to .factory/history/{issue_key}/, plan moved to plans/completed/)")
