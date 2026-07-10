---
name: caw-migrate-project
description: >-
  Migrate an EXISTING repo — a prototype or early project built with agents
  before the harness — into the Symphony Forge harness: vendor the machinery
  (forge adopt), sort existing content into prototype/ and docs/context/,
  harvest it into DISCOVERY/BRIEF and decision records, and hand off to the
  factory loop. Invoke when the user says "migrate this repo", "adopt the
  harness", "bring this project into symphony forge", "harness-ify this
  repo", or "/caw-migrate-project".
---

# Migrate an Existing Repo into the Harness

You are migrating a repo that predates the harness. The mechanical part is
one deterministic command; your judgment is only for sorting the existing
content. Never delete existing work — everything moves, nothing vanishes.

## Steps

1. **Locate or fetch the harness** (stamped at install time):
   ```bash
   HARNESS="{{HARNESS_PATH}}"
   [ -d "$HARNESS/.git" ] && git -C "$HARNESS" pull --ff-only \
     || git clone git@github.com:cawstudios/symphony-forge.git "$HARNESS"
   ```

2. **Doctor.** `python3 "$HARNESS/.agents/scripts/forge.py" doctor` — rerun
   with `--fix` (user approves) on misses; only logins stay manual.

3. **Precondition the target repo.** It must be a git repo with a CLEAN tree
   (commit or stash with the user). Create a migration branch:
   ```bash
   git checkout -b chore/adopt-harness
   ```

4. **Adopt (deterministic).**
   ```bash
   python3 "$HARNESS/.agents/scripts/forge.py" adopt --target <repo> --name <project>
   ```
   This vendors the machinery, preserves any pre-existing `AGENTS.md` /
   `CLAUDE.md` into `docs/context/migrated-*`, and creates project-owned
   files only where missing. It refuses a dirty tree and refuses repos that
   already carry the harness (use `forge upgrade` there).

5. **Review the diff with the user.** Walk the "Overwrote ..." list from the
   adopt output. If the repo had its own `.gitignore` or CI workflows, merge
   the harness entries instead of losing theirs.

6. **Sort the existing content** — ask the user ONE question first: *is this
   repo the prototype itself, or does it carry production-intent code?*
   - **Prototype repo**: move the app code under `prototype/` (reference
     forever, imported never — production gets scaffolded fresh at the
     workspace step). Screenshots/demos/walkthroughs go there too.
   - **Production-intent repo**: leave the code in place; move only prototype
     artifacts (mockups, spikes, demo assets) into `prototype/`.
   - Everything unstructured — notes, transcripts, chat exports, old README
     lore, the `migrated-*` files — belongs in `docs/context/`. Then:
   ```bash
   ./forge context scan
   ```

7. **Harvest** (`.agents/prompts/harvester.md`): distill
   `docs/product/DISCOVERY.md` and `BRIEF.md` from the context; propose a
   `./forge decision new <slug>` record for every client decision already
   made. THE HUMAN accepts decisions (`./forge decision accept`) — relay,
   never run. Mark harvested files with `./forge context mark`.

8. **If the client already signed off historically**, formalize it now:
   `client-signoff` decision → human accept → `record_signoff.py`. Otherwise
   the repo correctly sits pre-sign-off.

9. **Verify and land.** Run `python3 .agents/scripts/check_dual_runtime.py`,
   `check_factory_scaffold.py`, and the gate tests; commit the branch and
   open the PR for review.

10. **Hand off.** Run `python3 .agents/scripts/forge.py next`, relay the
    output — from here the repo's own `/forge` skill drives every phase
    (roadmap next, if features are already known).

## Rules

- Nothing is deleted; content is MOVED and the diff stays reviewable.
- Recorders and gates apply from the moment of adoption — no evidence enters
  `.factory/` except through the schema-validated scripts.
- Human-only actions stay human: decision accepts, sign-off confirmation.
