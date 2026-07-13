"""forge adopt — vendor the harness into an EXISTING repo (migration path).

Run FROM the harness clone, targeting a repo that predates the harness (a
prototype built with agents, an early client repo). Harness-owned machinery
is copied in; project content is never destroyed: the target must be clean so
every overwrite is a reviewable git diff, pre-existing AGENTS.md/CLAUDE.md
are preserved into docs/context/ for harvest, and project-owned files are
created only where missing. Content mapping (what is prototype, what is
context, what becomes the BRIEF) is judgment — the caw-migrate-project skill
drives that afterwards.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from factory_lib import dump_json, head_sha, now_iso, repo_root

from .common import fail
from .scaffold import COPY_CODEX, DISCOVERY_TEMPLATE, DOC_CONTRACTS, PROTOTYPE_README
from .upgrade import UPGRADE_TREES

# Harness-owned files: replaced outright (visible in the diff).
OWNED_FILES = ["forge", "WORKFLOW.md"]
# Files an agent-built repo often already has: existing content is saved to
# docs/context/migrated-<name> (harvest picks it up), then the harness
# version is written.
MERGE_FILES = ["AGENTS.md", "CLAUDE.md"]


def cmd_adopt(args: argparse.Namespace) -> None:
    harness = repo_root()
    target = Path(args.target).resolve()
    if not (target / ".git").exists():
        fail(f"{target} is not a git repo — adopt needs history so overwrites are reviewable")
    if target == harness:
        fail("run adopt FROM the harness clone TARGETING the existing repo, not itself")
    if (target / ".agents" / "scripts" / "forge.py").exists():
        fail(f"{target} already carries the harness — use `./forge upgrade --target {target}`")
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=target, capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        fail(
            f"{target} has uncommitted changes. Commit everything first — adopt "
            "overwrites harness-owned paths and the diff must be reviewable."
        )
    name = args.name or target.name

    overwritten: list[str] = []

    def vendor_file(src: Path, dst: Path) -> None:
        if dst.exists():
            overwritten.append(str(dst.relative_to(target)))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def vendor_tree(rel: str) -> None:
        src = harness / rel
        if not src.exists():
            return
        for path in src.rglob("*"):
            if path.is_file():
                vendor_file(path, target / path.relative_to(harness))

    # Machinery trees are MERGED per file, not replaced wholesale — an existing
    # repo's own .github/workflows/ or .claude/skills/ must survive.
    for tree in UPGRADE_TREES:
        vendor_tree(tree)
    for rel in COPY_CODEX:
        vendor_file(harness / ".codex" / rel, target / ".codex" / rel)
    for sub in ("agents", "skills"):
        vendor_tree(f".codex/{sub}")
    for rel in OWNED_FILES:
        vendor_file(harness / rel, target / rel)
    for src_rel, dst_rel in DOC_CONTRACTS:
        if (harness / src_rel).exists():
            vendor_file(harness / src_rel, target / dst_rel)

    # Pre-existing agent instructions are context, not garbage: preserve them
    # where the harvester will find them, then install the harness versions.
    preserved: list[str] = []
    context_dir = target / "docs" / "context"
    for rel in MERGE_FILES:
        dst = target / rel
        src_text = (harness / rel).read_text()
        if rel == "AGENTS.md":
            src_text = src_text.replace("Symphony Forge", name, 1)
        if dst.exists() and dst.read_text() != src_text:
            context_dir.mkdir(parents=True, exist_ok=True)
            keep = context_dir / f"migrated-{rel}"
            shutil.copy2(dst, keep)
            preserved.append(str(keep.relative_to(target)))
        dst.write_text(src_text)

    commit = head_sha(harness) or "unknown"
    (target / "constitution" / "VENDORED_FROM").write_text(
        f"symphony-forge @ {commit}\nUpdate by re-vendoring from the harness repo; do not edit in place.\n"
    )

    # Project-owned: created only where missing, never overwritten.
    created: list[str] = []

    def ensure(rel: str, text: str) -> None:
        dst = target / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text)
            created.append(rel)

    if not (target / "harness.yaml").exists():
        shutil.copy2(harness / "harness.yaml", target / "harness.yaml")
        created.append("harness.yaml")
    if not (target / ".gitignore").exists():
        shutil.copy2(harness / ".gitignore", target / ".gitignore")
        created.append(".gitignore")
    elif ".gstack/sessions/" not in (target / ".gitignore").read_text():
        with (target / ".gitignore").open("a") as fh:
            fh.write("\n# Project-local gstack store: projects/ committed, machine noise not\n"
                     ".gstack/sessions/\n.gstack/analytics/\n.gstack/cdp-profile/\n"
                     ".gstack/tmp/\n.gstack/.*\n")
        created.append(".gitignore (gstack entries appended)")
    if not (target / ".envrc").exists():
        shutil.copy2(harness / ".envrc", target / ".envrc")
        created.append(".envrc (run `direnv allow` in the repo)")
    attrs = target / ".gitattributes"
    if not attrs.exists():
        shutil.copy2(harness / ".gitattributes", attrs)
        created.append(".gitattributes")
    elif "merge=jsonl-append" not in attrs.read_text():
        with attrs.open("a") as fh:
            fh.write("\n.gstack/**/*.jsonl merge=jsonl-append\n")
        created.append(".gitattributes (jsonl merge rule appended)")
    brief_src = harness / "harness" / "nestjs-react" / "BRIEF_TEMPLATE.md"
    if brief_src.exists() and not (target / "docs" / "product" / "BRIEF.md").exists():
        (target / "docs" / "product").mkdir(parents=True, exist_ok=True)
        shutil.copy2(brief_src, target / "docs" / "product" / "BRIEF.md")
        created.append("docs/product/BRIEF.md")
    ensure("docs/product/DISCOVERY.md", DISCOVERY_TEMPLATE.format(name=name))
    ensure("prototype/README.md", PROTOTYPE_README)
    for sub in ("active", "completed", "debt"):
        plan_dir = target / "plans" / sub
        if not plan_dir.exists():
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / ".gitkeep").touch()
    for rel in ("docs/decisions", "docs/architecture", "docs/context"):
        (target / rel).mkdir(parents=True, exist_ok=True)
    if not (target / ".factory" / "run.json").exists():
        (target / ".factory" / "reviews").mkdir(parents=True, exist_ok=True)
        dump_json(
            target / ".factory" / "run.json",
            {"project": name, "client_signoff": False, "created_at": now_iso()},
        )
        created.append(".factory/run.json")

    print(f"Adopted the harness into {target} (symphony-forge @ {commit[:8]})")
    if overwritten:
        head = ", ".join(sorted(overwritten)[:8])
        more = f" (+{len(overwritten) - 8} more)" if len(overwritten) > 8 else ""
        print(f"Overwrote {len(overwritten)} pre-existing file(s): {head}{more} — review with git diff")
    if preserved:
        print("Preserved for harvest: " + ", ".join(preserved))
    if created:
        print("Created (project-owned): " + ", ".join(created))
    print("Next (the caw-migrate-project skill walks all of this):")
    print("  1. git diff — review every overwrite; merge old .gitignore/CI entries if needed")
    print("  2. Sort existing content: prototype work -> prototype/, raw notes -> docs/context/")
    print("  3. ./forge context scan, then harvest into DISCOVERY.md/BRIEF.md and decisions")
    print("  4. Linters + gate tests, commit, then: ./forge next")
