#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True)
    return Path(out.stdout.strip())


def factory_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / ".factory"


def run_state_path(root: Path | None = None) -> Path:
    return factory_dir(root) / "run.json"


def decomposition_state_path(root: Path | None = None) -> Path:
    return factory_dir(root) / "decomposition.json"


def verify_state_path(root: Path | None = None) -> Path:
    return factory_dir(root) / "verify.json"


def tests_state_path(root: Path | None = None) -> Path:
    return factory_dir(root) / "tests.json"


def review_dir(root: Path | None = None) -> Path:
    return factory_dir(root) / "reviews"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def gate(
    root: Path,
    *,
    signoff: bool = False,
    approved_plan: bool = False,
    decomposition: bool = False,
) -> dict[str, Any]:
    """The factory precondition matrix, in one place.

    Every artifact-writing script calls this with the preconditions its phase
    requires. Missing run state always fails — no gate is skippable by
    deleting .factory/run.json.
    """
    state = load_json(run_state_path(root), default={})
    if not state:
        raise SystemExit("Missing .factory/run.json. Run intake first.")
    if signoff and not state.get("client_signoff"):
        raise SystemExit(
            "Client sign-off required first. Get docs/decisions/NNNN-client-signoff.md "
            "accepted (non-empty confirmed_by), then run "
            "`python3 .agents/scripts/record_signoff.py`."
        )
    issue = state.get("issue_key", "")
    if approved_plan:
        plan_files = list((root / "plans" / "active").glob(f"{issue}-*.md")) if issue else []
        if state.get("plan_status") != "approved" or not plan_files:
            raise SystemExit(
                "An approved, saved plan is required first "
                f"(plans/active/{issue or '<issue>'}-*.md via `forge.py plan save`)."
            )
    if decomposition:
        if (
            state.get("decomposition_status") != "recorded"
            or not decomposition_state_path(root).exists()
        ):
            raise SystemExit(
                "Recorded decomposition is required first "
                "(record_decomposition_from_json.py after plan approval)."
            )
    return state


SCHEMA_TYPES = {"str": str, "int": int, "bool": bool, "list": list, "dict": dict}


def schema_path(root: Path, name: str) -> Path:
    return root / ".agents" / "schemas" / f"{name}.json"


def validate_payload(root: Path, name: str, payload: dict) -> None:
    """The determinism contract's front door: refuse any externally-authored
    artifact that does not match its .agents/schemas/ spec, including a
    generated_by value outside the pinned allowlist. Extra keys are allowed."""
    path = schema_path(root, name)
    schema = json.loads(path.read_text())
    problems: list[str] = []

    def check(field: str, kind: str, value: Any) -> None:
        ok = isinstance(value, SCHEMA_TYPES[kind])
        if kind != "bool" and isinstance(value, bool):
            ok = False
        if not ok:
            problems.append(f"'{field}' must be {kind}")

    for field, kind in schema.get("required", {}).items():
        if field not in payload:
            problems.append(f"missing required '{field}' ({kind})")
        else:
            check(field, kind, payload[field])
    for field, kind in schema.get("optional", {}).items():
        if field in payload:
            check(field, kind, payload[field])
    allowed = schema.get("generated_by", [])
    generator = payload.get("generated_by")
    if allowed and generator is not None and generator not in allowed:
        problems.append(
            f"generated_by {generator!r} is not pinned for this artifact — allowed: "
            f"{', '.join(allowed)}. Adopting a new tool is a harness PR "
            f"(harness.yaml + the schema file), never a local choice."
        )
    if problems:
        raise SystemExit(
            f"REFUSED by .agents/schemas/{path.name}:\n- " + "\n- ".join(problems)
        )


def head_sha(root: Path | None = None) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root or repo_root(),
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def require_grill(
    root: Path,
    gate: str,
    prefixes: tuple[str, ...],
    ignore_names: tuple[str, ...] = (),
) -> None:
    """Handover gates call this: a fresh, passing grill or no passage.

    `ignore_names` filters expected exhaust from the staleness check (e.g.
    the client-signoff record itself, which is created AFTER the grill)."""
    path = factory_dir(root) / "grills" / f"{gate}.json"
    data = load_json(path, default={})
    if not data:
        raise SystemExit(
            f"Handover grill required first: interrogate the handover for gaps and "
            f"contradictions per .agents/prompts/griller.md, resolve findings, then record "
            f"`python3 .agents/scripts/record_grill_from_json.py --gate {gate}`."
        )
    if data.get("verdict") != "pass":
        raise SystemExit(
            f".factory/grills/{gate}.json verdict is {data.get('verdict')!r} — resolve the "
            "recorded findings and re-grill; this gate needs a pass."
        )
    if not data.get("commit") and head_sha(root):
        raise SystemExit(
            f".factory/grills/{gate}.json has no commit stamp — re-record with current tooling."
        )
    stale = [
        f for f in changed_since(root, data.get("commit") or "", prefixes)
        if not any(token in Path(f).name for token in ignore_names)
    ]
    if stale:
        raise SystemExit(
            f"the {gate} grill is STALE — handover docs changed since it ran: "
            f"{', '.join(stale[:5])}. Re-run the grill against the current docs."
        )


def changed_since(root: Path, stamp: str, prefixes: tuple[str, ...]) -> list[str]:
    """Committed files under `prefixes` changed between `stamp` and HEAD.

    Returns ["<unknown commit>"] when the stamp is not in this repo's history,
    so callers treat an unverifiable stamp as stale rather than fresh."""
    head = head_sha(root)
    if not head or not stamp or stamp == head:
        return []
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{stamp}..{head}"],
        cwd=root, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return [f"<commit {stamp[:8]} unknown to this repo>"]
    return [f for f in proc.stdout.splitlines() if f.startswith(prefixes)]


def read_hook_input() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def branch_name(root: Path | None = None) -> str:
    out = subprocess.run(["git", "branch", "--show-current"], cwd=root or repo_root(), check=True, capture_output=True, text=True)
    return out.stdout.strip()


def infer_issue_key(value: str) -> str | None:
    match = re.search(r"([A-Z][A-Z0-9]+-\d+)", value)
    return match.group(1) if match else None


def ensure_issue_key(explicit: str | None = None, root: Path | None = None) -> str:
    # An explicitly passed key is accepted as-is (GitHub issue numbers, Jira,
    # plain slugs) as long as it is filesystem/branch-safe.
    if explicit and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", explicit.strip()):
        return explicit.strip()
    candidates = [explicit or "", os.environ.get("LINEAR_ISSUE_KEY", ""), branch_name(root)]
    for candidate in candidates:
        key = infer_issue_key(candidate)
        if key:
            return key
    raise SystemExit(
        "Unable to determine an issue key. Pass --issue <key> (e.g. ENG-123, GH-42, 42), "
        "set LINEAR_ISSUE_KEY, or use a branch like feat/ENG-123-slug."
    )


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return value or "task"


def run_cmd(command: str, cwd: Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=cwd or repo_root(), shell=True, capture_output=True, text=True)
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
