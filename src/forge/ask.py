"""forge ask: one read-only Codex turn on the builders' app-server path, for a quick question."""
import contextlib
import json
import os
import uuid
from typing import Any

from forge import codex, machine, repo

COMMANDS = [{"words": "ask", "run": "ask", "changes_state": False,
    "help": "Ask Codex a question in a read-only turn", "position": 25,
    "args": [(("question",), {}), (("--model",), {"metavar": "MODEL"})],
    "listing": "| `forge ask \"<question>\" [--model <model>]` | Asks Codex one question in a read-only turn that waits for an agent place and prints the answer; the model comes from `--model` or `[models.ask]` in `forge.toml` |"}]


def ask(args: Any) -> int:
    top = repo.root()
    chosen = repo.models(repo.config(top), "ask", "codex")
    model = args.model or chosen.get("model")
    if codex.sdk_problem(reuse=True):  # a Claude-only repo never installed it
        codex.install()
    item = f"ask-{uuid.uuid4().hex[:8]}"  # each ask is its own run: its log and record meet no other's
    # A worker or reader already holds a place for its whole round, so its question needs no second one.
    place = (contextlib.nullcontext() if os.environ.get("FORGE_WORKER") == "1"
             else machine.agent_slot(top, "ask", None, model, chosen.get("effort")))
    with place:
        ran = codex.run(top, item, "Ask", "Ask", args.question, "read-only", model=args.model, echo=False)
    if ran["status"] != "completed":
        ended = [line for line in repo.work_log(top, item).read_text("utf-8", errors="replace").splitlines()
                 if line.startswith("Codex ended the turn")]
        raise repo.Refused(ended[-1] if ended else "Codex reported no end to the turn.",
                           f"forge ask {json.dumps(args.question)}")
    print((ran["text"] or "").strip())
    return 0
