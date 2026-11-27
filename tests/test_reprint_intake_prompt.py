"""A lost intake prompt prints again, with its full handback command, while its intake is pending."""
import json
import re
from pathlib import Path

from test_start_sorts_ideas import (  # noqa: F401
    intake, land, env, _signed_off, _offer, _fix,
)

STORY = "FIX-REPRINT-INTAKE-PROMPT"
IDEA = "Correct the welcome page $(touch pwned)"


def test_1_start_and_next_print_the_saved_offer_and_its_handback_command_runs(intake, monkeypatch):
    repo, top, owner, *_ = intake
    _signed_off(intake)
    first = _offer(intake, IDEA)
    again = owner.forge("start", IDEA, cwd=top)
    assert again.returncode == 0, again.stdout + again.stderr
    assert json.loads(again.stdout) == first  # same prompt, models, checkout and command
    nxt = owner.forge("next", cwd=top)
    assert first["prompt"] in nxt.stdout and first["instruction"] in nxt.stdout
    assert "touch pwned" not in re.sub(re.escape(first["prompt"]), "", nxt.stdout)  # no idea in a command
    # A plain terminal has no coordinator: next still reports and shows the prompt.
    monkeypatch.delenv("CLAUDECODE")
    plain = repo.forge("next", cwd=top)
    assert plain.returncode == 0 and first["prompt"] in plain.stdout, plain.stdout + plain.stderr
    monkeypatch.setenv("CLAUDECODE", "1")
    # An intake saved before offers were kept is rebuilt the old way.
    git_dir = Path(repo.git("rev-parse", "--git-common-dir", cwd=top))
    git_dir = git_dir if git_dir.is_absolute() else top / git_dir
    record = next((git_dir / "forge/threads/read").glob("intake-*.json"))
    saved = json.loads(record.read_text("utf-8"))
    del saved["pending"]["offer"]
    record.write_text(json.dumps(saved), "utf-8")
    old = owner.forge("start", IDEA, cwd=top)
    assert json.loads(old.stdout)["prompt"] == first["prompt"], old.stdout + old.stderr
    assert first["instruction"] in owner.forge("next", cwd=top).stdout
    command = re.search(r"forge (handback \S+ --round \d+ --subagent <id> --text <message>)", first["instruction"])
    assert command, first["instruction"]
    args = command[1].replace("<id>", "idea-explorer").replace("<message>", _fix()).split(" ")
    done = owner.forge(*args[:5], "idea-explorer", "--text", _fix(), cwd=top)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Forge chose a fix" in done.stdout
