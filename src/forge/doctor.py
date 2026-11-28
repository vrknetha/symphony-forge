"""Check Forge's tools, generated files, hooks, CI and Codex trust; repair safe drift with --fix."""
from __future__ import annotations
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from contextlib import suppress
from datetime import datetime, timedelta
from itertools import islice
from pathlib import Path
from typing import Any

from forge import __version__, antigravity, checks, claude_sdk, close, codex, init, machine, quicktest, repo, review, story, sync, task

COMMANDS = [{"words": "doctor", "run": "doctor", "changes_state": False,
    "help": "Check tools, versions, hooks, adapter drift and the named CI checks", "args": [(('--fix',), {"action": "store_true", "help":
              "repair what doctor safely can: the pinned Forge, the agent SDKs, the git hooks, "
              "the folders of finished work and the files forge sync writes"})], "position": 30,
    "listing": "| `forge doctor` | Checks tools, versions, hooks, generated-file drift and CI; one row per problem, each with a fix; `--fix` repairs what it safely can |",
}]
REFUSALS = {"problems": ("forge doctor found {count} problem(s); each row above gives its fix.", "forge doctor")}
INSTALL = {"git": "install git from https://git-scm.com/downloads", "gh": "install gh from https://cli.github.com",
    "codex": "npm install -g @openai/codex",
    "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh", "claude": "npm install -g @anthropic-ai/claude-code",
    "impeccable": "npx skills add pbakaus/impeccable -g",
    "emil-design-eng": "npx --yes skills add emilkowalski/skills --skill emil-design-eng -g --yes",
    "autoreview": (f"install skills/autoreview from https://github.com/openclaw/agent-skills at "
                   f"{review.AUTOREVIEW_PIN} into {review.HELPERS[0].parents[1]} or " f"{review.HELPERS[1].parents[1]}")}
REPAIR = "forge doctor --fix"
WHY = "Bring the files Forge writes for Claude Code and Codex up to date"
DONE = "The files match what forge sync writes for the pinned Forge"
HAND = "move your change out of this file, since forge sync rewrites it, then forge doctor --fix"
SAMPLES = {"SessionStart": {"source": "startup"}, "PreToolUse": {"tool_name": "Bash", "tool_input": {"command": "git status"}},
    "PostToolUse": {"tool_name": "forge-doctor", "tool_input": {}, "tool_response": {}}}
BARE_PATH = "/usr/bin:/bin"
def _forge_hooks(text: str) -> list[tuple[str, str]]:
    try:
        hooks = json.loads(text or "{}").get("hooks", {})
        return [(event, hook["command"]) for event, groups in hooks.items() for group in groups
                for hook in group.get("hooks", []) if sync.FORGE_COMMAND.search(hook.get("command", ""))]
    except (ValueError, AttributeError, TypeError, KeyError): return []
def _codex_trust(top: Path, config: Path) -> tuple[bool, str]:
    """Trusted only on an exact trusted [projects] entry for the checkout or its main checkout (each
    as given or as its real path); a missing, untrusted or unreadable entry fails closed, and a
    parent folder's entry never counts. Returns the verdict and the fix: the entry that blocks, or
    the main checkout's entry to add."""
    common = Path(repo.git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=top))
    keys = {str(folder) for folder in (top, common.parent)} | {os.path.realpath(f) for f in (top, common.parent)}
    try: levels = {key: project.get("trust_level") for key, project in tomllib.loads(sync.read(config)).get("projects", {}).items() if key in keys}
    except (tomllib.TOMLDecodeError, AttributeError): levels = {}
    blocking = next((key for key, level in sorted(levels.items()) if level != "trusted"), None)
    if blocking: return False, (f'set trust_level = "trusted" under [projects.{json.dumps(blocking)}] in {config}; '
                                "a parent folder's entry does not count")
    return bool(levels), ("open Codex here and trust the project, or add trust_level = \"trusted\" under "
                          f"[projects.{json.dumps(os.path.realpath(common.parent))}] in {config}, the main checkout, which "
                          "covers every worktree Forge makes; a parent folder's entry does not count")
def _last(done: subprocess.CompletedProcess[str] | Exception) -> str:
    if not isinstance(done, (subprocess.CompletedProcess, subprocess.CalledProcessError)): return str(done).partition("\nNext: ")[0]
    return ((done.stderr or "").strip() or (done.stdout or "").strip() or f"exit code {done.returncode}").splitlines()[-1]
def _prs(top: Path, branch: str, *options: str) -> Any:
    done = repo.run("gh", "pr", "list", "--head", branch, "--state", "all", *options, cwd=top)
    try: return json.loads(done.stdout) if done.returncode == 0 else None
    except ValueError: return None
def _files_fix_finished(top: Path, branch: str) -> bool:
    prs = _prs(top, branch, "--json", "state") if shutil.which("gh") else None
    return isinstance(prs, list) and any(isinstance(pr, dict) and pr.get("state") in ("MERGED", "CLOSED") for pr in prs)
def _open_files_fix(top: Path) -> str: return next((branch for branch in repo.git("for-each-ref", "--format=%(refname:short)",
                 "refs/heads/fix/forge-files-*", cwd=top).splitlines() if not _files_fix_finished(top, branch)), "")
def _cleanup_prs(gh: str, top: Path, branches: dict[str, Path]) -> list[tuple[str, str, str]]:
    pending: dict[str, str | None] = dict.fromkeys(branches)
    prs = []
    while pending:
        batch = {f"head_{branch.encode().hex()}": (branch, cursor)
                 for branch, cursor in islice(pending.items(), 150)}
        fields = [
            f"{alias}: pullRequests(first: 25, headRefName: {json.dumps(branch, ensure_ascii=False)}, "
            f"after: {json.dumps(cursor)}) {{ nodes {{ headRefOid state }} "
            "pageInfo { hasNextPage endCursor } }"
            for alias, (branch, cursor) in batch.items()
        ]
        query = ("query FinishedFolders($owner: String!, $name: String!) { "
                 "repository(owner: $owner, name: $name) { " + " ".join(fields) + " } }")
        # A fresh, branch-filtered query avoids reading unrelated history or waiting for land's quota.
        done = subprocess.run([gh, "api", "graphql", "-F", "query=@-", "-F", "owner={owner}", "-F", "name={repo}"],
                              cwd=top, input=query.encode("utf-8"), capture_output=True, timeout=10)
        if done.returncode: return []
        response = json.loads(done.stdout)
        if response.get("errors"): return []
        pages = response["data"]["repository"]
        for alias, (branch, cursor) in batch.items():
            page = pages[alias]
            nodes, info = page["nodes"], page["pageInfo"]
            if not isinstance(nodes, list) or not all(
                    isinstance(pr, dict) and isinstance(pr.get("headRefOid"), str)
                    and pr.get("state") in ("OPEN", "MERGED", "CLOSED") for pr in nodes):
                return []
            if info["hasNextPage"] is True:
                after = info["endCursor"]
                if not isinstance(after, str) or not after or after == cursor: return []
                pending[branch] = after
            elif info["hasNextPage"] is False:
                del pending[branch]
            else:
                return []
            prs.extend((branch, pr["headRefOid"], pr["state"]) for pr in nodes)
    return prs


def _finished(top: Path, main: Path) -> list[tuple[Path, str, str, str]]:
    gh = shutil.which("gh")
    if not gh: return []
    trees = {branch: path for branch, path in story.worktrees(top).items()
             if branch.startswith(("story/", "task/", "fix/", "forge/"))
             and path.resolve() not in (main, top.resolve()) and path.is_dir()
             and not (path / ".gitmodules").exists()}
    if not trees: return []

    by_head = set(_cleanup_prs(gh, top, trees))
    open_branches = {branch for branch, _, state in by_head if state == "OPEN"}
    reported = {branch for branch, _, _ in by_head}
    # Old lane entries recorded the checkout as "repo", including while they waited for a place.
    live = {Path(folder).resolve() for run in machine.entries()
            if (folder := run.get("checkout_root") or run.get("repo"))}
    closed = {}
    found = []
    for branch, path in trees.items():
        if branch not in reported or branch in open_branches or path.resolve() in live: continue
        head = repo.git("rev-parse", f"refs/heads/{branch}", cwd=top)
        if (branch, head, "MERGED") in by_head:
            found.append((path, branch, head, "merged"))
        elif (branch, head, "CLOSED") in by_head:
            closed[f"refs/heads/{branch}"] = (head, path, branch)
    if closed:
        heads = repo.run("git", "ls-remote", "--heads", "origin", *closed, cwd=top, timeout=10)
        if not heads.returncode:
            for line in heads.stdout.splitlines():
                head, _, ref = line.partition("\t")
                if ref in closed and head == closed[ref][0]:
                    _, path, branch = closed[ref]
                    found.append((path, branch, head, "closed"))
    return found


def _removable(path: Path, ref: str, head: str) -> bool:
    return (not (path / ".gitmodules").exists()
            and repo.git("symbolic-ref", "--quiet", "HEAD", cwd=path) == ref
            and repo.git("show-ref", "--hash", "--verify", "HEAD", cwd=path) == head
            and not task.worktree_files(path))


def _checkout_in_use(path: Path) -> bool:
    """A process with this working directory can still write after the worktree moves."""
    folder = path.resolve()
    if sys.platform == "darwin":
        cwd = subprocess.run(["/usr/sbin/lsof", "-a", "-u", str(os.getuid()), "-d", "cwd", "-Fn0"],
                             capture_output=True, timeout=5, check=True)
        return any(Path(os.fsdecode(field[1:])).is_relative_to(folder)
                   for field in cwd.stdout.split(b"\0") if field.startswith(b"n/"))
    if sys.platform == "linux":
        proc = Path("/proc")
        if not (proc / "self/cwd").is_symlink(): return True
        for process in proc.iterdir():
            if not process.name.isdecimal(): continue
            with suppress(OSError):
                if (process / "cwd").readlink().is_relative_to(folder): return True
        return False
    # Windows holds a process's current directory open so Git cannot move it.
    return os.name != "nt"


def _remove_finished(main: Path, path: Path, ref: str, head: str, report, *,
                     restore_lock: bool) -> subprocess.CompletedProcess[str] | None:
    from forge import githooks

    if not restore_lock and repo.git("status", "--porcelain", "--", "uv.lock", cwd=path):
        return None
    # Git's removal check skips ignored files. Move away from the editor's path before checking them again.
    scratch = Path(tempfile.mkdtemp(prefix=".forge-tidy-", dir=path.parent))
    moved = scratch / "worktree"
    try:
        done = repo.run("git", "worktree", "move", str(path), str(moved), cwd=main)
        if done.returncode: return done
        if _checkout_in_use(moved) or not _removable(moved, ref, head): return None

        if restore_lock:
            if repo.run("git", "diff", "--cached", "--quiet", "--", "uv.lock", cwd=moved).returncode:
                return None  # Tests do not stage their lockfile changes.
            if repo.run("git", "diff", "--quiet", "--", "uv.lock", cwd=moved).returncode == 1:
                repo.git("checkout", "--", "uv.lock", cwd=moved)

        untracked = {moved / name for name in repo.git(
            "ls-files", "--others", "--exclude-standard", "-z", cwd=moved).split("\0")}
        for shim, expected in githooks.shims(moved, repo.config(moved)).items():
            if shim in untracked and not shim.is_symlink() and sync.read(shim) == expected:
                shim.unlink()
        if not _removable(moved, ref, head): return None
        return repo.run("git", "-c", "status.showUntrackedFiles=all", "worktree", "remove", str(moved), cwd=main)
    finally:
        if moved.exists():
            restored = repo.run("git", "worktree", "move", str(moved), str(path), cwd=main)
            if restored.returncode and report is not None:
                report(f"Forge kept the worktree at {moved}: {_last(restored)}",
                       f"git worktree move {repo.quote(str(moved))} {repo.quote(str(path))}")
        with suppress(OSError):
            scratch.rmdir()  # Never delete files if Git could not move the worktree back.


def tidy_finished(top: Path, *, inspect: bool = False, restore_lock: bool = False, report=None) -> int:
    """Remove only worktrees whose exact local work is available on GitHub."""
    from forge import board

    try:
        if repo._pin(sync.read(top / "forge.toml")) != __version__: return 0
        main = machine.main_checkout(top)
        finished = _finished(top, main)
        events = board._event_history(top)[1] if finished else {}
    except (AttributeError, KeyError, TypeError, OSError, ValueError, subprocess.SubprocessError, repo.Refused):
        return 0

    count = 0
    clean = []
    for path, branch, head, state in finished:
        ref = f"refs/heads/{branch}"
        try:
            item = task.branch_item(branch, path)
            if item and board.active_runs(path, item[0], events.get(item[0], [])): continue
            if not _removable(path, ref, head): continue
            if inspect:
                clean.append(str(path))
                continue
            removed = _remove_finished(main, path, ref, head, report, restore_lock=restore_lock)
            if removed is None: continue
            if removed.returncode:
                if report is not None:
                    report(f"Forge couldn't remove {path}: {_last(removed)}",
                           f"unlock it or close programs using it, then {REPAIR}")
                continue
            count += 1
            if repo.git("show-ref", "--hash", "--verify", ref, cwd=main) != head: continue
            deleted = repo.run("git", "branch", "-D", branch, cwd=main)
        except (OSError, ValueError, subprocess.SubprocessError, repo.Refused):
            continue
        if report is not None:
            if deleted.returncode:
                report(f"Removed {path}, but its branch {branch} is still here: "
                       f"{_last(deleted).rstrip('.')}.", f"git branch -D {branch}")
            else:
                print(f"- Fixed: removed {path}, whose pull request is {state}.")
    if clean and report is not None:
        report(f"{len(clean)} folders hold finished work: {', '.join(clean)}.")
    return count


def _unbuilt(top: Path) -> list[tuple[str, str]]:
    rows = []
    landed = story.landed_ref(top)
    now = datetime.fromisoformat(repo.now())
    for branch, path in story.worktrees(top).items():
        if not branch.startswith("fix/"): continue
        item = task.branch_item(branch, path)
        if not item: continue
        name, state = item
        if state.get("status") != "started": continue
        started = next((step["at"] for step in state.get("steps", []) if step["step"] == "start"), None)
        if not started or now - datetime.fromisoformat(started) <= timedelta(days=7): continue
        # The start record is a commit. Inherited work and merges of main are not this fix's work.
        commits = repo.git("rev-list", "--count", "--no-merges", branch, "--not",
                           state["base"], landed, cwd=top)
        if commits == "1":
            rows.append((f"Fix {name} started more than seven days ago and has no work commits.",
                         f'forge fix drop {name} --because "<reason>"'))
    return rows
def _contents(top: Path, specs: list[str]) -> dict[str, str]:
    if not specs: return {}
    done = subprocess.run([shutil.which("git") or "git", "cat-file", "--batch"], cwd=top,
                          input=("\n".join(specs) + "\n").encode("utf-8"), capture_output=True, check=True,
                          env={**os.environ, "FORGE_WORKER": "1"})
    contents = io.BytesIO(done.stdout)
    texts = {}
    for spec in specs:
        header = contents.readline()
        if header.endswith(b" missing\n"): texts[spec] = ""
        else:
            size = int(header.split()[-1])
            text = contents.read(size).decode("utf-8", errors="replace")
            contents.read(1)  # cat-file adds a newline after each blob's bytes.
            texts[spec] = text
    return texts
def _pin_changes(top: Path, commits: set[str]) -> set[str]:
    specs = [f"{commit}{parent}:forge.toml" for commit in sorted(commits) for parent in ("", "^")]
    pins = {spec: repo._pin(text) for spec, text in _contents(top, specs).items()}  # pyright: ignore[reportPrivateUsage]
    return {commit for commit in commits if pins[f"{commit}:forge.toml"] != pins[f"{commit}^:forge.toml"]}
def _agents_block(text: str) -> str:
    text = text.replace("\r\n", "\n")
    try:
        start, end = sync._span(text, "AGENTS.md")  # pyright: ignore[reportPrivateUsage]
    except repo.Refused:
        return text  # A broken historical block stays distinct; today's file is validated by sync.
    return text[start:end] if start != -1 else ""
def _history(top: Path, wanted: dict[str, str], ref: str) -> dict[str, str]:
    history = repo.git("log", "--format=commit %H%x00%P%x00%s", "-z", "--raw", "--no-renames",
                       "--no-abbrev", "--full-history", "--sparse", "--diff-merges=first-parent",
                       ref, "--", *wanted, cwd=top)
    parents: dict[str, list[str]] = {}
    subjects: dict[str, str] = {}
    changes: dict[tuple[str, str], tuple[str, str]] = {}
    fields = iter(history.split("\0"))
    commit = ""
    for field in fields:
        field = field.lstrip("\n")
        if field.startswith("commit "):
            commit = field.removeprefix("commit ")
            parents[commit] = next(fields).split()
            subjects[commit] = next(fields)
        elif field.startswith(":"):
            _, mode, _, blob, _ = field.split()
            rel = next(fields)
            changes[commit, rel] = (mode, blob) if mode != "000000" else ("", "")
    # Follow changes to Forge's block, rather than later commits to the client's rules.
    blobs = _contents(top, sorted({blob for (_, rel), (_, blob) in changes.items()
                                  if rel == "AGENTS.md" and blob}))
    for key, (mode, blob) in changes.items():
        if key[1] == "AGENTS.md" and blob:
            changes[key] = mode, _agents_block(blobs[blob])
    def entry(at: str, rel: str) -> tuple[str, str]:
        trail = []
        while at and (at, rel) not in changes:
            trail.append(at)
            at = next(iter(parents[at]), "")
        value = changes.get((at, rel), ("", ""))
        for ancestor in trail: changes[ancestor, rel] = value
        return value
    latest = {}
    for rel in wanted:
        at = next(iter(parents), "")
        while at:
            value = entry(at, rel)
            # Like log -- <one path>, follow the first parent with the same file.
            same = next((parent for parent in parents[at] if entry(parent, rel) == value), "")
            if same: at = same
            else:
                if parents[at] or value != ("", ""): latest[rel] = f"{at} {subjects[at]}"
                break
    return latest

def _changes(top: Path, cfg: dict[str, Any], wanted: dict[str, str],
             ref: str) -> tuple[set[str], dict[str, str]]:
    if not wanted: return set(), {}
    status = repo.git("status", "--porcelain=v2", "-z", "--no-renames", "--untracked-files=all",
                      "--ignored", "--", *wanted, cwd=top)
    dirty, staged = set(), set()
    for entry in status.split("\0"):
        if entry.startswith("1 "):
            _, xy, *_, rel = entry.split(" ", 8)
            dirty.add(rel)
            if xy[0] != ".": staged.add(rel)
        elif entry.startswith(("? ", "! ")): dirty.add(entry[2:])
        elif entry.startswith("u "):
            rel = entry.split(" ", 10)[-1]
            dirty.add(rel)
            staged.add(rel)
    if "AGENTS.md" in dirty and (top / "AGENTS.md").is_file():
        texts = _contents(top, ["HEAD:AGENTS.md", ":AGENTS.md"])
        head = _agents_block(texts["HEAD:AGENTS.md"])
        working = _agents_block((top / "AGENTS.md").read_bytes().decode("utf-8"))
        if working == head and _agents_block(texts[":AGENTS.md"]) == head:
            dirty.remove("AGENTS.md")
            staged.discard("AGENTS.md")
    latest = _history(top, wanted, ref)
    landed = (set(repo.git("rev-list", story.landed_ref(top), cwd=top).splitlines())
              if cfg["repo"] != "forge-source" else set())
    owned = {commit for last in latest.values() for commit, _, subject in [last.partition(" ")]
             if commit in landed and subject.startswith(WHY)}
    commits = {last.partition(" ")[0] for last in latest.values()} & landed
    free = owned | _pin_changes(top, commits - owned)
    held: dict[str, str] = {}
    for rel in wanted:
        if rel in dirty:
            held[rel] = "has changes not committed yet, so doctor won't overwrite it"
        else:
            last = latest.get(rel, "")
            commit, _, subject = last.partition(" ")
            held[rel] = ("" if not last or cfg["repo"] == "forge-source" or commit in free
                         else f"was changed by hand ({subject}), so doctor won't overwrite it")
    return staged, held

def _split(folder: Path, wanted: dict[str, str], staged: set[str],
           held: dict[str, str]) -> tuple[list[str], list[tuple[str, str]], frozenset[str]]:
    differing = set(sync.differing(folder, wanted))
    reasons = {rel: held.get(rel, "") for rel in wanted if rel in differing or rel in staged}
    free = [rel for rel, reason in reasons.items() if not reason]
    keep = {rel for rel, reason in reasons.items() if reason}
    rows = [(f"{rel} {reason}.", HAND) for rel, reason in reasons.items() if reason]
    if "AGENTS.md" in keep and "CLAUDE.md" in free:  # sync moves CLAUDE.md's lines into AGENTS.md
        free.remove("CLAUDE.md")
        keep.add("CLAUDE.md")
        rows.append(("CLAUDE.md stays until doctor can write AGENTS.md, since sync moves its lines " "there.", HAND))
    return free, rows, frozenset(keep)
def _linked(folder: Path, wanted: dict[str, str]) -> list[tuple[str, str]]:
    for rel in [*wanted, "AGENTS.md", "CLAUDE.md"]:
        path = folder / rel
        if any(part.is_symlink() for part in [path, *path.parents] if part.is_relative_to(folder) and part != folder):
            return [(f"{rel} is a link, so doctor repaired none of Forge's files.", f"replace the link with a regular file, then {REPAIR}")]
    return []
def _unfinished(name: str, branch: str, path: Path | None) -> tuple[str, str]:
    remove = (f'git worktree remove --force --force "{path}" and ' if path else "")
    return (f"Doctor's fix {name} isn't merged yet, so doctor started no new one.",
            f"finish it with forge close {name}, or remove it with {remove}git branch " f"-D {branch}, then {REPAIR}")
def _in_fix(top: Path, cfg: dict[str, Any], wanted: dict[str, str]) -> list[tuple[str, str]]:
    ref, default = story.landed_ref(top), repo.default_branch(top)
    if branch := _open_files_fix(top): return [_unfinished(branch.removeprefix("fix/"), branch, story.worktrees(top).get(branch))]
    staged, changes = _changes(top, cfg, wanted, ref)
    free, held, _ = _split(top, wanted, staged, changes)
    heads = repo.git("rev-parse", "HEAD", ref, cwd=top).splitlines()
    if (len(set(heads)) != 1 or repo.git("status", "--porcelain", "--untracked-files=all", cwd=top)):
        return [(f"Doctor needs a clean checkout at origin/{default} before it makes a fix for "
                 "Forge's files.", f"commit or discard your changes first, bring this checkout "
                 f"to origin/{default}, then {REPAIR}"), *_rows(free), *held]
    if not free: return held
    name = "forge-files-" + repo.now()[:16].replace("-", "").replace(":", "").replace("T", "-")
    branch = f"fix/{name}"
    if (_files_fix_finished(top, branch) or story.show(top, ref, repo.state_path(name)) is not None
            or repo.run("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", cwd=top).returncode == 0):
        return [(f"Doctor already used fix {name}, so doctor started no new one.",
                 f"run {REPAIR} again in the next minute"), *_rows(free), *held]
    who = repo.git("var", "GIT_AUTHOR_IDENT", cwd=top).split("<")[0].strip()
    state = {"kind": "fix", "why": WHY, "done_when": DONE, "base": repo.git("rev-parse", ref, cwd=top),
             "allow_large": "Doctor brings every file forge sync writes up to date in one change; "
                            f"{who} allowed it by running forge doctor --fix."}
    path = task._folder(f"fix-{name}")  # pyright: ignore[reportPrivateUsage]
    try:
        task._new_checkout(name, branch, f"fix-{name}", ref, state, f"Start the fix: {WHY}")  # pyright: ignore[reportPrivateUsage]
        fixed = repo.config(path)
        fixed_wanted = sync.files(path, fixed)
        if linked := _linked(path, fixed_wanted): return [(problem, _unfinished(name, branch, path)[1]) for problem, _ in linked]
        free, held, keep = _split(path, fixed_wanted, staged, changes)
        if free:
            free = sync.write(path, fixed, keep)
            repo.git("add", "-A", "-f", "--", *free, cwd=path)
            proof = close.generated_fix_proof(DONE,
                f"Forge {fixed['version']}'s forge sync brought these files up to date: "
                + ", ".join(free) + ".", name)
            repo.git("commit", "-q", "-m", WHY, "-m", proof, "--", *free, cwd=path)
    except (repo.Refused, OSError, subprocess.CalledProcessError) as failed:
        return [(f"Doctor couldn't bring Forge's files up to date in fix {name}: "
                        f"{_last(failed)}", _unfinished(name, branch, path)[1]), *held]
    if not free: return [_unfinished(name, branch, path), *held]
    print(f"- Fixed: wrote {len(free)} of Forge's files in fix {name}.")
    return [(f"Doctor's fix {name} holds Forge's files and isn't merged yet.", f"forge close {name}"), *held]

def _rows(free: list[str]) -> list[tuple[str, str]]:
    return [(f"{rel} differs from what forge sync writes for the installed Forge v{__version__}.", REPAIR) for rel in free]

def _files(top: Path, cfg: dict[str, Any], wanted: dict[str, str], fix: bool) -> list[tuple[str, str]]:
    if linked := _linked(top, wanted): return linked
    default = repo.default_branch(top)
    on_default, failed = repo.current_branch(top) == default, []
    if fix and on_default:
        fetched = repo.run("git", "fetch", "-q", "origin", cwd=top)
        if not fetched.returncode: return _in_fix(top, cfg, wanted)
        failed = [(f"doctor couldn't fetch {default} from origin, so it started no fix for " f"Forge's files: {_last(fetched)}",
                   f"check your network and GitHub access, then {REPAIR}")]
    staged, changes = _changes(top, cfg, wanted, story.landed_ref(top) if on_default else "HEAD")
    free, rows, keep = _split(top, wanted, staged, changes)
    if not fix or not free or failed: return failed + _rows(free) + rows
    try:  # forge sync's own write, so deletions and links behave exactly as there
        written = sync.write(top, cfg, keep)
    except (repo.Refused, OSError) as error:  # what is written stays, as forge sync leaves it
        still = [rel for rel in sync.differing(top, sync.files(top, cfg)) if rel not in keep]
        written = [rel for rel in free if rel not in still]
        if isinstance(error, repo.Refused) and error.entry is repo.REFUSALS["default_branch"]:
            problem, _, next_step = str(error).partition("\nNext: ")
            failure = (problem, next_step)  # a detached HEAD: sync's own refusal
        else: failure = (f"doctor couldn't write Forge's files: {_last(error)}", REPAIR)
        rows = [failure, *_rows(still), *rows]
    for rel in written: print(f"- Fixed: {'wrote' if (top / rel).exists() else 'removed'} {rel}.")
    return rows

def doctor(args: argparse.Namespace) -> int:
    top = repo.root()
    cfg = repo.config(top)
    if (cfg["test_place"] == "local" and set(cfg["checks"]) == {"forge-pr-check"}
            and "test_place" not in tomllib.loads(sync.read(top / "forge.toml"))):
        print('- Warning: Close runs tests on this machine because checks names only '
              'forge-pr-check, which runs no app tests. Ask the agent to set '
              'checks = ["forge-pr-check", "tests"] in a fix whose Done-when names '
              'forge.toml, then run forge sync.')
    if warning := quicktest.group_warning(top, cfg):
        print(f"- Warning: {warning}")
    test, fast = cfg["test"], cfg["fast_test"]
    same_selection = (test != fast and bool(fast)
                      and test.replace("{base}", "").split() == fast.replace("{base}", "").split())
    if test and (same_selection or "{base}" in test or re.search(
            r"\b(changed|changedSince|onlyChanged|affected|related)\b|--(?:pytest|change|lf|ff|last-failed)\b", test)):
        print("- Warning: The nightly full run needs test to run the full suite. "
              "The test command looks like a change selector. Keep change selection in fast_test.")
    install = sync.install_line(cfg["version"])
    rows: list[tuple[str, str]] = []
    def add(problem: str, fix: str = REPAIR) -> None: rows.append((problem, fix))
    pinned = "v" + cfg["version"].removeprefix("v")
    if pinned != f"v{__version__}":
        problem = repo.REFUSALS["pin"][0].format(installed=f"v{__version__}", pinned=pinned)
        release, installed = (re.match(r"v?(\d+)\.(\d+)\.(\d+)", v) for v in (pinned, __version__))
        repairs = bool(release and installed and tuple(map(int, release.groups())) >
                       tuple(map(int, installed.groups()))) and os.environ.get("FORGE_PINNED_RUN") != pinned
        if repairs and args.fix and shutil.which("uv"):
            done = repo.run(*install.split())
            forge = shutil.which("forge")
            if done.returncode == 0 and forge:
                print(f"- Fixed: installed Forge {pinned}, the version this repo pins.", flush=True)
                return subprocess.run([forge, "doctor", "--fix"], env={**os.environ, "FORGE_PINNED_RUN": pinned}).returncode
            said = _last(done) if done.returncode else "no forge is on PATH after uv installed it"
            add(f"{problem} Installing it failed: {said}", install)
        else: add(problem, REPAIR if repairs and not args.fix else install)
    antigravity_selected = cfg["workers"] == "antigravity" or cfg.get("reviews") == "antigravity"
    workers = cfg["workers"] if cfg["tools"] == "both" else cfg["tools"]
    if cfg["workers"] == "antigravity":
        workers = "antigravity"
    if item := task.branch_item(repo.current_branch(top), top):
        workers = item[1].get("tool") or workers
    if antigravity_selected:
        reader = cfg.get("reviews") or ("codex" if cfg["tools"] == "both" else cfg["tools"])
        on_codex = workers in ("codex", "split") or reader == "codex"
        on_claude = workers in ("claude", "split") or reader == "claude"
    else:
        on_codex = workers != "claude" or cfg["tools"] == "both"
        on_claude = workers != "codex"
    programs = {"codex": shutil.which(os.environ.get("CODEX_BIN") or "codex"),
                "claude": shutil.which("claude")}
    if (cfg["tools"] != "both" and not programs[cfg["tools"]]
            and (not antigravity_selected or cfg["tools"] == "codex" and on_codex
                 or cfg["tools"] == "claude" and on_claude)):
        add(f"{cfg['tools']} is not installed or not on PATH.", INSTALL[cfg["tools"]])
    # Kits supply their own executables; their repair needs no standalone program.
    needs_sdk = bool(cfg["tools"] == "both" or cfg["tools"] == "codex"
                     and (cfg["codex_fast"] == "off" or programs["claude"]))
    if antigravity_selected:
        needs_sdk = bool(on_codex and needs_sdk)
    needs_sdk = needs_sdk or cfg.get("reviews") == "codex"
    sdk_failed = ""
    if args.fix and needs_sdk and shutil.which("uv") and codex.sdk_problem():
        try: codex.install()
        except repo.Refused as refused: sdk_failed = str(refused).partition("\nNext: ")[0]
    for tool in ("git", "gh", "uv"):
        if not shutil.which(tool): add(f"{tool} is not installed or not on PATH.", INSTALL[tool])
    if shutil.which("gh") and repo.run("gh", "auth", "status", cwd=top).returncode: add("gh is not signed in to GitHub.", "gh auth login")
    if on_claude and programs["claude"] and init.signed_in("claude", top) is False:
        add("Claude is not signed in.", "run claude and sign in")
    if on_codex and init.signed_in("codex", top) is False:
        add("Codex is not signed in.", "codex login")
    if antigravity_selected:
        if problem := antigravity.problem():
            add(problem, antigravity.INSTALL)
        else:
            signed_in, reason = antigravity.signed_in(top)
            if signed_in is False:
                add("Antigravity is not signed in.", "run agy and sign in")
            elif signed_in is None:
                add(f"Forge could not check Antigravity's sign-in: {reason}.",
                    "run agy to check it, then forge doctor")
            if os.environ.get("SSH_CONNECTION"):
                signed_in, reason = antigravity.signed_in(top, mode="full")
                if signed_in is False:
                    add("Antigravity's full profile for this checkout is not signed in.", reason)
                elif signed_in is None:
                    add(f"Forge could not check Antigravity's sign-in for this checkout: {reason}.",
                        "run agy to check it, then forge doctor")
    if needs_sdk and (problem := sdk_failed or codex.sdk_problem()): add(problem)
    needs_claude_sdk = bool(cfg["tools"] == "both" or cfg["tools"] == "claude" and programs["codex"])
    if antigravity_selected:
        needs_claude_sdk = bool(on_claude and needs_claude_sdk)
    needs_claude_sdk = needs_claude_sdk or cfg.get("reviews") == "claude"
    claude_failed = ""
    if args.fix and needs_claude_sdk and shutil.which("uv") and claude_sdk.sdk_problem():
        try: claude_sdk.install()
        except repo.Refused as refused: claude_failed = str(refused).partition("\nNext: ")[0]
    if needs_claude_sdk and (problem := claude_failed or claude_sdk.sdk_problem()): add(problem)
    try:  # the reviewer close runs, at the version Forge pins
        review.helper()
    except repo.Refused as refused: add(str(refused).partition("\nNext: ")[0], INSTALL["autoreview"])
    try:
        wanted = sync.files(top, cfg)
        compared = ("- Note: doctor compared the synced files with the installed Forge " f"v{__version__}")
        compared += "." if pinned == f"v{__version__}" else (
            f", not the pinned {pinned}.\n  To check with {pinned}: {install}, then run forge " "doctor again.")
    except repo.Refused as refused:
        problem, _, fix = str(refused).partition("\nNext: ")
        add(f"doctor couldn't compare the synced files with what forge sync writes: " f"{problem}", fix)
        wanted, compared = {}, ""
    driver = repo.run("git", "config", "--get", "merge.forge-roadmap.driver", cwd=top).stdout.strip()
    attributes = sync.read(Path(repo.git("rev-parse", "--path-format=absolute", "--git-path", "info/attributes", cwd=top)))
    merge_drift = driver != sync.MERGE_DRIVER or sync.merge_attributes(attributes) != attributes
    hooks_drift = any(sync.read(path) != text for path, text in sync.shims(top, cfg).items())
    if hooks_drift or merge_drift:
        if not args.fix: add("The git hooks that check each commit and push aren't installed."
                         if hooks_drift else "The roadmap and spotted-list merge rule doesn't " "match the installed Forge.")
        else:
            try:  # never committed, so this repair runs on the default branch too
                if hooks_drift: sync.install_shims(top, cfg)
                else: sync.install_merge_rules(top)
                print("- Fixed: installed the git hooks that check each commit and push."
                      if hooks_drift else "- Fixed: installed the roadmap and spotted-list merge rule.")
            except repo.Refused as refused:
                problem, _, fix = str(refused).partition("\nNext: ")
                add(problem, fix)
    rows += _unbuilt(top)
    tidy_finished(top, inspect=not args.fix, restore_lock=args.fix, report=add)
    rows += _files(top, cfg, wanted, args.fix and pinned == f"v{__version__}")
    if not shutil.which("sh"): add("sh isn't on PATH, so no host hook can run.", "install Git, which brings sh, and put it on PATH")
    elif wanted and sync.read(top / sync.LAUNCHER) != wanted.get(sync.LAUNCHER):
        add(f"doctor didn't run the host hooks, because {sync.LAUNCHER} differs from what " "forge sync writes.")
    else:
        env = {**os.environ, "PATH": BARE_PATH} if os.name != "nt" else None  # Windows has no /usr/bin
        bare = f" when run with PATH={BARE_PATH}" if env else ""
        checked: dict[tuple[str, str], subprocess.CompletedProcess[str]] = {}
        for rel in sync.HOSTS:
            generated = set(_forge_hooks(wanted.get(rel, "")))
            for event, command in _forge_hooks(sync.read(top / rel)):
                if (event, command) not in generated: continue
                key = (event, command)
                if key not in checked:
                    payload = {"session_id": "forge-doctor", "cwd": str(top), "hook_event_name": event, **SAMPLES.get(event, {})}
                    checked[key] = subprocess.run( [shutil.which("sh") or "sh", "-c", command], cwd=top,
                        input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
                done = checked[key]
                if done.returncode:
                    said = (done.stderr.strip() or "it printed nothing").splitlines()
                    fix = next((line[6:] for line in said if line.startswith("Next: ")), install)
                    add(f"The {event} hook in {rel} fails with exit code " f"{done.returncode}{bare}: {said[0]}", fix)
    if cfg["test_place"] == "ci" and not cfg["checks"]:
        add("forge.toml names no checks, so close has nothing to wait for.", "ask your agent to set checks in forge.toml")
    if shutil.which("gh"):
        from forge import citime
        if warning := citime.warning(top):
            print(f"- Warning: {warning}")
        prs = _prs(top, repo.current_branch(top), "--json", "headRefOid,state,number,headRefName")
        for pr in prs if isinstance(prs, list) else []:
            if not isinstance(pr, dict) or pr.get("state") != "OPEN" or not pr.get("headRefOid"):
                continue
            try:
                if reason := checks.queued_reason(top, pr["headRefOid"], number=pr.get("number"),
                                                  branch=pr.get("headRefName") or ""):
                    add(reason, "make a matching runner available or correct the setting in forge.toml, "
                        "then run forge sync only if you change the runner setting")
            except repo.Refused as error:
                add(str(error).partition("\nNext: ")[0], "check gh auth status and GitHub access, "
                    "then run forge doctor")
    protection = (repo.run("gh", "api", f"repos/{{owner}}/{{repo}}/branches/" f"{repo.default_branch(top)}/protection", cwd=top)
                  if shutil.which("gh") else None)
    plan_note = (init.skipped(repo.default_branch(top), cfg["checks"]) if protection and init.no_protection_plan(protection) else "")
    if protection and (protection.returncode == 0 or "Branch not protected" in protection.stdout + protection.stderr):
        try:
            required = json.loads(protection.stdout).get("required_status_checks") or {}
            protected = {entry["context"] for entry in required.get("checks") or []
                         if isinstance(entry, dict) and isinstance(entry.get("context"), str)}
            protected.update(name for name in required.get("contexts") or [] if isinstance(name, str))
        except (ValueError, AttributeError): protected = set()
        if protected != set(cfg["checks"]): add("forge.toml checks differ from branch protection's required checks: "
                         f"Forge names {', '.join(sorted(cfg['checks'])) or 'none'}; protection "
                         f"requires {', '.join(sorted(protected)) or 'none'}.", "ask your agent to reconcile checks in forge.toml with branch protection")
    if "python -m forge.fasttest" in cfg["fast_test"]:
        add("fast_test still runs python -m forge.fasttest in the client's environment.",
            'replace it with fast_test = "forge test --pytest {base}" in forge.toml')
    if not cfg["test"]: add("forge.toml has no test command.", "ask your agent to set test in forge.toml, then run forge sync")
    elif cfg["test_place"] == "ci" and "tests" in cfg["checks"]:
        workflow = sync.read(top / sync.WORKFLOW_PATH)
        tests_job = re.search(r"^  tests:\n(.*?)(?=^  [\w-]+:\n|\Z)", workflow, re.M | re.S)
        tests_job = tests_job[1] if tests_job else ""
        if "forge test --change" not in tests_job:
            add(f"The tests check in {sync.WORKFLOW_PATH} does not run forge test --change.")
    codex_config = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml"
    trusted, trust = _codex_trust(top, codex_config)
    if on_codex and not trusted: add("Codex doesn't trust this project, so it would skip Forge's hooks and the "
                     "project's Codex settings.", trust)
    skills = {"claude": [Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"), top / ".claude"],
              "codex": [codex_config.parent, Path.home() / ".agents", top / ".codex", top / ".agents"],
              "antigravity": [Path.home() / ".gemini/config", Path.home() / ".gemini/antigravity-cli",
                              Path.home() / ".gemini", top / ".agents", top / ".codex"]}
    package = top / "package.json"
    packages = json.loads(sync.read(package)) if package.is_file() else {}
    dependencies = {**packages.get("dependencies", {}), **packages.get("devDependencies", {})}
    has_frontend = (any((top / path / "package.json").is_file() for path in ("frontend", "web", "apps/web"))
                    or any(name in dependencies for name in ("react", "react-dom", "vue", "svelte", "@angular/core", "next", "vite")))
    if has_frontend:
        for host in (host for host in skills if cfg["tools"] == host or cfg["tools"] == "both"
                     and (workers in (host, "split") or shutil.which(host))
                     or host == "antigravity" and workers == "antigravity"):
            for skill in ("impeccable", "emil-design-eng"):
                if not any((folder / "skills" / skill / "SKILL.md").is_file() for folder in skills[host]):
                    add(f"{skill} is required for UI work but isn't installed where the " f"{host} worker reads skills.", INSTALL[skill])
    for line in codex.tidy(top): print(f"- {line}")
    for problem, fix in rows: print(f"- {problem}\n  Fix: {fix}")
    if local := cfg.get("local"):
        entries = [(kind, table) if "model" in table else (f"{kind}.{tool}", entry)
                   for kind, table in local.get("models", {}).items()
                   for tool, entry in ([("", table)] if "model" in table else table.items())]
        print(f"- Note: {repo.LOCAL} overrides " + ", ".join(
            [f"{key} = {local[key]}" for key in ("tools", "workers") if key in local]
            + [f"models.{name} ({', '.join(f'{key} {value}' for key, value in entry.items())})"
               for name, entry in entries]) + ".")
    if plan_note: print(f"- Note: {plan_note}")
    quicktest.combined_note(top, cfg)
    quicktest.suggest(top, cfg)
    if cfg["fast_test"]: print(f"- Note: change tests use fast_test ({cfg['fast_test']}) instead of test, with {{base}} as "
              "the merge base with the default branch" + (". The pull request's tests check runs related tests. "
              "The nightly full run covers the rest"
              if cfg["test_place"] == "ci" else "") + ".")
    if on_codex: print("- Note: when Codex asks you to approve Forge's hooks, approve them; Forge can't see " "whether you did.")
    elif cfg["tools"] == "both" and not trusted: print("- Note: Codex runs this repo's hooks only in a project it trusts, and it doesn't "
              f"trust this one yet.\n  Fix: {trust}")
    if rows:
        if compared: print(compared)
    else:
        print(f"Everything {'checks' if trusted or cfg['tools'] == 'claude' else 'else checks'} out for Forge {cfg['version']}.")
        print(compared)
    cores = getattr(os, "process_cpu_count", os.cpu_count)() or 2
    runners = machine.busy_runners()
    budget = machine.half_cores(runners)
    print(f"This machine: {cores} cores, so {budget} agents at once and "
          f"{machine.test_slots(runners)} test processes shared by all runs.")
    memory = machine.memory()
    free = memory["available_bytes"]
    available = "unknown" if free is None else f"{free / 1e9:.1f} GB"
    print(f"Memory: {available} free, floor {machine.memory_floor(memory) / 1e9:.1f} GB.")
    tests = [run for run in machine.entries() if run["kind"] == "test"]
    processes = machine.test_allocation(tests)
    print(f"Test processes in use: {processes}. Busy runners: {runners} ({runners} cores reserved).")
    for run in tests:
        if "processes" not in run:
            print(f"Older-release test run: {run.get('title') or run.get('item') or run['repo_name']}; "
                  f"counts as {machine.half_cores(0)} test processes.")
    if os.name != "nt":
        processes = repo.run("ps", "-axo", "command=")
        if processes.returncode == 0 and re.search(
                r"^(?:\S*/)?Runner\.Listener(?:\s|$)|"
                r"^(?:(?:\S*/)?(?:bash|sh|dash|zsh)\s+)?(?:\S*/)?actions-runner/run\.sh(?:\s|$)",
                processes.stdout, re.M):
            print("- Warning: a GitHub Actions self-hosted runner runs on this machine. "
                  "Its CPUs count against Forge's load limit.")
    if on_codex:
        fast = {"needed": "on for every fix, after the first repair round, or when other planned work waits",
                "off": "off", "always": "always on"}[cfg["codex_fast"]]
        from forge import event_log
        history = event_log.read(top)
        last = next((row for row in reversed(history) if row.get("event") == "codex speed"), None)
        said = ("" if last is None else " The last Codex turn ran with Fast."
                if last["tier"] not in (None, "default") and last["tier"] == last["requested_tier"] else
                " Codex reported a different speed from the one Forge requested."
                if last["tier"] not in (None, "default") else
                " Codex did not report the last turn's speed." if last["tier"] is None else
                " The last Codex turn wanted Fast, but Codex reported normal speed."
                if last.get("fast_wanted") and last["requested_tier"] != "default" else
                " The last Codex turn ran at normal speed.")
        if last and last.get("fast_wanted") and last["requested_tier"] == "default":
            said = f" The last Codex turn wanted Fast, but {last['model']} doesn't offer it." + said
        print(f"- Codex Fast: {fast}; models without Fast run normally.{said}")
    claude = shutil.which("claude")
    version = None
    if claude:
        try:
            checked = subprocess.run([claude, "--version"], cwd=top, input="", capture_output=True,
                                     text=True, encoding="utf-8", errors="replace", timeout=30)
            if checked.returncode == 0:
                version = re.search(r"(\d+)\.(\d+)\.(\d+)", checked.stdout)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not version or tuple(map(int, version.groups())) < (2, 1, 287):
        print("- Warning: Claude Code is missing or older than v2.1.287; upgrade Claude Code to use the Forge pane.")
    if rows: repo.refuse(REFUSALS["problems"], count=len(rows))
    return 0
