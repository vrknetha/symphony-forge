"""Worker routing comes from the default branch's forge.toml, not a story branch's older copy."""
from test_codex_worker import _codex_repo, sdk_data, story  # noqa: F401

STORY = "settings-from-main"


def test_1_a_story_part_follows_workers_changed_on_main(repo, monkeypatch, sdk_data):
    _codex_repo(repo, monkeypatch, sdk_data, start_task=False)
    story(repo)
    repo.git("push", "-q", "origin", "story/BOARD")
    text = (repo.path / "forge.toml").read_text(encoding="utf-8")
    assert 'workers = "codex"' in text
    repo.write("forge.toml", text.replace('workers = "codex"', 'workers = "claude"'))
    repo.git("commit", "-qam", "Workers move to Claude")
    repo.git("push", "-q", "origin", "main")
    shown = repo.forge("next").stdout
    assert "Next: forge task start BOARD/" in shown, shown
    assert "# Claude builds it" in shown and "Codex builds it" not in shown, shown


def test_2_forge_work_runs_with_main_s_models_and_the_local_override(repo, monkeypatch, sdk_data):
    from test_codex_worker import MODELS, _sent, _toml
    folder, calls = _codex_repo(repo, monkeypatch, sdk_data)
    version = repo.forge("--version").stdout.split()[-1]
    nova = {"model": "gpt-6-nova", "effort": "high"}
    repo.write("forge.toml", _toml(version, "codex", {**MODELS, "build": nova, "fix": nova}))
    repo.git("commit", "-qam", "Switch models on main")
    repo.git("push", "-q", "origin", "main")
    # A merge conflict elsewhere stops the merge of main, so the task keeps its old forge.toml.
    repo.write("README.md", "main\n")
    repo.git("add", "README.md")
    repo.git("commit", "-qm", "Readme on main")
    repo.git("push", "-q", "origin", "main")
    (folder / "README.md").write_text("task\n", "utf-8")
    repo.git("add", "README.md", cwd=folder)
    repo.git("commit", "-qm", "Readme on task", cwd=folder)
    assert repo.forge("work", "BOARD/PAGE").returncode == 0
    assert 'gpt-6-nova' not in (folder / "forge.toml").read_text("utf-8")
    config = _sent(calls, "thread/start")[-1]["config"]
    assert (config["model"], config["model_reasoning_effort"]) == ("gpt-6-nova", "high")
    # The clone's own file lays over main's models.
    (repo.path / "forge.local.toml").write_text('[models.fix]\nmodel = "gpt-6-luna"\neffort = "low"\n', "utf-8")
    assert repo.forge("work", "BOARD/PAGE").returncode == 0
    config = _sent(calls, "thread/resume")[-1]["config"]
    assert (config["model"], _sent(calls, "turn/start")[-1]["effort"]) == ("gpt-6-luna", "low")
