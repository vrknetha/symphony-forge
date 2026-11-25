"""Since 24 Nov 2026, Forge's source repo uses Codex for both user-facing and plain tasks.
Both use the ordinary build model with this repo's two-tool configuration."""
from conftest import ROOT
from test_codex_worker import _codex_repo, _sent, sdk_data  # noqa: F401
from test_worker import calls, install_claude

STORY = "workers-split"


def test_1_user_facing_and_plain_source_tasks_use_codex_low(
        repo, monkeypatch, sdk_data):
    folder, codex_log = _codex_repo(repo, monkeypatch, sdk_data)
    text = (ROOT / "forge.toml").read_text("utf-8")
    (folder / "forge.toml").write_text(text, encoding="utf-8")
    repo.git("commit", "-qam", "Use this repo's settings", cwd=folder)
    claude_log = install_claude(repo)

    page = repo.forge("work", "BOARD/PAGE")

    assert page.returncode == 0, page.stdout + page.stderr
    assert "Building BOARD/PAGE with Codex (gpt-6.2-sol, low) because workers = codex" in page.stdout, page.stdout

    started = repo.forge("task", "start", "BOARD/HELP")
    assert started.returncode == 0, started.stdout + started.stderr
    help_folder = repo.path.parent / f"{repo.path.name}-BOARD-HELP"
    (help_folder / "forge.toml").write_text(text, encoding="utf-8")
    repo.git("commit", "-qam", "Use this repo's settings", cwd=help_folder)
    plain = repo.forge("work", "BOARD/HELP")
    assert plain.returncode == 0, plain.stdout + plain.stderr
    assert "Building BOARD/HELP with Codex (gpt-6.2-sol, low) because workers = codex" in plain.stdout, plain.stdout
    starts = _sent(codex_log, "thread/start")
    assert [(start["config"]["model"], start["config"]["model_reasoning_effort"])
            for start in starts] == [("gpt-6.2-sol", "low"), ("gpt-6.2-sol", "low")]
    assert len(_sent(codex_log, "turn/start")) == 2
    assert calls(claude_log) == []
