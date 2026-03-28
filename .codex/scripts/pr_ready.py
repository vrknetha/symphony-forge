#!/usr/bin/env python3
from __future__ import annotations

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
    if run_state.get("plan_status") != "approved":
        missing.append("approved plan status in .factory/run.json")
    if run_state.get("decomposition_status") != "recorded":
        missing.append("recorded decomposition status in .factory/run.json")
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

run_state["phase"] = "pr-ready"
run_state["review_status"] = "passed"
run_state["tests_status"] = "passed"
run_state["updated_at"] = now_iso()
dump_json(run_state_path(root), run_state)
print("PR_READY")
