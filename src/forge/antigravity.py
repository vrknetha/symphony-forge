"""Antigravity's newline-delimited Agent Client Protocol."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Timer
from typing import Any, Callable

from forge import __version__, codex, deny, machine, repo

MINIMUM = (1, 5, 12)
PROGRAM = os.environ.get("AGY_BIN") or "agy"
INSTALL = "install Antigravity CLI 1.5.12 or newer (https://antigravity.google/docs/getting-started), then run agy and sign in"
OLD = "Antigravity {version} is installed, and Forge needs 1.5.12 or newer."
SIGNED_OUT = "Antigravity is not signed in."
# Keep evidence preparation on the pinned review helper's Git settings.
SAFE_GIT_CONFIG_ARGS = (
    "core.fsmonitor=false", "core.pager=cat", "diff.external=", "diff.renames=false",
    "pager.diff=cat", "pager.log=cat", "pager.show=cat", "diff.suppressBlankEmpty=false",
)


class NoSession(Exception):
    """The server no longer has the requested conversation."""


def _key(path: Path) -> str:
    return hashlib.sha256(os.fsencode(path.resolve())).hexdigest()[:12]


def home(top: Path) -> Path:
    common = repo.forge_dir(top).parent
    main = common.parent if common.name == ".git" else top
    default = Path.home() / ".local/share"
    for data in (Path(os.environ.get("XDG_DATA_HOME") or default), default):
        folder = (data / "forge" / "antigravity" / _key(main)).resolve()
        if not any((parent / ".git").exists() for parent in (folder, *folder.parents)):
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt":
                folder.chmod(0o700)  # Also protect copies made by earlier releases.
            return folder
    raise ValueError("Forge needs an Antigravity data folder outside Git checkouts")


def profile(top: Path, mode: str, checkout: Path | None = None) -> Path:
    checkout = (checkout or top).resolve()
    root = home(top)
    folder = root / ("full" if mode == "full" else "read-profile")
    if mode == "full":
        folder /= _key(checkout)

    def write(name: str, value: dict) -> None:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    guard = root / f"deny-{__version__}.py"
    if not guard.exists():
        root.mkdir(parents=True, exist_ok=True)
        # Publish once so another work round cannot replace the guard from its checkout.
        with TemporaryDirectory(dir=root) as temp:
            snapshot = Path(temp) / guard.name
            shutil.copyfile(deny.__file__, snapshot)
            try:
                os.link(snapshot, guard)
            except FileExistsError:
                pass
    python = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    words = [str(python), "-I", "-S", str(guard)]
    command = subprocess.list2cmdline(words) if os.name == "nt" else shlex.join(words)
    write("config/hooks.json", {"forge": {"PreToolUse": [{
        "matcher": tool, "hooks": [{"type": "command", "command": command, "timeout": 60}],
    } for tool in ("run_command", "manage_task")]}})
    settings = {}
    source_settings = Path.home() / ".gemini/antigravity-cli/settings.json"
    if source_settings.is_file():
        personal = json.loads(source_settings.read_text(encoding="utf-8-sig"))
        settings = {key: personal[key] for key in ("auth", "gcp", "modelProvider") if key in personal}
    if mode == "full":
        write("config/skills.json", {"entries": [{"path": str(checkout / ".codex/skills")}]})
    else:
        settings.update(toolPermission="strict", permissions={
            "deny": ["write_file(*)", "command(*)", "execute_url(*)", "read_url(*)", "mcp(*)"],
            "ask": ["read_file(*)"],
        })
    write("antigravity-cli/settings.json", settings)
    return folder


def _version(text: str) -> tuple[int, ...]:
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", text)
    return tuple(map(int, match.groups())) if match else ()


def version() -> str:
    try:
        result = subprocess.run([PROGRAM, "--version"], capture_output=True,
                                text=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def problem(installed: str | None = None) -> str:
    installed = version() if installed is None else installed
    if not installed:
        return "Forge cannot run the Antigravity CLI (agy)."
    return OLD.format(version=installed) if _version(installed) < MINIMUM else ""


@contextmanager
def clean_git(tmp: Path, *, checkout: Path | None = None):
    """Keep personal Git configuration from running code while preparing evidence."""
    config, hooks = tmp / "gitconfig", tmp / "hooks"
    config.touch()
    hooks.mkdir()
    overrides = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(config)}
    for field in ("name", "email"):
        value = repo.run("git", "config", "--get", f"user.{field}", cwd=checkout).stdout.strip()
        if value:
            for role in ("AUTHOR", "COMMITTER"):
                key = f"GIT_{role}_{field.upper()}"
                overrides[key] = os.environ.get(key) or value
    options = [*SAFE_GIT_CONFIG_ARGS, f"core.hooksPath={hooks}"]
    if checkout is not None:
        # Keep declarative ignore and attribute rules, and disable executable filters.
        for key in ("core.excludesFile", "core.attributesFile"):
            setting = repo.run("git", "config", "--null", "--path", "--get", key, cwd=checkout)
            if setting.returncode == 0:
                options.append(f"{key}=" + setting.stdout.removesuffix("\0"))
        filters = repo.run("git", "config", "--null", "--name-only", "--get-regexp",
                           r"^filter\..*\.(clean|smudge|process|required)$", cwd=checkout)
        if filters.returncode not in (0, 1):
            filters.check_returncode()
        for key in filter(None, filters.stdout.split("\0")):
            options.append(f"{key}=" + ("false" if key.endswith(".required") else ""))
        options.append("commit.gpgSign=false")
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    for index, option in enumerate(options, count):
        key, value = option.split("=", 1)
        overrides.update({f"GIT_CONFIG_KEY_{index}": key, f"GIT_CONFIG_VALUE_{index}": value})
    overrides["GIT_CONFIG_COUNT"] = str(count + len(options))
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield hooks
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def copy_for_reading(source: Path, dest: Path, paths: list[str], drop: set[str]) -> None:
    source = source.resolve()
    drop = {os.path.normcase(name) for name in drop}
    listed = {os.path.normcase(name) for name in paths}

    def allowed(path: Path) -> bool:
        name = os.path.normcase(path.as_posix())
        return (name in listed and name not in drop
                and not {part.lower() for part in path.parts} &
                {".git", ".agents", ".agent", "_agents", "_agent", ".gemini"}
                and path.name.lower() not in {"agents.md", "gemini.md", "claude.md"})

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(mode=0o700, parents=True)
    for name in paths:
        path = Path(name)
        if path.anchor or ".." in path.parts or not allowed(path):
            continue
        try:
            resolved = (source / path).resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not resolved.is_relative_to(source) or not allowed(resolved.relative_to(source)) or not resolved.is_file():
            continue
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved, target, follow_symlinks=False)


def review_design_context(top: Path, cfg: dict, changes: str, user_facing: bool) -> tuple[str, str]:
    """Point reviewers to design files only after the review copy has been filtered."""
    from forge import roles, story, sync

    owned = ""
    if named := re.search(r"^Design: (docs/design/[^/\s]+/) \(", changes, re.M):
        owned = named[1]
    elif not changes and repo.is_prototype(top, cfg, ("HEAD", story.landed_ref(top))):
        owned = "docs/design/prototype/"
    parts = ["## Design context",
             "Read `PRODUCT.md` and `DESIGN.md` in the review copy if present."]
    if owned:
        parts.append(f"Approved design: read the screens and images in `{owned}` in the review copy.")
    elif re.search(r"^Design: none \(", changes, re.M):
        parts.append("Use `docs/design/prototype/` for context if present. Its components add no requirement.")
    if user_facing:
        parts.append("### Frontend\n\nUse impeccable for layout and copy and emil-design-eng for motion "
                     "and interactions. " + roles.ROLES["frontend"][2].removeprefix(roles.BUILD).strip())
    audit = sync._synced_text(".codex/skills/test-audit/SKILL.md", "skills/test-audit/SKILL.md")
    parts.append("### test-audit\n\n" + audit.split("## Authoring gate\n", 1)[1].split("## Junk patterns", 1)[0].strip())
    return "\n\n".join(parts), owned


def review_engine(top: Path, item: str, checkout: Path, copy: Path, prompt: str,
                  sensitive: Callable[[list[str]], set[str]], model: str, effort: str,
                  spent: Path) -> str:
    paths = list(filter(None, repo.git("ls-files", "-z", cwd=checkout).split("\0")))
    copy_for_reading(checkout, copy, paths, sensitive(paths))
    ran = {"model_kind": "review"}
    try:
        result = turn(top, item, prompt, cwd=copy, mode="read", model=model, effort=effort,
                      again=f"forge close {item}", ran=ran, group=False)
    except repo.Refused as error:
        problem, _, next_step = str(error).partition("\n")
        if next_step:
            print(next_step, file=sys.stderr, flush=True)
        raise SystemExit(problem) from None
    print(f"model: {ran['model']}", flush=True)
    if ran["effort"]:
        print(f"thinking: {ran['effort']}", flush=True)
    tokens = result["tokens"]
    if tokens["input_tokens"] is not None:
        cached = tokens["cached_input_tokens"] or 0
        spent.mkdir(exist_ok=True)
        (spent / f"{copy.name}.jsonl").write_text(json.dumps({
            "type": "result", "session_id": result["session"],
            "usage": {"input_tokens": tokens["input_tokens"] - cached,
                      "cache_read_input_tokens": cached, "output_tokens": tokens["output_tokens"]},
        }) + "\n", encoding="utf-8")
    return result["text"]


def require_unfiltered(top: Path, paths: list[str]) -> None:
    """Do not publish a file whose filter might change what Git is allowed to store."""
    names = [name for name in paths if not (top / name).is_dir()]
    folders = [name for name in paths if (top / name).is_dir()]
    if folders:
        listing = repo.run("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                           "--", *folders, cwd=top)
        listing.check_returncode()
        names.extend(name for name in listing.stdout.split("\0") if name)
    if not names:
        return
    attrs = repo.run("git", "check-attr", "-z", "filter", "--", *names, cwd=top)
    attrs.check_returncode()
    fields = attrs.stdout.split("\0")
    for name, value in zip(fields[::3], fields[2::3]):
        if value not in ("unspecified", "unset", "set"):
            repo.refuse(("Forge cannot safely record an Antigravity read with a Git filter on {path}.",
                         "use a plan and read records that Git can store as written"), path=name)


def read(top: Path, target: str, models: dict, prompt: str, fresh: str) -> subprocess.CompletedProcess[str]:
    """Run inside the cold read's clean Git context."""
    from forge import review, story
    helper = Path(__file__).with_name("review_process.py")
    pinned = review.helper().resolve()
    listed = repo.run("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", cwd=top)
    listed.check_returncode()
    paths = sorted(set(listed.stdout.split("\0")) - {""})
    sensitive = subprocess.run([sys.executable, str(helper), "sensitive", str(pinned)],
                               input=json.dumps(paths), encoding="utf-8",
                               capture_output=True, check=True)
    cwd = home(top) / "read" / target
    copy_for_reading(top, cwd, paths, set(json.loads(sensitive.stdout)))
    rules = story.agents_section(top, "Review rules")
    suffix = "\n\nThis repo's Review rules, from its AGENTS.md on the default branch:\n" + rules
    path = codex._item_file(top, target, ".json", "Grill")
    saved = codex.record(top, target, "Grill").get("antigravity") or {}
    resume = saved.get("id")
    with repo.record_run(top, target, "read", family="antigravity", **models) as ran:
        ran["model_kind"] = "grill"
        kwargs = dict(cwd=cwd, mode="read", model=models["model"], effort=models["effort"],
                      again=f"forge read {target}", ran=ran)
        try:
            result = turn(top, target, (prompt if resume else fresh) + suffix, resume=resume, **kwargs)
        except NoSession:
            result = turn(top, target, fresh + suffix, **kwargs)
        finally:
            if ran.get("chat"):
                codex._record(path, antigravity={"id": ran["chat"]})
        ran["outcome"] = "completed"
    said = result["text"].replace(str(cwd), str(top)).replace(cwd.as_posix(), top.as_posix())
    return subprocess.CompletedProcess([PROGRAM], 0, said, "")


def signed_in(top: Path, *, mode: str = "read",
              again: str = "forge doctor") -> tuple[bool | None, str]:
    try:
        with TemporaryDirectory() as temp:
            turn(top, "doctor", "", cwd=Path(temp), mode=mode, model="default", effort="",
                 again=again, ran={}, probe=True)
    except (OSError, NoSession, repo.Refused) as error:
        if isinstance(error, repo.Refused) and error.entry and error.entry[0] == SIGNED_OUT:
            return False, str(error).partition("\nNext: ")[2]
        return None, str(error).partition("\n")[0].rstrip(".") or "Antigravity gave no reason"
    return True, ""


def ready(cfg: dict, kind: str, design: bool) -> dict:
    if message := problem():
        repo.refuse((message, INSTALL))
    return (repo.design_models(cfg, "antigravity") if design
            else repo.worker_models(cfg, kind.lower(), "antigravity"))


def _permission(params: dict, cwd: Path, mode: str, questions: list[str]) -> dict:
    tool = params["toolCall"]
    options = params["options"]
    if tool.get("toolCallId", "").startswith("interaction_"):
        names = ", ".join(option["name"] for option in options)
        questions.append(f"\n\nQuestion: {tool['title']} (options: {names})")
        return {"outcome": "cancelled"}
    kind = tool.get("kind")
    allow = mode == "full" or kind == "think"
    if mode == "read" and kind in ("read", "search"):
        locations = [location.get("path") for location in tool.get("locations", [])]
        extra = [value for key, value in (tool.get("rawInput") or {}).items()
                 if "path" in key.lower()]
        try:
            allow = bool(locations) and all(isinstance(path, str) and path
                and (cwd / path).resolve().is_relative_to(cwd) for path in locations + extra)
        except (OSError, RuntimeError, ValueError):
            allow = False
    kinds = (("allow_always", "allow_once") if mode == "full" else ("allow_once",)) if allow else ("reject_once",)
    for option_kind in kinds:
        for option in options:
            if option["kind"] == option_kind:
                return {"outcome": "selected", "optionId": option["optionId"]}
    return {"outcome": "cancelled"}


def turn(top: Path, item: str, prompt: str, *, cwd: Path, mode: str, model: str,
         effort: str, again: str, ran: dict, resume: str | None = None, group: bool = True,
         probe: bool = False) -> dict:
    log = cwd / "agy.log" if probe else repo.work_log(top, item)
    questions, chunks = [], []
    kind = ran.pop("model_kind", "build")
    refused_tool = ""
    unfinished = (("{detail}", "") if probe else
                  ("Antigravity ended its turn without finishing ({detail}); see {log}.", "{again}"))
    try:
        cwd = cwd.resolve()
        folder = profile(top, mode, top if probe else cwd)
        program = shutil.which(PROGRAM)
        if not program:
            raise FileNotFoundError(PROGRAM)
        command = [str(Path(program).absolute()), "acp", "--gemini-dir", str(folder)]
        if mode == "full":
            command.append("--dangerously-skip-permissions")
        with log.open("a", encoding="utf-8") as out, subprocess.Popen(
            command, cwd=cwd, env=machine.worker_env(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=out, text=True, encoding="utf-8",
            **(codex.GROUP if group else {}),
        ) as process, machine.agent_process(process, log), _probe_deadline(process, probe):
            assert process.stdin is not None and process.stdout is not None
            serial = 0

            def send(message: dict) -> None:
                process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
                process.stdin.flush()

            def call(method: str, params: dict) -> dict:
                nonlocal serial, refused_tool
                serial += 1
                send({"id": serial, "method": method, "params": params})
                for line in process.stdout:
                    message = json.loads(line)
                    name = message.get("method")
                    data = message.get("params", {})
                    if name and "id" in message:
                        answer: dict[str, Any]
                        if name == "session/request_permission":
                            outcome = _permission(data, cwd, mode, questions)
                            if kind == "review" and (outcome["outcome"] == "cancelled" or any(
                                option["kind"] == "reject_once" and option["optionId"] == outcome.get("optionId")
                                for option in data["options"]
                            )):
                                tool = data["toolCall"]
                                refused_tool = " ".join((tool.get("title") or tool.get("kind") or "unknown tool").split())
                            answer = {"result": {"outcome": outcome}}
                        else:
                            answer = {"error": {"code": -32601, "message": "Method not found"}}
                        send({"id": message["id"], **answer})
                    elif name == "session/update":
                        update = data.get("update", {})
                        if update.get("sessionUpdate") == "agent_message_chunk":
                            chunks.append(update.get("content", {}).get("text", ""))
                        if update.get("sessionUpdate") == "tool_call":
                            raw = update.get("rawInput") or {}
                            action = update.get("kind")
                            if not probe and (run_id := ran.get("run_id")) and action in ("execute", "edit", "read"):
                                step = repo.worker_step("Edit" if action == "edit" else action,
                                    {"command": raw.get("CommandLine"), "path": raw.get("Path") or
                                     next(iter(update.get("locations", [])), {}).get("path")})
                                repo.record_progress(top, item, run_id, step=step)
                    elif message.get("id") == serial:
                        if "error" not in message:
                            return message.get("result") or {}
                        error = message["error"]
                        detail = str(error.get("message", error))
                        lowered = detail.lower()
                        if "trajectory not found" in lowered or (
                            method == "session/resume" and (error.get("code") == -32002
                            or "session not found" in lowered or "unknown session" in lowered)
                        ):
                            raise NoSession()
                        if any(word in lowered for word in (
                            "sign in", "signed in", "authenticate", "authentication required", "log in",
                        )):
                            step = "run agy and sign in with Google, or with a Gemini API key or Vertex AI"
                            if os.environ.get("SSH_CONNECTION"):
                                step += f" (over ssh, sign in for Forge's profile: agy acp --gemini-dir {repo.quote(folder)} --login)"
                            repo.refuse((SIGNED_OUT, f"{step}, then {{again}}"), again=again)
                        repo.refuse(unfinished, detail=detail, log=log, again=again)
                repo.refuse(unfinished, detail="no answer", log=log, again=again)

            init = call("initialize", {"protocolVersion": 1, "clientCapabilities": {}})
            version = init.get("agentInfo", {}).get("version", "")
            if _version(version) < MINIMUM:
                repo.refuse((OLD, "run agy update, then {again}"), version=version, again=again)
            capabilities = init.get("agentCapabilities", {}).get("sessionCapabilities", {})
            if capabilities.get("resume") is None:
                repo.refuse(unfinished, detail="session resume is unavailable", log=log, again=again)
            context = {"cwd": str(cwd), "mcpServers": []}
            session = (call("session/resume", {**context, "sessionId": resume}) if resume
                       else call("session/new", context))
            if probe:
                if not session.get("sessionId"):
                    repo.refuse(unfinished, detail="Antigravity did not start a session")
                process.stdin.close()
                process.wait()
                if process.returncode:
                    repo.refuse(unfinished, detail="Antigravity did not finish the sign-in check")
                return session
            chat = resume or session["sessionId"]
            ran["chat"] = chat
            options = {option["id"]: option for option in session.get("configOptions", [])}

            def select(option_id: str, value: str) -> None:
                changed = call("session/set_config_option", {
                    "sessionId": chat, "configId": option_id, "value": value,
                })
                options.update({option["id"]: option for option in changed.get("configOptions", [])})

            def offered(option_id: str) -> list[str]:
                return [value["value"] for value in options.get(option_id, {}).get("options", [])]

            if model != "default":
                if model not in offered("model"):
                    repo.refuse(("Antigravity offers no model {model} on this account; it offers {values}.",
                                 "ask the owner, then set models.{kind}.antigravity in forge.toml, then {again}"),
                                model=model, values=", ".join(offered("model")), kind=kind, again=again)
                select("model", model)
            current = options["model"]["currentValue"]
            if effort and effort in offered("thought_level"):
                select("thought_level", effort)
            elif effort:
                print(f"Antigravity's {current} has no thinking level {effort}; it runs at its own level.")
            level = options.get("thought_level", {}).get("currentValue")
            print(f"Antigravity runs {current} at {level or 'its own level'}.", flush=True)
            ran.update(model=current, effort=level)
            result = call("session/prompt", {
                "sessionId": chat, "prompt": [{"type": "text", "text": prompt}],
            })
            usage = result.get("usage") or {}
            cached = (usage.get("cachedReadTokens") or 0) if usage else None
            tokens = dict(input_tokens=(usage["inputTokens"] + cached) if "inputTokens" in usage else None,
                          cached_input_tokens=cached, output_tokens=usage.get("outputTokens"),
                          reasoning_output_tokens=usage.get("thoughtTokens"))
            ran.update(tokens)
            stop = result.get("stopReason")
            text = "".join(chunks + questions)
            if refused_tool and (stop != "end_turn" or not "".join(chunks).strip()):
                repo.refuse(unfinished, detail=f'Forge refused the tool "{refused_tool}"', log=log, again=again)
            if stop != "end_turn":
                repo.refuse(unfinished, detail=stop or "no answer", log=log, again=again)
            process.stdin.close()
            return {"session": chat, "text": text, "stop": stop,
                    "model": current, "tokens": tokens}
    except (OSError, ValueError, KeyError, TypeError) as error:
        repo.refuse(unfinished, detail=str(error), log=log, again=again)


@contextmanager
def _probe_deadline(process: subprocess.Popen[str], probe: bool):
    if not probe:
        yield
        return
    def stop() -> None:
        if process.poll() is None:
            codex._stop(codex.identity(process.pid) or {"pid": process.pid}, True)
    timer = Timer(30, stop)
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        timer.join()
