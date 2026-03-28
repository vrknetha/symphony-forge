#!/usr/bin/env python3
from __future__ import annotations

import json

from factory_lib import (
    decomposition_state_path,
    load_json,
    repo_root,
    review_dir,
    run_state_path,
    tests_state_path,
    verify_state_path,
)

root = repo_root()
run_state = load_json(run_state_path(root), default={})
if not run_state:
    print(json.dumps({"continue": True}))
    raise SystemExit(0)

phase = run_state.get("phase")
if phase in {"planning", "decomposing", "awaiting-approval", "blocked", "pr-ready", "done"}:
    print(json.dumps({"continue": True}))
    raise SystemExit(0)

if not load_json(decomposition_state_path(root), default={}):
    print(json.dumps({"decision": "block", "reason": "Record decomposition before ending the turn."}))
    raise SystemExit(0)

verify = load_json(verify_state_path(root), default={})
if not verify or not verify.get("ok"):
    print(json.dumps({"decision": "block", "reason": "Run deterministic verification before ending the turn."}))
    raise SystemExit(0)

tests = load_json(tests_state_path(root), default={})
missing_tests = [kind for kind in ("automated", "functional") if not tests.get(kind)]
blocked_tests = []
for kind in ("automated", "functional"):
    entry = tests.get(kind, {})
    if not entry:
        continue
    blockers = entry.get("blocking_findings", [])
    if blockers or entry.get("status") == "failed" or (kind == "functional" and entry.get("score", 0) < 8):
        blocked_tests.append(kind)
if missing_tests:
    print(json.dumps({"decision": "block", "reason": f"Missing test artifacts: {', '.join(missing_tests)}."}))
    raise SystemExit(0)
if blocked_tests:
    print(json.dumps({"decision": "block", "reason": f"Testing gates not met: {', '.join(blocked_tests)}."}))
    raise SystemExit(0)

missing_reviews = []
blocked_reviews = []
for aspect in ("quality", "performance", "security"):
    review = load_json(review_dir(root) / f"{aspect}.json", default={})
    if not review:
        missing_reviews.append(aspect)
        continue
    blockers = review.get("blocking_findings", review.get("blocking", []))
    if blockers or review.get("score", 0) < 8:
        blocked_reviews.append(aspect)

if missing_reviews:
    print(json.dumps({"decision": "block", "reason": f"Missing review artifacts: {', '.join(missing_reviews)}."}))
    raise SystemExit(0)
if blocked_reviews:
    print(json.dumps({"decision": "block", "reason": f"Review gates not met: {', '.join(blocked_reviews)}."}))
    raise SystemExit(0)

print(json.dumps({"continue": True}))
