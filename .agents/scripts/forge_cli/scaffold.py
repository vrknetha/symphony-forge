"""forge init — scaffold a new client repo from the harness."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from factory_lib import dump_json, now_iso, repo_root

from .common import fail

COPY_TREES = [".agents", ".claude", "constitution", "harness"]
# .github/workflows/ is MIXED ownership: only these generic factory workflows
# are harness-owned and vendored. A client repo's own workflows (deployment,
# release, etc.) are project-owned — copied file-by-file so we never clobber or
# leak them (init) and never delete them (upgrade rmtree'd the whole tree).
COPY_WORKFLOWS = [
    ".github/workflows/factory-scaffold.yml",
    ".github/workflows/gardener.yml",
]
COPY_CODEX = ["config.toml", "hooks.json"]  # + agents/ and skills/ dirs
COPY_FILES = ["harness.yaml", ".gitignore", ".gitattributes", ".envrc",
              "WORKFLOW.md", "CLAUDE.md", "forge"]
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
<!-- Each becomes docs/decisions/NNNN-<slug>.md via: ./forge decision new <slug> -->
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
    for rel in COPY_WORKFLOWS:
        src = root / rel
        if src.exists():
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
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
    print("  0. cd in and run `direnv allow` (once per machine) — pins gstack "
         "output into the repo's .gstack/, not ~/.gstack")
    print("  1. Fill docs/product/DISCOVERY.md (phase 0a) and BRIEF.md")
    print("  2. Prototype (phase 0b), then: ./forge decision new client-signoff")
    print("  3. After `./forge decision accept client-signoff --by <name>`: "
          "python3 .agents/scripts/record_signoff.py")
    print(f"  4. Generate the {args.stack} workspace via harness/{args.stack}/SCAFFOLD_PROMPT.md")
