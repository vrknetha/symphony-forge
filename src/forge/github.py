"""GitHub reads, quota recovery and admission for check waits."""
import json
import math
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

wait_for_reset = False  # Shared command setup enables this only for close, merge and land.


def _quota(cwd, fresh=False):
    """One quota lookup per 45 seconds across this repository's worktrees, including failures."""
    from forge import codex, repo

    cache = repo.forge_dir(cwd) / "github-quota.json"
    with codex._one_at_a_time(cache):
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            # A fresh reading still reuses a lookup that just failed: the endpoint refused us a moment ago.
            if 0 <= time.monotonic() - saved["at"] < 45 and (not fresh or not saved["resources"]):
                return saved["resources"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        done = repo.run("gh", "api", "rate_limit", cwd=cwd, timeout=60)
        try:
            resources = json.loads(done.stdout)["resources"] if done.returncode == 0 else {}
            if not isinstance(resources, dict):
                resources = {}
        except (ValueError, KeyError, TypeError):
            resources = {}
        temp = cache.with_suffix(".tmp")
        temp.write_text(json.dumps({"at": time.monotonic(), "resources": resources}), encoding="utf-8")
        temp.replace(cache)
        return resources


def _numbers(resources):
    """The quota a wait follows: remaining and limit for REST and GraphQL, with each reset time."""
    parts = []
    for label, name in (("REST", "core"), ("GraphQL", "graphql")):
        try:
            quota = resources[name]
            parts.append(f"{label} {quota['remaining']}/{quota['limit']}, resets "
                         + datetime.fromtimestamp(int(quota["reset"]), timezone.utc).strftime("%H:%M:%S UTC"))
        except (KeyError, TypeError, ValueError):
            parts.append(f"{label} unavailable")
    return "; ".join(parts)


def _wait_until(cwd, ready, say, fresh=False, wake=None, stream=None):
    """Shared quota wait: recheck every 15 seconds (the shared lookup is at most 45 seconds old,
    so the quota is read at least once a minute), print the numbers at least every two minutes.
    `wake` gives the monotonic time the wait ends, so the last sleep does not overshoot it."""
    said_at = None
    while True:
        resources = _quota(cwd, fresh)
        fresh = False
        if ready(resources):
            return
        if said_at is None or time.monotonic() - said_at >= 120:
            print(say(resources), file=stream, flush=True)
            said_at = time.monotonic()
        time.sleep(15 if wake is None else max(0, min(15, wake() - time.monotonic())))


@contextmanager
def check_wait(cwd, slot=None):
    """Keep quota admission separate from a borrowed land place."""
    from forge import codex, repo

    folder = repo.forge_dir(cwd)
    held = None
    lent = False
    state = {}

    def release():
        nonlocal held
        if held is not None:
            codex._unlock(held)
            held.close()
            held = None

    def waiting(value):
        nonlocal lent
        if slot is not None and value != lent:
            if not value:
                release()  # Other land children may hold every land place while waiting for quota.
            lent = value
            slot(value)

    def admit():
        from forge import checks

        def ready(resources):
            nonlocal held
            limits = []
            for name, per_poll in (("core", 6), ("graphql", 2)):
                # One poll spends about three REST requests (pages and queue recovery) and
                # one GraphQL PR read; the numbers carry a margin of two. FORGE_CHECKS_POLL
                # sets how many polls run each minute.
                try:
                    quota = resources[name]
                    remaining = max(0, int(quota["remaining"]))
                    minutes = max(1, math.ceil((int(quota["reset"]) - time.time()) / 60))
                    # One place stays open while any quota remains. No wait polls faster than
                    # once a second, however FORGE_CHECKS_POLL is set (tests set it to 0.01).
                    limits.append(max(1 if remaining else 0,
                                      int(remaining // (minutes * per_poll * 60 / max(checks.POLL, 1)))))
                except (KeyError, TypeError, ValueError):
                    limits.append(1)  # An unavailable quota permits only one wait.
            state["allowed"] = min(*limits, 8)  # ponytail: eight waits is plenty on one machine
            with codex._one_at_a_time(folder / "github-check-waits"):
                # Renew before each poll. Count every holder, including places
                # above a newly reduced budget, before admitting another wait.
                release()
                paths = sorted(folder.glob("github-check-wait-*.lock"))
                active, free = 0, None
                for path in paths:
                    with path.open("a+b") as candidate:
                        if codex._try_lock(candidate):
                            codex._unlock(candidate)
                            free = path
                        else:
                            active += 1
                state["active"] = active
                if active < state["allowed"]:
                    candidate = (free or folder / f"github-check-wait-{len(paths)}.lock").open("a+b")
                    if codex._try_lock(candidate):
                        held = candidate
                        return True
                    candidate.close()
            return False

        _wait_until(cwd, ready, lambda resources: (
            "Waiting for GitHub API quota before another check wait. " + _numbers(resources)
            + f". Places in use {state['active']}, allowed {state['allowed']}. Checking again each minute."))

    try:
        admit()
        yield admit, waiting
    finally:
        release()
        waiting(False)


def run(args, execute, cwd):
    if not wait_for_reset or args[1:3] == ("api", "rate_limit"):
        return execute()
    name = "graphql" if args[1:3] == ("api", "graphql") else "core"

    while True:
        done = execute()
        said = done.stderr + done.stdout
        if not done.returncode or not re.search(
                r"\brate limit\b.*\bexceeded\b|\bexceeded\b.*\brate limit\b|\bHTTP\s+429\b", said, re.I | re.S):
            return done
        failed_at, failed_time = time.monotonic(), time.time()
        due, primary, shown = None, False, False  # `due`: wall-clock time the wait ends

        def ready(resources):
            nonlocal due, primary
            try:
                quota = resources[name]
                remaining, reset = int(quota["remaining"]), int(quota["reset"]) + 3
            except (ValueError, KeyError, TypeError, AttributeError):
                remaining, reset = None, 0  # An unavailable lookup still permits the one-minute retry.
            if due is None:  # The reading taken just after the failure says which limit it was.
                primary = remaining == 0 and reset > failed_time
                due = reset if primary else failed_time + 60
            if remaining is None:  # A failed refresh falls back to the one-minute retry.
                primary, due = False, min(due, failed_time + 60)
            # The wall clock may not move with the monotonic one, so count the wait on the latter.
            return bool(primary and remaining) or time.monotonic() - failed_at >= due - failed_time

        def say(resources):
            nonlocal shown
            if shown:
                return f"Still waiting for GitHub API quota: {_numbers(resources)}. Checking again each minute."
            shown = True
            when = datetime.fromtimestamp(due, timezone.utc).strftime("%H:%M:%S UTC")
            return f"{_numbers(resources)}. GitHub rate limit reached. Wait until {when}, then continue."

        _wait_until(cwd, ready, say, fresh=True, stream=sys.stderr,
                    wake=lambda: failed_at + due - failed_time)


def read(args: tuple[str, ...], execute) -> subprocess.CompletedProcess[str]:
    """Retry reads only: replaying a write after an unreadable receipt could duplicate it."""
    from forge import repo

    if args[1:3] == ("api", "rate_limit"):
        return execute()  # Cache a failed lookup too; never spend retries on the quota endpoint.
    api = args[1:2] == ("api",)
    read = (args[1:3] in (("pr", "list"), ("pr", "view"), ("pr", "checks"),
                         ("run", "list"), ("run", "view"),
                         ("release", "list"), ("release", "view")))
    if api:
        # gh infers POST from fields; our GraphQL query is a read despite that POST.
        read = (not any(flag in args for flag in ("-f", "-F", "--field", "--raw-field", "--input"))
                or ("graphql" in args and any(re.match(r"query=\s*(?:\{|query\b)", arg)
                                              for arg in args)))
        if "--method" in args or "-X" in args:
            flag = "--method" if "--method" in args else "-X"
            read = args[args.index(flag) + 1].upper() == "GET"
    if not read:
        return execute()
    jq = args[args.index("--jq") + 1] if "--jq" in args else None
    structured = api or "--json" in args
    for pause in (1, 2, 4, None):
        done = execute()
        said = done.stderr + done.stdout
        if done.returncode and re.search(r"\bHTTP\s+(?:401|403|404)\b", said, re.I):
            return done
        unreadable = False
        if structured and done.returncode == 0:
            text = done.stdout.strip()
            try:
                if ((jq is None and api and "--paginate" in args and "--slurp" not in args)
                        or (jq is not None and jq.endswith("[]"))):
                    decoder = json.JSONDecoder()
                    while text:
                        _, end = decoder.raw_decode(text)
                        text = text[end:].lstrip()
                elif jq is None:
                    json.loads(text)
                else:
                    unreadable = text.startswith("<")
            except ValueError:
                unreadable = True
        transient = unreadable or (structured and (done.stdout.lstrip().startswith("<")
                                                   or done.stderr.lstrip().startswith("<"))) or (done.returncode and (
            re.search(r"\bHTTP\s+5\d\d\b", said, re.I)
            or re.search(r"\bunexpected EOF\b|\binvalid character\b", said, re.I)
            or "looking for beginning of value" in said
            or "unexpected end of JSON input" in said
            or any(text in said for text in repo.NETWORK)))
        if not transient:
            return done
        if pause is None:
            return subprocess.CompletedProcess(done.args, 1, "",
                                               repo.REFUSALS["no_github"][0] + "\n")
        time.sleep(pause)
