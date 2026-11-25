"""Adapt the pinned Autoreview process for checkout paths, Windows and sign-off parts."""
from __future__ import annotations

import contextlib
import json
import os
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def snapshot(top: Path, *, isolated: bool = False) -> str:
    """Hash the worktree without changing its index or saving unfiltered blobs."""
    from forge import repo
    index = Path(repo.git("rev-parse", "--path-format=absolute", "--git-path", "index", cwd=top))
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp) / "index"
        if index.is_file():
            shutil.copyfile(index, temp)
        env = {**os.environ, "GIT_INDEX_FILE": str(temp)}
        if isolated:
            objects = repo.git("rev-parse", "--path-format=absolute", "--git-path", "objects", cwd=top)
            (temp.parent / "objects").mkdir()
            env["GIT_OBJECT_DIRECTORY"] = str(temp.parent / "objects")
            env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = os.pathsep.join(filter(None, (
                json.dumps(objects, ensure_ascii=False), env.get("GIT_ALTERNATE_OBJECT_DIRECTORIES"))))
        for args in (["add", "-A"], ["write-tree"]):
            done = subprocess.run(["git", *args], cwd=top, env=env, capture_output=True, text=True, check=True)
    return done.stdout + repo.run("git", "rev-parse", "-q", "--verify", "HEAD", cwd=top).stdout

# Ported from the old tree's review launcher: the helper starts the reviewer in an empty folder,
# where it can't open the code a finding depends on. Each launcher starts the real one in the
# reviewed checkout instead. The `codex` one swaps that one folder; the read-only sandbox the
# helper asks for stays as it is. The helper gives Claude only web search and refuses Read as a
# tool option, so the `claude` one adds the read-only file tools; --restricted keeps them inside
# the checkout and leaves out every tool that runs commands.
LAUNCHER = '''\
import os, subprocess, sys, time
from pathlib import Path
argv = sys.argv[1:]
if {engine!r} == "codex":
    for i in range(len(argv) - 1):
        if argv[i] in ("-C", "--cd"):
            argv[i + 1] = {tree!r}
    if "exec" in argv:
        i = argv.index("exec")
        argv[i:i] = {quiet!r}
elif "--tools" in argv:
    i = argv.index("--tools") + 1
    argv[i] = ",".join(filter(None, ["Read", "Grep", "Glob", argv[i]]))
    argv.append("--restricted")
# Each engine needs its own stream so parallel calls cannot mix chat and token use.
log = Path({spent!r}) / (str(time.time_ns()) + "-" + str(os.getpid()) + ".jsonl")
with log.open("ab") as spent, subprocess.Popen(
        [*{real!r}, *argv], cwd={tree!r}, stdout=subprocess.PIPE) as engine:
    for line in engine.stdout:
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
        if any(kind in line for kind in (b"thread.started", b"turn.completed", b"session_id")):
            spent.write(line)
sys.exit(engine.returncode)
'''


def main() -> None:
    from forge import codex
    # Close must attach the real interpreter to its Windows job before the
    # helper can launch engines. A venv launcher may sit between the two.
    print(os.getpid(), flush=True)
    if sys.stdin.buffer.read(1) != b"1":
        return
    tree, launcher, mode, helper, *args = sys.argv[1:]
    roots = (Path(tree), Path(tree).resolve())
    class EngineProcess(subprocess.Popen):
        def __init__(self, command, *positional, **kwargs):
            if isinstance(command, (list, tuple)) and command and command[0] == launcher:
                command = [sys.executable, *command]
            if os.name != "nt":
                # Autoreview normally detaches engines. Close owns one group
                # for the helper, its engines and the engines' children.
                kwargs.pop("start_new_session", None)
            super().__init__(command, *positional, **kwargs)

    subprocess.Popen = EngineProcess
    sys.argv = [helper, *args]
    sys.path[0] = str(Path(helper).resolve().parent)
    namespace = runpy.run_path(helper, run_name="forge_autoreview")
    entry = namespace.get("sanitized_main")
    if entry is None:  # Executable helpers can also finish at module scope.
        return
    implementation = entry.__globals__
    validate = implementation["validate_report"]
    if os.name != "nt":
        def terminate_engine(proc: subprocess.Popen[Any], *args: Any, **kwargs: Any) -> None:
            # Engines share close's group, so a per-engine timeout must stop
            # that engine's tree rather than target a nonexistent child group.
            codex._stop(codex.identity(proc.pid) or {"pid": proc.pid}, False)
            proc.wait()
        implementation["terminate_process_group"] = terminate_engine

    def validate_paths(report: Any, repo: Path, *args: Any) -> None:
        # Translate our disposable checkout paths before the helper rejects absolute paths.
        if isinstance(report, dict) and isinstance(report.get("findings"), list):
            for finding in report["findings"]:
                location = finding.get("code_location") if isinstance(finding, dict) else None
                file = location.get("file_path") if isinstance(location, dict) else None
                if isinstance(file, str):
                    for root in roots:
                        prefix = root.as_posix().rstrip("/") + "/"
                        if file.replace("\\", "/").startswith(prefix):
                            location["file_path"] = file.replace("\\", "/")[len(prefix):]
                            break
        validate(report, repo, *args)

    implementation["validate_report"] = validate_paths
    if mode == "serial":
        raise SystemExit(entry())

    def parallel_parts(args: Any, reviewers: list[Any], repo: Path, prompts: list[Any],
                       changed_paths: Any, evidence: Any = None) -> list[tuple[str, Any]]:
        # The pinned helper still owns validation, report merging and process cleanup.
        args.review_usage = reviewers[0].review_usage = []
        with ThreadPoolExecutor(max_workers=len(prompts)) as pool:
            futures = []
            for index, prompt in enumerate(prompts, 1):
                if len(prompts) > 1:
                    text = getattr(prompt, "prompt", prompt)
                    print(f"review pass: {index}/{len(prompts)} "
                          f"({len(text.encode('utf-8'))} prompt bytes)", flush=True)
                futures.append(pool.submit(implementation["run_reviewer"], reviewers[0],
                                           repo, prompt, changed_paths, [], evidence))
            return [(f"chunk {index}/{len(prompts)}", result.result())
                    for index, result in enumerate(futures, 1)]

    implementation["run_review_passes"] = parallel_parts
    raise SystemExit(entry())


@contextlib.contextmanager
def owned(argv: list[str], cwd: Path) -> Iterator[subprocess.Popen[bytes]]:
    """Close owns the review group or job, including across exceptions and signals."""
    from forge import codex
    process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env={**os.environ, "FORGE_WORKER": "1"},
                               **codex.GROUP)
    recorded = codex.identity(process.pid) or {"pid": process.pid}
    job, watcher, monitor = None, None, None
    ended = False
    lock = threading.Lock()

    def end() -> None:
        nonlocal ended
        with lock:
            if not ended:
                if job is not None:
                    import ctypes
                    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(job))
                else:
                    codex._stop(recorded, True)
                ended = True

    def collected() -> None:
        process.wait()
        end()  # A surviving engine can still hold the output pipe open.

    def interrupted(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    previous = {}
    try:
        previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT)}
        helper = int(process.stdout.readline())
        if os.name == "nt":
            # This handle belongs to close. Even TerminateProcess closes it,
            # ending the helper and descendants in the job.
            job = windows_job(helper)
        else:
            # Only close holds the write end. A hard kill closes it too. The
            # watcher is outside the review group used by forge stop.
            watcher = subprocess.Popen([sys.executable, __file__, "--watch", json.dumps(recorded)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **codex.GROUP)
        process.stdin.write(b"1")
        process.stdin.close()
        monitor = threading.Thread(target=collected, daemon=True)
        monitor.start()
        yield process
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        end()
        process.wait()
        if monitor is not None:
            monitor.join()
        if watcher is not None:
            watcher.stdin.close()
            watcher.wait()
        process.stdout.close()
        process.stdin.close()


def windows_job(pid: int) -> Any:
    """The watcher owns a kill-on-close job before the helper can spawn children."""
    import ctypes
    from ctypes import wintypes as w
    class Limits(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", w.DWORD), ("minimum", ctypes.c_size_t),
                    ("maximum", ctypes.c_size_t), ("active", w.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Limits), ("io", ctypes.c_uint64 * 6),
                    ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                    ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    process = kernel.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
    limits = Extended()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    try:
        if not (job and process and kernel.SetInformationJobObject(
                job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
                and kernel.AssignProcessToJobObject(job, process)):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        if job:
            kernel.CloseHandle(job)
        raise
    finally:
        if process:
            kernel.CloseHandle(process)
    return job


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    if sys.argv[1:2] == ["sensitive"]:
        helper = Path(sys.argv[2])
        sys.path[0] = str(helper.parent)
        namespace = runpy.run_path(str(helper), run_name="forge_autoreview")
        print(json.dumps(sorted(namespace["tracked_sensitive_paths"](json.load(sys.stdin)))))
    elif sys.argv[1:2] == ["--watch"]:
        from forge import codex
        recorded = json.loads(sys.argv[2])
        sys.stdin.buffer.read()
        codex._stop(recorded, True)
    else:
        main()
