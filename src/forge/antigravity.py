"""Antigravity's newline-delimited Agent Client Protocol."""
from __future__ import annotations

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
from typing import Any

from forge import __version__, codex, deny, machine, repo

MINIMUM = (1, 5, 12)
PROGRAM = os.environ.get("AGY_BIN") or "agy"
INSTALL = "install Antigravity CLI 1.5.12 or newer (https://antigravity.google/docs/getting-started), then run agy and sign in"
OLD = "Antigravity {version} is installed, and Forge needs 1.5.12 or newer."


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


def problem() -> str:
    try:
        result = subprocess.run([PROGRAM, "--version"], capture_output=True,
                                text=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return "Forge cannot run the Antigravity CLI (agy)."
    version = result.stdout.strip()
    return OLD.format(version=version) if _version(version) < MINIMUM else ""


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
         effort: str, again: str, ran: dict, resume: str | None = None, group: bool = True) -> dict:
    log = repo.work_log(top, item)
    questions, chunks = [], []
    kind = ran.pop("model_kind", "build")
    unfinished = ("Antigravity ended its turn without finishing ({detail}); see {log}.", "{again}")
    try:
        cwd = cwd.resolve()
        folder = profile(top, mode, cwd)
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
        ) as process, machine.agent_process(process, log):
            assert process.stdin is not None and process.stdout is not None
            serial = 0

            def send(message: dict) -> None:
                process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
                process.stdin.flush()

            def call(method: str, params: dict) -> dict:
                nonlocal serial
                serial += 1
                send({"id": serial, "method": method, "params": params})
                for line in process.stdout:
                    message = json.loads(line)
                    name = message.get("method")
                    data = message.get("params", {})
                    if name and "id" in message:
                        answer: dict[str, Any]
                        if name == "session/request_permission":
                            answer = {"result": {"outcome": _permission(data, cwd.resolve(), mode, questions)}}
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
                            if action in ("execute", "edit", "read"):
                                step = repo.worker_step("Edit" if action == "edit" else action,
                                    {"command": raw.get("CommandLine"), "path": raw.get("Path") or
                                     next(iter(update.get("locations", [])), {}).get("path")})
                                repo.record_progress(top, item, ran["run_id"], step=step)
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
                            repo.refuse(("Antigravity is not signed in.", f"{step}, then {{again}}"), again=again)
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
            if effort in offered("thought_level"):
                select("thought_level", effort)
            else:
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
            if stop != "end_turn":
                repo.refuse(unfinished, detail=stop or "no answer", log=log, again=again)
            process.stdin.close()
            return {"session": chat, "text": "".join(chunks + questions), "stop": stop,
                    "model": current, "tokens": tokens}
    except (OSError, ValueError, KeyError, TypeError) as error:
        repo.refuse(unfinished, detail=str(error), log=log, again=again)
