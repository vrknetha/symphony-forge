#!/usr/bin/env python3
"""Record a handover grill (.factory/grills/<gate>.json).

A grill is the adversarial gap/contradiction interrogation run BEFORE a
handover gate (.agents/prompts/griller.md): `signoff` protects the client->PM
gate, `epics` protects the PM->EM gate. The downstream gate scripts
(record_signoff.py, forge roadmap import) refuse without a fresh, passing
grill — recording a verdict here is what makes "we checked for gaps" a fact
instead of a claim. A `blocked` verdict is recordable (it is the audit trail
of what blocked) but never satisfies a gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from factory_lib import dump_json, head_sha, now_iso, repo_root, validate_payload

VERDICTS = {"pass", "blocked"}

parser = argparse.ArgumentParser(description="Record a handover grill from structured JSON")
parser.add_argument("--gate", required=True, choices=["signoff", "epics"])
parser.add_argument("--input", help="Path to grill JSON. If omitted, read from stdin.")
args = parser.parse_args()

if args.input:
    payload = json.loads(Path(args.input).read_text())
else:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected JSON on stdin or via --input")
    payload = json.loads(raw)

root = repo_root()
validate_payload(root, "grill", payload)
if payload.get("gate") != args.gate:
    raise SystemExit(f"payload gate {payload.get('gate')!r} does not match --gate {args.gate}")
if payload.get("verdict") not in VERDICTS:
    raise SystemExit(f"verdict must be one of {', '.join(sorted(VERDICTS))}")
unresolved = (len(payload["gaps"]) + len(payload["contradictions"])) - len(payload["resolutions"])
if payload["verdict"] == "pass" and unresolved > 0:
    raise SystemExit(
        f"verdict 'pass' with {unresolved} unresolved finding(s) — every gap/contradiction "
        "needs a resolution (doc edit or decision record) or the verdict is 'blocked'."
    )
payload["recorded_at"] = now_iso()
payload["commit"] = head_sha(root)
dest = root / ".factory" / "grills" / f"{args.gate}.json"
dump_json(dest, payload)
print(f"Recorded {args.gate} grill: {payload['verdict']} "
      f"({len(payload['gaps'])} gap(s), {len(payload['contradictions'])} contradiction(s), "
      f"{len(payload['resolutions'])} resolution(s))")
