---
issue: FORGE-INIT-1
title: forge init: per-file collision check for non-empty targets
status: approved
saved: 2026-07-24T12:01:57+00:00
---

# forge init: replace blanket non-empty refusal with a per-file collision check

## Context

Bootstrapping `agentstats` (a new repo that already had one commit — a design spec at `docs/superpowers/specs/`) hit a wall: `forge init` refuses **any** non-empty target (`scaffold.py:122`, `any(target.iterdir())`), even when nothing init writes would collide. The only escape is `--force`, which blindly overwrites everything. The workaround (scaffold into a scratch dir, rsync in) proves the guard is a false positive: the correct question is "would init overwrite anything?", not "is the dir empty?". `adopt` already models this per-file thinking (`adopt.py:63-73` records collisions in `vendor_file` instead of pre-refusing).

**Recommendation (high confidence):** keep init's safety guarantee — never silently clobber — but enforce it by checking the actual destination paths init writes. Non-empty target with zero collisions → proceed. Collisions → fail listing them; `--force` keeps its overwrite meaning.

## Change

**Modify: `.agents/scripts/forge_cli/scaffold.py`** (only file with logic changes)

1. Add a module-level helper that enumerates every destination file `cmd_init` will write, mirroring the copy lists it already uses:

```python
GENERATED_FILES = ["AGENTS.md", "docs/product/BRIEF.md", "docs/product/DISCOVERY.md",
                   "prototype/README.md", ".factory/run.json",
                   "constitution/VENDORED_FROM", "constitution/VENDOR_MANIFEST.json"]

def _would_write(root: Path, target: Path) -> list[Path]:
    """Every file cmd_init creates or overwrites. README.md is excluded
    (append-if-missing via ensure_onboarding); plans/**/.gitkeep are
    touch-only. Keep in sync with the copy loops in cmd_init."""
    dests: list[Path] = []
    trees = [*COPY_TREES, ".codex/agents", ".codex/skills"]
    for tree in trees:
        src = root / tree
        if src.exists():
            for f in src.rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                    dests.append(target / f.relative_to(root))
    for rel in [*COPY_WORKFLOWS, *(f".codex/{n}" for n in COPY_CODEX),
                *COPY_FILES, *(dst for _, dst in DOC_CONTRACTS), *GENERATED_FILES]:
        dests.append(target / rel)
    return dests
```

2. Replace the guard at `cmd_init` (`scaffold.py:122-127`):

```python
if target.exists() and any(target.iterdir()) and not args.force:
    collisions = sorted(
        str(p.relative_to(target)) for p in _would_write(root, target) if p.exists()
    )
    if collisions:
        listing = "\n  ".join(collisions[:10])
        more = f"\n  ... and {len(collisions) - 10} more" if len(collisions) > 10 else ""
        fail(
            f"target {target} already contains {len(collisions)} file(s) forge init "
            f"would overwrite:\n  {listing}{more}\nuse --force to overwrite them."
        )
```

Nothing else in `cmd_init` changes — the copy loops already tolerate existing dirs (`dirs_exist_ok=True`, `mkdir(exist_ok=True)`), which the scratch-dir rsync workaround empirically confirmed. `--force` behavior is unchanged. `constitution/VENDORED_FROM` and `constitution/VENDOR_MANIFEST.json` are generated (not in the source tree walk), so they are listed in `GENERATED_FILES` explicitly — a pre-existing copy in the target must count as a collision (caught in review of the first draft).

**Test: `.agents/tests/test_gates.py`** — two new tests following the existing subprocess pattern (see the `repo` fixture, lines 52-63):

- `test_init_into_nonempty_noncolliding_target`: pre-seed `target/docs/notes/spec.md` (+ `git init`), run init, assert returncode 0 and the seeded file still exists with original content.
- `test_init_refuses_colliding_target`: pre-seed `target/WORKFLOW.md`, run init, assert returncode 1 and `"WORKFLOW.md"` appears in output.

**Docs: `docs/getting-started.md:91`** — replace "It fails on a non-empty target." with: "It refuses a target containing files it would overwrite (listing them); a non-empty target with no collisions is fine."

## Surface Impact

| Surface | Status | Note |
|---|---|---|
| Runtime behavior | Changed | `forge init` now proceeds into a non-empty target with zero collisions; refusal only on actual collisions |
| CLI/ops | Changed | init error message now lists colliding files; `--force` semantics unchanged |
| Tests | Changed | two new gate tests in `.agents/tests/test_gates.py` |
| Docs | Changed | one sentence at `docs/getting-started.md:91` |
| API | N/A | no programmatic API surface |
| Data/schema | Unchanged by design | no `.factory` schema or recorder touched — the fix is pre-scaffold guard logic only |
| UI | N/A | no UI in the harness |

## Verification

1. `python3 -m pytest .agents/tests/test_gates.py -x -q` — full gate suite green (existing `repo` fixture exercises the empty-target happy path; new tests cover both new branches).
2. End-to-end: re-run the exact failing scenario — `forge.py init --name t --target <tmpdir>` where tmpdir has `.git` + one doc → succeeds, doc intact; second run into the now-scaffolded dir → refuses with collision list.
3. `python3 .agents/scripts/check_dual_runtime.py` stays green.

## Process (repo contract)

After approval: save the plan (`python3 .agents/scripts/forge.py plan save --from <this file>`), branch `fix/init-collision-check`, delegate implementation to Codex per `.claude/CLAUDE.md` (`/codex:rescue --background`, gpt-5.6-sol @ medium), review, PR.
