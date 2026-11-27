"""Read the worker's Done-when proof list and check its named tests."""
from __future__ import annotations

import collections
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from forge import repo

LINE = re.compile(r"^\s*(?:-\s*)?(?P<key>\d+(?:\s*,\s*\d+)*|Done when)\s*:\s*(?P<rest>.*)$",
                  re.I)
TEST_NAME = re.compile(r"`?(?P<name>(?:[\w.-]+/)*(?:test_[\w-]*|[\w-]+_test)\.py"
                       r"(?:::(?:[^\s,;`\[]+|\[[^\]]*\])+)?)`?")
JS_NAME = re.compile(r"`(?P<name>(?:[\w.-]+/)*[\w.-]+\.[cm]?[jt]sx?"
                     r"(?:::[^`]+| > [^`]+)*)`|(?P<plain>(?:[\w.-]+/)*[\w.-]+\.[cm]?[jt]sx?)")
RESULT_WORDS = ("passed", "failed", "error", "skipped", "xfail", "xpass")
CI_DOCS_ONLY = ("CI treats this change as docs only and skips tests; "
                "only test names on the branch are checked.")


def _test(rest: str) -> tuple[str, int, int] | None:
    """The test at the start of a proof line, its span, and its kind."""
    if rest.lower().startswith("check:"):
        return "check:", 0, len("check:")
    if match := TEST_NAME.match(rest):
        return match["name"], *match.span("name")
    if match := JS_NAME.match(rest):
        group = "name" if match["name"] else "plain"
        return match[group], *match.span(group)
    return None


def _line(line: str) -> tuple[list[str], str, tuple[str, int, int] | None] | None:
    match = LINE.match(line)
    if not match:
        return None
    raw = match["key"].strip()
    keys = [str(int(value.strip())) for value in raw.split(",")] if raw.lower() != "done when" else ["Done when"]
    rest = match["rest"]
    found = _test(rest.lstrip())
    if found:
        name, start, end = found
        leading = len(rest) - len(rest.lstrip())
        found = name, start + leading, end + leading
    return keys, rest, found


def _proof(top: Path, item: str, commit: str, base: str | None = None) -> tuple[str, str]:
    """The newest proof paragraph and the base that bounds its branch history."""
    from forge import githooks, review, story

    state = _state(top, item, commit)
    if not state:
        return "", ""
    if base is None:
        base = githooks.fix_base(top, state, story.landed_ref(top), commit)
    return review.commit_paragraph(top, base, "Proof list:", commit), base


def _state(top: Path, item: str, commit: str) -> dict[str, Any]:
    from forge import story

    if "/" in item:
        key, _, task = item.partition("/")
        path = f".factory/stories/{key}/tasks/{task}.json"
    else:
        path = f".factory/fixes/{item}.json"
    text = story.show(top, commit, path)
    return story.json_of(text) if text else {}


def _parsed(proof: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in proof.splitlines():
        parsed = _line(line)
        if not parsed:
            continue
        keys, _, test = parsed
        names = [test[0]] if test and test[0] else []
        for key in keys:
            found.setdefault(key, []).extend(names)
    return found


def entries(top: Path, item: str, commit: str, base: str | None = None) -> dict[str, list[str]]:
    """Each covered Done-when key to its named tests, or ["check:"]."""
    proof, _ = _proof(top, item, commit, base)
    return _parsed(proof)


def _covered(top: Path, item: str, commit: str) -> list[str]:
    if "/" not in item:
        return ["Done when"]
    from forge import review, story

    text, _, row = review.task(top, item, commit)
    parsed = story.parse(text)
    covers = {int(number) for number in re.findall(r"\d+", row.get("covers", ""))}
    return [str(number) for number in parsed["done"] if number in covers]


def _tree(top: Path, commit: str) -> set[str]:
    return set(filter(None, repo.git("ls-tree", "-r", "--name-only", commit, cwd=top).splitlines()))


def _blob(top: Path, commit: str, path: str) -> str:
    if Path(path).is_absolute() or ".." in Path(path).parts:
        return ""
    result = repo.run("git", "show", f"{commit}:{path}", cwd=top)
    return result.stdout if result.returncode == 0 else ""


def _on_branch(top: Path, commit: str, name: str) -> bool:
    path = re.split(r"::| > ", name, maxsplit=1)[0]
    if path not in _tree(top, commit):
        return False
    source = _blob(top, commit, path)
    if path.endswith(".py"):
        case = name.rsplit("::", 1)[-1] if "::" in name else ""
        case = re.sub(r"\[.*", "", case)
        return not case or bool(re.search(rf"\b{re.escape(case)}\b", source))
    case = (name.rsplit(" > ", 1)[-1] if " > " in name else
            name.rsplit("::", 1)[-1] if "::" in name else "")
    return not case or case in source


def _matches(name: str, node: str, files: set[str]) -> bool:
    path, _, selector = name.partition("::")
    node_path, _, node_selector = node.partition("::")
    if path != node_path:
        # pytest can report paths relative to a nested project root. Permit that only when
        # the shorter path cannot name another test file in this checkout.
        if node_path in files:
            return False
        candidates = [candidate for candidate in files if candidate.endswith("/" + node_path)]
        if len(candidates) != 1 or candidates[0] != path:
            return False
    if not selector:
        return True
    expected, actual = selector.split("::"), node_selector.split("::")
    if len(expected) > len(actual):
        return False
    return all(wanted == (got if "[" in wanted else re.sub(r"\[.*", "", got))
               for wanted, got in zip(expected, actual))


def _results(report: str) -> dict[str, str]:
    from forge import fasttest

    outcomes: dict[str, str] = {}
    rank = {"passed": 0, "skipped": 1, "xfail": 1, "xpass": 1, "failed": 2, "error": 3}
    for attempt in report.split(fasttest.RETRY_HEADER):
        current: dict[str, str] = {}
        for outcome, node in re.findall(r"^(passed|failed|error|skipped|xfail|xpass) (.+)$", attempt, re.M):
            current[node] = max(current.get(node, outcome), outcome, key=rank.__getitem__)
        retried = {node.split("::", 1)[0] for node in current}
        outcomes = {node: result for node, result in outcomes.items()
                    if node.split("::", 1)[0] not in retried}
        outcomes.update(current)
    return outcomes


def _result_for(name: str, outcomes: dict[str, str], files: set[str]) -> list[tuple[str, str]]:
    return [(outcome, node) for node, outcome in outcomes.items() if _matches(name, node, files)]


def _generated_only(top: Path, base: str, head: str) -> bool:
    from forge import review, sync

    changed = {path for path in repo.git("diff", "--name-only", "--no-renames",
                                         f"{base}...{head}", cwd=top).splitlines()
               if path and not path.startswith(review.BOOKKEEPING)}
    changed.discard("forge.toml")
    if not changed:
        return True
    # A client's own generated files, such as an API client, change what the app does: not exempt.
    cfg = repo._config_text(_blob(top, head, "forge.toml"))
    listing = repo.git("ls-tree", "-r", "-z", "--full-tree", head, cwd=top).split("\0")
    hashes = {path: entry.partition("\t")[0].split()[-1] for entry in listing
              if (path := entry.partition("\t")[2])}
    return not changed - sync.synced(top, cfg, base, head, sorted(changed), hashes=hashes)


def check(top: Path, item: str, base: str, results: str, *, ran: bool = True,
          head: str = "HEAD") -> tuple[bool, list[str]]:
    """Check each covered proof name, then named pytest outcomes from this run."""
    state = _state(top, item, head)
    if not state or repo.sample_data(top, ref=head):
        return True, []
    if _generated_only(top, base, head):
        return True, ["Done-when proof: Forge's own settings or generated files only; no Done-when test needed."]

    proof, _ = _proof(top, item, head, base)
    mapped = _parsed(proof)
    covered = _covered(top, item, head)
    messages: list[str] = []
    names: list[str] = []
    for key in covered:
        tests = mapped.get(key, [])
        if not ran and not tests:
            if key == "Done when":
                messages.append("Done-when proof: The fix's Done-when line names no test in the Proof list.")
            else:
                messages.append(f"Done-when proof: Done-when {key} names no test in the Proof list.")
            continue
        for name in tests:
            if name == "check:":
                continue
            if not ran and not _on_branch(top, head, name):
                messages.append(f"Done-when proof: {name} is not on this branch.")
            if name.lower().endswith(".py") or ".py::" in name:
                names.append(name)
    if not ran and any("names no test" in message for message in messages):
        missing = [key for key in covered if not mapped.get(key)]
        if missing:
            wanted = "Done when" if missing == ["Done when"] else ", ".join(missing)
            messages.append(f'Done-when proof: Add a line "- {wanted}: `<test>`" to the Proof list '
                            'in a commit message.')
    if ran:
        files = _tree(top, head)
        outcomes = _results(results)
        for name in names:
            matches = _result_for(name, outcomes, files)
            failures = {outcome for outcome, _ in matches}
            if failures & {"failed", "error"}:
                messages.append(f"Done-when proof: {name} failed in this test run.")
            elif failures & {"skipped", "xfail", "xpass"}:
                messages.append(f"Done-when proof: {name} was skipped in this test run. Name the case that proves the line.")
            elif not matches and int(os.environ.get("FORGE_GROUPS", "1")) == 1:
                messages.append(f"Done-when proof: {name} did not run in this test run.")
    if messages:
        messages.append("Done-when proof: Put each test name in backticks. "
                        "Forge skips Proof lists on merge commits.")
    return not messages, messages


# The longest an old-code run may take; a test that hangs there gives the "timed out" warning.
OLD_CODE_SECONDS = float(os.environ.get("FORGE_OLD_CODE_SECONDS", 300))


def _old_code_run(top: Path, item: str, base: str, head: str, tests: list[str], gone: list[str]) -> str:
    """Run close's test command on the code before the fix, in a temporary copy. Returns the run's
    per-test results, then a `# error` line with the first error line of its output."""
    from forge import codex, fasttest, machine, review

    temp = Path(tempfile.mkdtemp(prefix="forge-before-")).resolve()
    results = repo.forge_dir(top) / f"replay-results-{item}.txt"
    results.unlink(missing_ok=True)
    entry, hung = None, False
    try:
        repo.git("worktree", "add", "-q", "--detach", str(temp), base, cwd=top)
        if tests:
            repo.git("checkout", head, "--", *tests, cwd=temp)
        if gone:
            repo.git("rm", "-q", "--", *gone, cwd=temp)
        # The copy's own command, with every CI group's files in this one run.
        command = review.close_test(temp, base).replace("{group}", "1").replace("{groups}", "1")
        hook = repo.forge_dir(top) / "pytest"
        hook.mkdir(exist_ok=True)
        (hook / "_forge_test_results.py").write_text(fasttest.RESULTS, "utf-8")
        # A picker that Forge's own command starts in the copy finds this entry and reuses it.
        entry = machine.join("test", temp, item, None, None)
        workers = machine.test_cpus(entry)
        # The copy's code first, so an editable install of the checkout cannot supply the new code.
        path = [str(temp), *([str(temp / "src")] if (temp / "src").is_dir() else []), str(hook),
                os.environ.get("PYTHONPATH", "")]
        env = {**os.environ, "FORGE_WORKER": "1", "FORGE_GROUPS": "1", "FORGE_GROUP": "1",
               "FORGE_TEST_RESULTS": str(results), "FORGE_TEST_REPO": str(temp),
               "FORGE_TEST_LANE": entry["id"], "FORGE_TEST_CPUS": workers,
               "PYTEST_XDIST_AUTO_NUM_WORKERS": workers, "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPATH": os.pathsep.join(filter(None, path)),
               "PYTEST_PLUGINS": ",".join(filter(None, [os.environ.get("PYTEST_PLUGINS"),
                                                        "_forge_test_results"]))}
        for name in ("FORGE_WORKER_TESTS", "FORGE_RETRY_FILES"):
            env.pop(name, None)
        with subprocess.Popen(command, shell=True, cwd=temp, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace", **codex.GROUP) as process:
            try:
                machine.started(entry, process.pid)
                try:
                    output = process.communicate(timeout=OLD_CODE_SECONDS)[0]
                except subprocess.TimeoutExpired:  # a hang is not a result: warn, never hold the place
                    codex._stop(codex.identity(process.pid) or {"pid": process.pid}, True)
                    output = process.communicate()[0]
                    hung = True
            except BaseException:
                codex._stop(codex.identity(process.pid) or {"pid": process.pid}, True)
                process.wait()
                raise
        error = next((line[1:].strip() for line in output.splitlines() if re.match(r"E\s", line)), "")
        return (results.read_text("utf-8") if results.is_file() else "") + ("# hung\n" if hung else "") + f"# error {error}\n"
    finally:
        if entry:
            machine.leave(entry)
        repo.run("git", "worktree", "remove", "--force", str(temp), cwd=top)
        shutil.rmtree(temp, ignore_errors=True)
        repo.run("git", "worktree", "prune", cwd=top)


def replay(top: Path, item: str, base: str) -> tuple[bool, list[str]]:
    """A fix's new or changed pytest Done-when test must fail on the code before the fix.
    Refuse a test that passes there; warn when it cannot run there. Never touches `top`."""
    if "/" in item:
        return True, []
    from forge import review

    head = repo.git("rev-parse", "HEAD", cwd=top)
    proof, _ = _proof(top, item, head, base)

    def files(*flags: str, spec: tuple[str, ...]) -> list[str]:
        return repo.git("diff", "--name-only", "--no-renames", *flags, base, head, "--", *spec,
                        cwd=top).splitlines()

    fixtures = (":(glob)**/conftest.py",)  # shared test setup travels with the tests
    tests = files("--diff-filter=ACMRT", spec=tuple(repo.TEST_PATHS))
    code = files(spec=(".", *(path.replace(":(glob)", ":(exclude,glob)") for path in (*repo.TEST_PATHS, *fixtures)),
                       *review.DOC_EXCLUDES, ":(exclude)forge.toml"))
    # Ignore rules and generated files change no runtime code, as in a fix's size count.
    code = [path for path in code if Path(path).name not in (".gitignore", ".gitattributes")]
    generated = repo.generated_files(top, code, head)
    code = [path for path in code if path not in generated]
    names = list(dict.fromkeys(name for found in _parsed(proof).values() for name in found
                               if (name.lower().endswith(".py") or ".py::" in name)
                               and name.partition("::")[0] in tests))
    if not (names and code):
        return True, []
    command = review.close_test(top, base)
    # The old code is part of the key: a fix that merges main keeps its files but not its base.
    record = review.passed_record(top, f"replay {repo.git('rev-parse', base, cwd=top)} {command}", base=base)
    saved = record.with_name(record.name + ".old-code") if record else None
    if saved and saved.is_file():
        report = saved.read_text("utf-8")
    else:
        gone = files("--diff-filter=D", spec=(*repo.TEST_PATHS, *fixtures))
        report = _old_code_run(top, item, base, head,
                               [*tests, *files("--diff-filter=ACMRT", spec=fixtures)], gone)
        if saved:
            saved.parent.mkdir(exist_ok=True)
            saved.write_text(report, "utf-8")
    outcomes, slow = _results(report), set(re.findall(r"^# timeout (.+)$", report, re.M))
    error = (re.findall(r"^# error (.*)$", report, re.M) or [""])[-1]
    tree = _tree(top, head)
    hung = "# hung\n" in report
    messages: list[str] = []
    refused = False
    for name in names:
        matches = _result_for(name, outcomes, tree)
        seen = {outcome for outcome, _ in matches}
        timed_out = any(node in slow for _, node in matches)
        if hung and seen != {"failed"} or not matches or seen - {"passed", "failed"} or timed_out:
            broken = any(result == "error" and node.partition("::")[0] == name.partition("::")[0]
                         for node, result in outcomes.items())
            why = "it timed out" if timed_out or hung else error if broken and error else "it did not run"
            messages.append(f"Done-when proof: {name} could not run on the code before the fix ({why}). "
                            "The review judges it.")
        elif seen == {"failed"}:
            continue
        else:
            refused = True
            messages.append(
                f"Done-when proof: {name} passed on the code before the fix, so it does not prove the fix. "
                "Make it fail there for the reported problem." if seen == {"passed"} else
                f"Done-when proof: {name} has passing and failing cases on the code before the fix. "
                "Name the case that proves the fix.")
    return not refused, messages


def proof_list(top: Path, base: str, report: str | None = None) -> str:
    """Write each proof entry with the results of the latest close-test attempt."""
    from forge import fasttest, review

    branch = repo.current_branch(top)
    current = review.branch_item(branch, top) if branch else None
    item = current[0] if current else ""
    proof = review.commit_paragraph(top, base, "Proof list:")
    has_tests = any(name != "check:" for names in _parsed(proof).values() for name in names)
    command = review.close_test(top, base) if has_tests else ""
    passed = review.passed_record(top, command, base=base) if command else None
    results = review.results_path(top) if has_tests else None
    if passed and passed.is_file():
        report = passed.read_text("utf-8")
    elif report is not None and results:
        report = results.read_text("utf-8") if results.is_file() else ""
    files = _tree(top, "HEAD") if item and has_tests else set()
    outcomes = _results(report or "")
    skipped_docs = bool(_parsed(proof)) and review.docs_only(top, base)
    ran_none = bool(_parsed(proof)) and (not command or skipped_docs)
    cfg = repo.config(top)
    ci_skipped = skipped_docs and repo.test_place(cfg) == "ci" and "tests" in cfg["checks"]

    def render(line: str) -> str:
        parsed = _line(line)
        if not parsed:
            return line if not line.strip() or line.startswith("Proof list") else line + " (not checked)"
        _, rest, found = parsed
        if not found or found[0] == "check:":
            return line if not line.strip() or line.lstrip().startswith("Proof list:") else line + " (not checked)"
        name, start, end = found
        path = re.split(r"::| > ", name, maxsplit=1)[0]
        source = _blob(top, "HEAD", path)
        selector = name.partition("::")[2]
        case = (re.sub(r"\[.*", "", selector.rsplit("::", 1)[-1])
                if path.endswith(".py") and selector else "" if path.endswith(".py") else
                name.rsplit(" > ", 1)[-1] if " > " in name else
                name.rsplit("::", 1)[-1] if "::" in name else "")
        matches = _result_for(name, outcomes, files) if outcomes else []
        if path not in files or case and (not re.search(rf"\b{re.escape(case)}\b", source)
                                   if path.endswith(".py") else case not in source):
            said = "not run"
        elif not path.endswith(".py"):
            said = f"{name} (not checked)"
        elif ci_skipped:
            said = f"{name} (not run in CI; only the name on the branch was checked)"
        elif ran_none and fasttest.RESULTS_HEADER not in (report or ""):
            said = "not run (close ran no tests for this change)"
        elif report is None:
            said = f"{name} (in the branch; close's test run gives its result)"
        elif fasttest.RESULTS_HEADER not in report:
            said = f"{name} (not checked)"
        elif len(matches) == 1 and matches[0][1].rsplit("::", 1)[-1] == name.rsplit("::", 1)[-1]:
            said = f"{name} ({matches[0][0]} in close's run)"
        elif matches:
            counts = collections.Counter(outcome for outcome, _ in matches)
            said = f"{name} ({', '.join(f'{counts[word]} {word}' for word in RESULT_WORDS if counts[word])} in close's run)"
        else:
            said = "not run"
        rendered = rest[:start] + said + rest[end:]
        return line[:line.find(rest)] + rendered

    rendered = "\n".join(render(line) for line in proof.splitlines())
    return f"{CI_DOCS_ONLY}\n{rendered}" if ci_skipped else rendered


def uncommitted(top: Path) -> list[str]:
    """Each modified or staged tracked file and each untracked file that .gitignore does not cover."""
    entries = iter(repo.run("git", "status", "--porcelain", "-z", "--untracked-files=all",
                            cwd=top).stdout.split("\0"))
    found = []
    for entry in entries:
        if entry:
            found.append(entry[3:])
            if entry[0] in "RC":
                next(entries, None)  # a rename or copy lists its old path next
    return found
