"""forge ask: one read-only turn on Codex, Claude or Gemini, for a quick second opinion."""
import contextlib
import io
import os
import uuid
from typing import Any

from forge import antigravity, claude_sdk, codex, doctor, machine, repo, roles, routing, story

COMMANDS = [{"words": "ask", "run": "ask", "changes_state": False,
    "help": "Ask Codex, Claude or Gemini a question in a read-only turn", "position": 25,
    "args": [(("question",), {}), (("--model",), {"metavar": "MODEL"})],
    "listing": '| `forge ask "<question>" [--model <model>]` | Asks Codex, Claude or Gemini one question in a read-only turn that waits for an agent place and prints the answer; the model name picks the family, `--model` wins over `[models.ask]`, and with no model Forge asks the other family of the session |'}]


def _choose(cfg: dict[str, Any], requested: str | None) -> tuple[str, str | None, str | None]:
    ask_cfg = cfg.get("models", {}).get("ask") or {}
    if requested:
        family = roles.model_family(requested)
    elif "model" in ask_cfg:
        family = roles.model_family(ask_cfg["model"])
    else:
        family = "claude" if repo.coordinator() == "codex" else "codex"
    chosen = repo.models(cfg, "ask", family)
    return family, requested or chosen.get("model"), chosen.get("effort")


def ask(args: Any) -> int:
    top = repo.root()
    cfg = routing.routed(top, repo.config(top))
    family, model, effort = _choose(cfg, args.model)
    ag_models: dict[str, str] = {}
    if family == "codex":
        if codex.sdk_problem(reuse=True):  # a Claude-only repo never installed it
            codex.install()
    elif family == "claude":
        if claude_sdk.sdk_problem():
            claude_sdk.install()
    else:
        ag_models = dict(repo.worker_models(cfg, "ask", "antigravity"))
        if args.model:
            ag_models["model"] = args.model
        antigravity.ready(cfg, "ask", False)
        model, effort = ag_models["model"], ag_models["effort"]

    item = f"ask-{uuid.uuid4().hex[:8]}"  # each ask is its own run: its log and record meet no other's
    again = ("run forge ask again with the same question"
             + (f" and --model {repo.quote(args.model)}" if args.model else ""))
    # A worker or reader already holds a place for its whole round, so its question needs no second one.
    place = (contextlib.nullcontext() if os.environ.get("FORGE_WORKER") == "1"
             else machine.agent_slot(top, "ask", None, model, effort))
    with place:
        if family == "codex":
            ran = codex.run(top, item, "Ask", "Ask", args.question, "read-only",
                            model=model, effort=effort, echo=False)
            if ran["status"] != "completed":
                ended = [line for line in repo.work_log(top, item).read_text("utf-8", errors="replace").splitlines()
                         if line.startswith("Codex ended the turn")]
                raise repo.Refused(ended[-1] if ended else "Codex reported no end to the turn.", again)
            text = (ran["text"] or "").strip()
        elif family == "claude":
            flags = [*(["--model", model] if model else []), *(["--effort", effort] if effort else [])]
            with contextlib.redirect_stdout(io.StringIO()):
                done = story._sdk_read(top, item, flags, args.question, args.question, None, "", 1, lambda _: None)
            if done.returncode:
                raise repo.Refused(doctor._last(done), again)
            text = (done.stdout or "").strip()
        else:
            done = antigravity.read(top, item, ag_models, args.question, args.question,
                                    kind="explore", again=again)
            text = (done.stdout or "").strip()
    if family != "codex":
        log = repo.work_log(top, item)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as out:
            out.write(text + "\n")
    print(text)
    return 0
