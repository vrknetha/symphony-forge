#!/usr/bin/env python3
"""forge — bootstrap a new client repo from this harness, and manage decision records.

Usage:
  python3 .agents/scripts/forge.py init --name <project> [--target <dir>] [--stack nestjs-react] [--force]
  python3 .agents/scripts/forge.py decision new <slug> [--title <title>] [--repo <dir>]
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

from factory_lib import dump_json, load_json, now_iso, repo_root, run_state_path, slugify

COPY_TREES = [".agents", ".claude", "constitution", "harness", ".github"]
COPY_CODEX = ["config.toml", "hooks.json"]  # + agents/ dir
COPY_FILES = ["harness.yaml", ".gitignore", "WORKFLOW.md", "CLAUDE.md", "forge"]
DOC_CONTRACTS = [
    ("docs/product/README.md", "docs/product/README.md"),
    ("docs/architecture/README.md", "docs/architecture/README.md"),
    ("docs/decisions/README.md", "docs/decisions/README.md"),
    ("docs/FACTORY.md", "docs/FACTORY.md"),
    ("docs/QUALITY.md", "docs/QUALITY.md"),
    ("docs/harness-philosophy.md", "docs/harness-philosophy.md"),
    ("docs/degraded-mode.md", "docs/degraded-mode.md"),
    ("docs/context/README.md", "docs/context/README.md"),
]

DISCOVERY_TEMPLATE = """# Discovery — {name}

Phase 0a. Lightweight on purpose: no .factory ceremony until client sign-off.

## Problem
<!-- What hurts, for whom, observed where? -->

## Stakeholders
<!-- Client-side names and roles; who signs off? -->

## Client-approved decisions
<!-- Each becomes docs/decisions/NNNN-<slug>.md via:
     python3 .agents/scripts/forge.py decision new <slug> -->
- [ ]

## Prototype notes (phase 0b)
<!-- What was shown, what the client said, what changed. -->
"""

PROTOTYPE_README = """# Prototype — preserved reference

The phase-0b prototype that earned client sign-off lives here permanently:
code, screenshots, and walkthrough notes. It is the record of what the client
saw and approved, and the UX reference when the UI/UX evolves later.

Rules:
- **Reference forever, imported never.** Production code must not import,
  link, or build anything from this directory.
- Do not "clean it up" to production standards — its value is fidelity to
  what was approved, not code quality.
- When a future UI/UX change is discussed, start here: what did the client
  originally react to, and which decision records came out of it?
"""

DECISION_TEMPLATE = """---
status: proposed
confirmed_by: ""
date: {date}
---

# {title}

## Context
<!-- Why this decision was needed; the forces at play. -->

## Decision
<!-- What was decided, in one or two sentences. -->

## Consequences
<!-- What follows: tradeoffs accepted, doors closed, work implied. -->
"""


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def cmd_init(args: argparse.Namespace) -> None:
    root = repo_root()
    target = Path(args.target or args.name).resolve()
    if target.exists() and any(target.iterdir()):
        if not args.force:
            fail(
                f"target {target} is not empty. forge init has no merge mode; "
                "use --force to overwrite an existing scaffold."
            )
    target.mkdir(parents=True, exist_ok=True)

    for tree in COPY_TREES:
        src = root / tree
        if src.exists():
            shutil.copytree(src, target / tree, dirs_exist_ok=True)
    (target / ".codex").mkdir(exist_ok=True)
    for name in COPY_CODEX:
        shutil.copy2(root / ".codex" / name, target / ".codex" / name)
    shutil.copytree(root / ".codex" / "agents", target / ".codex" / "agents", dirs_exist_ok=True)
    if (root / ".codex" / "skills").is_dir():
        shutil.copytree(root / ".codex" / "skills", target / ".codex" / "skills", dirs_exist_ok=True)
    for name in COPY_FILES:
        src = root / name
        if src.exists():
            shutil.copy2(src, target / name)
    for src_rel, dst_rel in DOC_CONTRACTS:
        src = root / src_rel
        if src.exists():
            dst = target / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Pin the vendored constitution to its source commit.
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "unknown"
    (target / "constitution" / "VENDORED_FROM").write_text(
        f"symphony-forge @ {commit}\nUpdate by re-vendoring from the harness repo; do not edit in place.\n"
    )

    brief_src = root / "harness" / "nestjs-react" / "BRIEF_TEMPLATE.md"
    brief_dst = target / "docs" / "product" / "BRIEF.md"
    brief_dst.parent.mkdir(parents=True, exist_ok=True)
    if brief_src.exists():
        shutil.copy2(brief_src, brief_dst)
    (target / "docs" / "product" / "DISCOVERY.md").write_text(
        DISCOVERY_TEMPLATE.format(name=args.name)
    )
    (target / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (target / "prototype").mkdir(parents=True, exist_ok=True)
    (target / "prototype" / "README.md").write_text(PROTOTYPE_README)
    for sub in ("active", "completed", "debt"):
        plan_dir = target / "plans" / sub
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / ".gitkeep").touch()
    (target / ".factory" / "reviews").mkdir(parents=True, exist_ok=True)
    dump_json(
        target / ".factory" / "run.json",
        {"project": args.name, "client_signoff": False, "created_at": now_iso()},
    )

    agents_md = (root / "AGENTS.md").read_text().replace("Symphony Forge", args.name, 1)
    (target / "AGENTS.md").write_text(agents_md)

    if not (target / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)

    print(f"Scaffolded {args.name} at {target}")
    print("Next steps:")
    print("  1. Fill docs/product/DISCOVERY.md (phase 0a) and BRIEF.md")
    print("  2. Prototype (phase 0b), then: forge.py decision new client-signoff")
    print("  3. After the record is accepted: python3 .agents/scripts/record_signoff.py")
    print(f"  4. Generate the {args.stack} workspace via harness/{args.stack}/SCAFFOLD_PROMPT.md")


def cmd_decision_new(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    decisions = base / "docs" / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    taken = set()
    for existing in decisions.glob("[0-9][0-9][0-9][0-9]-*.md"):
        taken.add(int(existing.name[:4]))
    number = 1
    while number in taken:
        number += 1
    slug = args.slug.strip().lower().replace(" ", "-")
    path = decisions / f"{number:04d}-{slug}.md"
    title = args.title or slug.replace("-", " ").title()
    path.write_text(
        DECISION_TEMPLATE.format(date=datetime.date.today().isoformat(), title=title)
    )
    print(f"Created {path}")
    print(
        "Reminder: status: accepted requires a non-empty confirmed_by (a human), "
        "and the commit adding it should carry a `Confirmed-by:` trailer."
    )


def _pending_context(base: Path) -> list[str]:
    """Pending = ledgered-pending PLUS unscanned/changed inbox files on disk.

    The single source of truth for 'is there unharvested context' — used by
    the plan-approval gate and the phase engine so they can never disagree.
    """
    context_dir, ledger_path = _context_paths(base)
    ledger = load_json(ledger_path, default={"files": {}})
    pending = [
        rel for rel, e in ledger.get("files", {}).items() if e.get("status") == "pending"
    ]
    if context_dir.is_dir():
        for f in _context_files(context_dir):
            rel = str(f.relative_to(context_dir))
            entry = ledger.get("files", {}).get(rel)
            if entry is None or (
                entry.get("status") != "pending" and entry.get("sha256") != _sha256(f)
            ):
                pending.append(f"{rel} (unscanned)")
    return pending


def cmd_next(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    factory = base / ".factory"
    pending_ctx = len(_pending_context(base))
    steps: list[str] = []

    def phase(label: str) -> None:
        issue = state.get("issue_key")
        suffix = f" ({issue} — {state.get('title')})" if issue else ""
        print(f"PHASE: {label}{suffix}")

    if pending_ctx:
        steps.append(
            f"Harvest {pending_ctx} pending docs/context/ file(s) first "
            "(.agents/prompts/harvester.md; then forge.py context mark ...)"
        )
    if not state:
        phase("uninitialized")
        steps.append("New project? scaffold with: forge.py init --name <project> --target <dir>")
        steps.append("Existing project, new feature? this repo has no .factory/run.json — "
                     "run: python3 .agents/scripts/intake.py --issue <KEY> --title \"<title>\"")
    elif not state.get("client_signoff"):
        phase("discovery/prototype (0a/0b)")
        steps.append("Fill docs/product/DISCOVERY.md and BRIEF.md; prototype freely (no ceremony)")
        steps.append("Capture client decisions: forge.py decision new <slug>")
        steps.append("When the client confirms: forge.py decision new client-signoff, "
                     "set status: accepted + confirmed_by, then run record_signoff.py")
    elif not state.get("issue_key"):
        phase("signed off — no active task")
        steps.append("Start a task: python3 .agents/scripts/intake.py --issue <KEY> --title \"<title>\"")
    elif state.get("plan_status") != "approved":
        phase("planning")
        steps.append("Plan per .agents/prompts/planner.md — Claude Code plan mode (default, "
                     "exploration via Codex read-only) or the planner-high Codex agent")
        steps.append("Record new decisions as you go: forge.py decision new <slug>")
        steps.append("On approval: forge.py plan save --from <plan-file>")
    elif state.get("decomposition_status") != "recorded":
        phase("decomposing")
        steps.append("Run docs-decomposer (.agents/prompts/decomposer.md), then "
                     "record_decomposition_from_json.py and "
                     "update_run.py --phase implementing --decomposition-status recorded")
    else:
        tests = load_json(factory / "tests.json", default={})
        verify = load_json(factory / "verify.json", default={})
        reviews_missing = [
            a for a in ("quality", "performance", "security")
            if not load_json(factory / "reviews" / f"{a}.json", default={})
        ]
        if not tests.get("automated"):
            phase("implementing")
            steps.append("Implement the next bounded leaf task via /codex:rescue --background "
                         "(.agents/prompts/implementer.md)")
            steps.append("Then run automated-tester and record: "
                         "record_test_from_json.py --kind automated --input <json>")
        elif not verify.get("ok"):
            phase("verifying")
            steps.append("Run: python3 .agents/scripts/verify.py")
        elif reviews_missing:
            phase("reviewing")
            steps.append(f"Spawn review subagents for: {', '.join(reviews_missing)}; record via "
                         "record_review_from_json.py (escalate flagged tasks to autoreview "
                         "per harness.yaml)")
        elif not tests.get("functional"):
            phase("functional-check")
            steps.append("Run functional-checker and record: "
                         "record_test_from_json.py --kind functional --input <json>")
        else:
            phase("ready for PR gate")
            steps.append("Run: python3 .agents/scripts/pr_ready.py (archives the task; merge stays manual)")
            steps.append("Next task afterwards: intake.py --issue <KEY> --title \"<title>\"")
    proposed = len(list((base / ".agents" / "skills" / "proposed").glob("*.md")))
    if proposed:
        steps.append(f"(Also: {proposed} proposed skill(s) await human review in "
                     ".agents/skills/proposed/)")
    print("NEXT:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")


def _context_paths(base: Path) -> tuple[Path, Path]:
    context_dir = base / "docs" / "context"
    return context_dir, context_dir / "ledger.json"


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _context_files(context_dir: Path) -> list[Path]:
    # Only the inbox's own top-level README and ledger are infrastructure;
    # a dumped subdirectory may legitimately contain files with those names.
    skip = {"README.md", "ledger.json"}
    return sorted(
        p for p in context_dir.rglob("*")
        if p.is_file()
        and str(p.relative_to(context_dir)) not in skip
        and not p.name.startswith(".")
    )


def cmd_context_scan(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    context_dir, ledger_path = _context_paths(base)
    context_dir.mkdir(parents=True, exist_ok=True)
    ledger = load_json(ledger_path, default={"files": {}})
    drift: list[str] = []
    for f in _context_files(context_dir):
        rel = str(f.relative_to(context_dir))
        digest = _sha256(f)
        entry = ledger["files"].get(rel)
        if entry is None:
            drift.append(f"new: {rel}")
            ledger["files"][rel] = {
                "sha256": digest, "added": now_iso(), "status": "pending",
                "outputs": [], "notes": "",
            }
        elif entry.get("sha256") != digest:
            drift.append(f"changed (re-pending): {rel}")
            entry.update({"sha256": digest, "status": "pending", "updated": now_iso()})
    on_disk = {str(f.relative_to(context_dir)) for f in _context_files(context_dir)}
    for rel in sorted(set(ledger["files"]) - on_disk):
        drift.append(f"missing (marked removed): {rel}")
        ledger["files"][rel]["status"] = "removed"
    if args.check:
        if drift:
            print("Context ledger out of sync (run `forge.py context scan` and commit):")
            for line in drift:
                print(f"- {line}")
            raise SystemExit(1)
    else:
        dump_json(ledger_path, ledger)
        for line in drift:
            print(line)
    counts: dict[str, int] = {}
    for entry in ledger["files"].values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "empty"
    print(f"context ledger — {summary}")
    if counts.get("pending"):
        print("Harvest pending files per .agents/prompts/harvester.md.")


def cmd_context_list(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    _, ledger_path = _context_paths(base)
    ledger = load_json(ledger_path, default={"files": {}})
    for rel, entry in sorted(ledger["files"].items()):
        if args.pending and entry["status"] != "pending":
            continue
        outputs = f" -> {', '.join(entry['outputs'])}" if entry.get("outputs") else ""
        print(f"[{entry['status']:<9}] {rel}{outputs}")


def cmd_context_mark(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    _, ledger_path = _context_paths(base)
    ledger = load_json(ledger_path, default={"files": {}})
    entry = ledger["files"].get(args.file)
    if entry is None:
        fail(f"{args.file} is not in the ledger — run `forge.py context scan` first")
    status = "harvested" if args.harvested else "ignored"
    outputs = args.outputs or []
    escaping = []
    for o in outputs:
        candidate = (base / o).resolve()
        if Path(o).is_absolute() or not candidate.is_relative_to(base):
            escaping.append(o)
    if escaping:
        fail(
            f"outputs must be repo-relative paths inside the repo: {', '.join(escaping)}"
        )
    missing = [o for o in outputs if not (base / o).exists()]
    if missing:
        fail(f"outputs do not exist: {', '.join(missing)} — create them before marking")
    if args.harvested and not args.outputs:
        fail("--harvested requires --outputs (what did the harvest produce?)")
    if args.ignored and not (args.notes or "").strip():
        fail("--ignored requires --notes (why is this context irrelevant? auditable rationale)")
    entry.update({
        "status": status,
        "marked_at": now_iso(),
        "outputs": args.outputs or [],
        "notes": args.notes or entry.get("notes", ""),
    })
    dump_json(ledger_path, ledger)
    print(f"{args.file}: {status}")


def cmd_plan_save(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    if not state or not state.get("client_signoff"):
        fail(
            "plan approval requires an initialized run with client sign-off. Run "
            "intake, get docs/decisions/NNNN-client-signoff.md accepted, run "
            "record_signoff.py, then save the plan."
        )
    pending = _pending_context(base)
    if pending:
        fail(
            f"{len(pending)} docs/context/ file(s) are unharvested: {', '.join(pending[:5])}"
            f"{'…' if len(pending) > 5 else ''}. Plans must not be approved over pending "
            "context — run `forge.py context scan`, harvest per .agents/prompts/harvester.md "
            "or mark irrelevant ones `forge.py context mark <file> --ignored`, then save."
        )
    issue = args.issue or state.get("issue_key")
    if not issue:
        fail("no --issue given and no issue_key in .factory/run.json (run intake first)")
    source = Path(args.source).expanduser()
    if not source.is_file():
        fail(f"plan source {source} not found — pass the approved plan file via --from")
    title = args.title or state.get("title") or issue
    dest_dir = base / "plans" / "active"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{issue}-{slugify(title)}.md"
    header = (
        f"---\nissue: {issue}\ntitle: {title}\nstatus: approved\nsaved: {now_iso()}\n---\n\n"
    )
    dest.write_text(header + source.read_text())
    if state:
        state["plan_status"] = "approved"
        state["plan_file"] = str(dest.relative_to(base))
        state["updated_at"] = now_iso()
        dump_json(run_state_path(base), state)
    print(f"Plan saved to {dest.relative_to(base)} (plan_status: approved)")
    print(
        "Decisions made while planning must exist as docs/decisions/ records "
        "(forge.py decision new <slug>) and be referenced in the plan."
    )


def cmd_plan_assume(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    state = load_json(run_state_path(base), default={})
    issue = args.issue or state.get("issue_key")
    if not issue:
        fail("no --issue given and no issue_key in .factory/run.json (run intake first)")
    plans = sorted((base / "plans" / "active").glob(f"{issue}-*.md"))
    if not plans:
        fail(
            f"no active plan for {issue} (plans/active/{issue}-*.md). Save the approved "
            "plan first with `forge.py plan save` — assumptions attach to a plan."
        )
    plan = plans[-1]
    text = plan.read_text()
    heading = "## Implementation Assumptions"
    entry = f"- {datetime.date.today().isoformat()}: {args.text.strip()}\n"
    if heading in text:
        text = text.rstrip("\n") + "\n" + entry
    else:
        text = (
            text.rstrip("\n")
            + f"\n\n{heading}\n\n"
            "<!-- Made during implementation, NOT part of the approved plan. "
            "Dev: review these before merge; promote any that matter to docs/decisions/. -->\n"
            + entry
        )
    plan.write_text(text)
    print(f"Assumption recorded in {plan.relative_to(base)}")
    print("Dev reviews these before merge; promote durable ones: forge.py decision new <slug>")


def _check(name: str, ok: bool, detail: str, fix: str, required: bool = True) -> dict:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix, "required": required}


def _run_quiet(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def cmd_doctor(args: argparse.Namespace) -> None:
    home = Path.home()
    checks: list[dict] = []

    def which(binary: str) -> str | None:
        return shutil.which(binary)

    # Core toolchain
    checks.append(_check(
        "git", which("git") is not None, which("git") or "not on PATH",
        "https://git-scm.com — or `xcode-select --install` on macOS"))
    node = which("node")
    node_ok, node_ver = (False, "not on PATH")
    if node:
        code, out = _run_quiet([node, "--version"])
        node_ver = out
        node_ok = code == 0 and out.lstrip("v").split(".")[0].isdigit() and int(out.lstrip("v").split(".")[0]) >= 20
    checks.append(_check("node >= 20", node_ok, node_ver, "install Node 20+ (https://nodejs.org or `brew install node`)"))
    checks.append(_check(
        "pnpm", which("pnpm") is not None, which("pnpm") or "not on PATH",
        "`npm install -g pnpm` (needed once the nx workspace exists)", required=False))
    checks.append(_check(
        "docker", which("docker") is not None, which("docker") or "not on PATH",
        "Docker Desktop (needed once the nx workspace exists)", required=False))

    # Codex — the execution plane
    if not which("codex") and args.fix and which("npm"):
        print("[fix ] installing @openai/codex ...")
        _run_quiet(["npm", "install", "-g", "@openai/codex"])
    codex = which("codex")
    if codex:
        code, out = _run_quiet([codex, "login", "status"])
        logged_in = code == 0 and "not logged in" not in out.lower()
        checks.append(_check("codex CLI + login", logged_in, out.splitlines()[-1] if out else "unknown",
                             "`codex login` (ChatGPT subscription or API key — login is always manual)"))
    else:
        checks.append(_check("codex CLI + login", False, "not on PATH",
                             "`npm install -g @openai/codex` then `codex login` — or rerun with --fix"))

    # Claude Code — the coordination plane
    claude_bin = which("claude")
    checks.append(_check(
        "claude CLI", claude_bin is not None, claude_bin or "not on PATH",
        "https://claude.ai/code — install Claude Code"))

    def _install_claude_plugin(marketplace_url: str, plugin_ref: str) -> None:
        _run_quiet([claude_bin, "plugin", "marketplace", "add", marketplace_url])
        _run_quiet([claude_bin, "plugin", "install", plugin_ref])

    plugin = home / ".claude" / "plugins" / "cache" / "openai-codex" / "codex"
    if not plugin.is_dir() and args.fix and claude_bin:
        print("[fix ] installing codex-plugin-cc ...")
        _install_claude_plugin("https://github.com/openai/codex-plugin-cc", "codex@openai-codex")
    checks.append(_check(
        "codex-plugin-cc", plugin.is_dir(), str(plugin) if plugin.is_dir() else "not installed",
        "`claude plugin marketplace add https://github.com/openai/codex-plugin-cc && "
        "claude plugin install codex@openai-codex` — or rerun with --fix "
        "(leave the review gate disabled)"))

    # Skills
    gstack = home / ".claude" / "skills" / "gstack"
    if not gstack.is_dir() and args.fix:
        print("[fix ] installing gstack ...")
        code, _ = _run_quiet(["git", "clone", "--depth", "1",
                              "https://github.com/garrytan/gstack.git", str(gstack)])
        if code == 0 and (gstack / "setup").exists():
            _run_quiet([str(gstack / "setup")])  # best-effort; skills work from clone
    checks.append(_check(
        "gstack skills", gstack.is_dir(), str(gstack) if gstack.is_dir() else "not installed",
        "`git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && ~/.claude/skills/gstack/setup` "
        "(needed for /office-hours discovery) — or rerun with --fix"))
    autoreview = home / ".codex" / "skills" / "autoreview"
    if not autoreview.is_dir() and args.fix:
        print("[fix ] installing autoreview ...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = _run_quiet(["git", "clone", "--depth", "1",
                                  "https://github.com/openclaw/agent-skills.git", tmp + "/as"])
            src = Path(tmp) / "as" / "skills" / "autoreview"
            if code == 0 and src.is_dir():
                shutil.copytree(src, autoreview)
    checks.append(_check(
        "autoreview skill", autoreview.is_dir(), str(autoreview) if autoreview.is_dir() else "not installed",
        "clone https://github.com/openclaw/agent-skills and copy skills/autoreview to "
        "~/.codex/skills/ — or rerun with --fix (escalation-tier review; see harness.yaml)",
        required=False))
    ponytail_cache = home / ".claude" / "plugins" / "cache"

    def _ponytail_ok() -> bool:
        return ponytail_cache.is_dir() and any(ponytail_cache.glob("*ponytail*"))

    if not _ponytail_ok() and args.fix and claude_bin:
        print("[fix ] installing ponytail ...")
        _install_claude_plugin("https://github.com/DietrichGebert/ponytail", "ponytail@ponytail")
    checks.append(_check(
        "ponytail plugin", _ponytail_ok(),
        "installed" if _ponytail_ok() else "not installed",
        "`claude plugin marketplace add https://github.com/DietrichGebert/ponytail && "
        "claude plugin install ponytail@ponytail` — or rerun with --fix "
        "(prototype phase 0b only — see harness.yaml)",
        required=False))

    width = max(len(c["name"]) for c in checks)
    failures = 0
    for c in checks:
        mark = "OK " if c["ok"] else ("MISS" if c["required"] else "opt ")
        print(f"[{mark}] {c['name']:<{width}}  {c['detail']}")
        if not c["ok"]:
            print(f"       fix: {c['fix']}")
            if c["required"]:
                failures += 1
    if failures:
        print(f"\nforge doctor: {failures} required tool(s) missing.")
        raise SystemExit(1)
    print("\nforge doctor: ready. Next: forge.py init --name <project> --target <dir>")


def cmd_decision_accept(args: argparse.Namespace) -> None:
    base = Path(args.repo).resolve() if args.repo else repo_root()
    decisions = base / "docs" / "decisions"
    slug = args.slug.strip().lower().replace(" ", "-")
    matches = sorted(decisions.glob(f"[0-9][0-9][0-9][0-9]-{slug}.md"))
    if not matches:
        fail(f"no decision record matching docs/decisions/NNNN-{slug}.md")
    record = matches[-1]
    text = record.read_text()
    if "status: accepted" in text:
        print(f"{record.relative_to(base)} is already accepted.")
        return
    text = text.replace("status: proposed", "status: accepted", 1)
    if 'confirmed_by: ""' in text:
        text = text.replace('confirmed_by: ""', f'confirmed_by: "{args.by}"', 1)
    else:
        text = re.sub(r"confirmed_by: .*", f'confirmed_by: "{args.by}"', text, count=1)
    record.write_text(text)
    rel = record.relative_to(base)
    print(f"Accepted: {rel} (confirmed_by: {args.by})")
    print("Commit it with the audit trailer:")
    print(f'  git add {rel} && git commit -m "docs(decisions): accept {slug}" '
          f'--trailer "Confirmed-by: {args.by}"')
    if slug == "client-signoff":
        print("Then arm the gate: python3 .agents/scripts/record_signoff.py")


def main() -> None:
    parser = argparse.ArgumentParser(prog="forge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="check machine prerequisites for the harness")
    p_doc.add_argument("--fix", action="store_true",
                       help="auto-install what is safely scriptable (gstack, autoreview); "
                            "logins and in-app plugin installs stay manual")
    p_doc.set_defaults(func=cmd_doctor)

    p_next = sub.add_parser("next", help="where am I and what do I do now (deterministic)")
    p_next.add_argument("--repo")
    p_next.set_defaults(func=cmd_next)

    p_init = sub.add_parser("init", help="scaffold a new client repo from this harness")
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--target")
    p_init.add_argument("--stack", default="nestjs-react")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_plan = sub.add_parser("plan", help="manage task plans")
    plan_sub = p_plan.add_subparsers(dest="plan_command", required=True)
    p_save = plan_sub.add_parser("save", help="persist an approved plan into plans/active/")
    p_save.add_argument("--from", dest="source", required=True,
                        help="path to the approved plan file (e.g. the Claude Code plan)")
    p_save.add_argument("--issue", help="issue key (defaults to .factory/run.json)")
    p_save.add_argument("--title", help="plan title (defaults to run.json title)")
    p_save.add_argument("--repo", help="target repo (defaults to this repo)")
    p_save.set_defaults(func=cmd_plan_save)
    p_assume = plan_sub.add_parser(
        "assume", help="record an implementation assumption on the active plan")
    p_assume.add_argument("text", help="the assumption, one sentence")
    p_assume.add_argument("--issue", help="issue key (defaults to .factory/run.json)")
    p_assume.add_argument("--repo")
    p_assume.set_defaults(func=cmd_plan_assume)

    p_ctx = sub.add_parser("context", help="track the docs/context inbox")
    ctx_sub = p_ctx.add_subparsers(dest="context_command", required=True)
    p_scan = ctx_sub.add_parser("scan", help="register new/changed context files in the ledger")
    p_scan.add_argument("--check", action="store_true",
                        help="fail if the ledger is out of sync (CI mode; writes nothing)")
    p_scan.add_argument("--repo")
    p_scan.set_defaults(func=cmd_context_scan)
    p_list = ctx_sub.add_parser("list", help="show ledger entries")
    p_list.add_argument("--pending", action="store_true")
    p_list.add_argument("--repo")
    p_list.set_defaults(func=cmd_context_list)
    p_mark = ctx_sub.add_parser("mark", help="record harvest outcome for a context file")
    p_mark.add_argument("file")
    group = p_mark.add_mutually_exclusive_group(required=True)
    group.add_argument("--harvested", action="store_true")
    group.add_argument("--ignored", action="store_true")
    p_mark.add_argument("--outputs", nargs="*", help="repo-relative paths the harvest produced")
    p_mark.add_argument("--notes")
    p_mark.add_argument("--repo")
    p_mark.set_defaults(func=cmd_context_mark)

    p_dec = sub.add_parser("decision", help="manage decision records")
    dec_sub = p_dec.add_subparsers(dest="decision_command", required=True)
    p_new = dec_sub.add_parser("new", help="create the next NNNN-<slug>.md record")
    p_new.add_argument("slug")
    p_new.add_argument("--title")
    p_new.add_argument("--repo", help="target repo (defaults to this repo)")
    p_new.set_defaults(func=cmd_decision_new)
    p_acc = dec_sub.add_parser("accept", help="mark a decision accepted with a human's name")
    p_acc.add_argument("slug")
    p_acc.add_argument("--by", required=True, help="the human confirming (not an agent)")
    p_acc.add_argument("--repo")
    p_acc.set_defaults(func=cmd_decision_accept)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
