---
name: caw-new-project
description: >-
  Bootstrap a new CAW client project from the Symphony Forge harness:
  update the harness clone, verify machine prerequisites (doctor), scaffold
  the repo (forge init), and hand off to the project's /forge skill. Invoke
  when the user says "new CAW project", "set up a client project", "start a
  project with the harness", "scaffold <name>", or "/caw-new-project".
---

# New CAW Project

You are bootstrapping a client repo from the harness. Everything below is
runnable by you — the user should only have to answer questions.

## Steps

1. **Locate or fetch the harness.** `./setup` stamped the clone location below
   at install time; fall back to asking the user, then cloning where they say.
   ```bash
   HARNESS="{{HARNESS_PATH}}"
   [ -d "$HARNESS/.git" ] && git -C "$HARNESS" pull --ff-only \
     || git clone git@github.com:cawstudios/symphony-forge.git "$HARNESS"
   ```

2. **Doctor.** Run `python3 "$HARNESS/.agents/scripts/forge.py" doctor`.
   If it reports misses, rerun with `--fix` (user approves) — that installs
   everything installable: Codex CLI, codex-plugin-cc, ponytail, gstack,
   autoreview, all from their canonical GitHub sources. Only logins remain
   (`codex login`) — give the user that command and wait. Do not proceed with
   required tools missing.

3. **Ask** (one question): project name, and target directory if not
   `~/Workdir/<name>`.

4. **Scaffold.**
   ```bash
   python3 "$HARNESS/.agents/scripts/forge.py" init --name <name> --target <dir>
   ```
   Never pass `--force` without explicit user confirmation — it overwrites.

5. **Enable the project-local gstack store.** `cd <dir>` and run
   `direnv allow` — this activates `.envrc` (GSTACK_HOME pinned to the
   repo's `.gstack/`), so office-hours design docs, decisions, and learnings
   are committed and shared instead of stranded in `~/.gstack`.

6. **Hand off.** Run `python3 .agents/scripts/forge.py next`,
   relay its output, and tell the user: from here, this repo's own `/forge`
   skill (and `forge.py next`) drives every phase — discovery first.

## Rules

- The generated repo is the system of record; the harness clone is only the
  template source. Never do project work inside the harness clone.
- If doctor and init both pass but `next` errors, report verbatim — do not
  improvise around a broken scaffold.
