"""The installed coordinator guide requires explicit models for ad-hoc subagents."""

from pathlib import Path

from test_setup import _fresh_client

STORY = "FIX-A-COORDINATOR-S-OWN-AD-HOC-SUBAGENTS-WIT"


def test_1_the_coordinator_guide_requires_ad_hoc_subagent_models(repo, gh, tmp_path):
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr

    # The file-relative path also selects this test when the template changes.
    template = Path(__file__).resolve().parents[1] / "src/forge/templates/skill.md"
    for host in (".claude", ".codex"):
        path = client / host / "skills/forge/SKILL.md"
        guide = " ".join(path.read_text(encoding="utf-8").split())
        missing = f"Missing model guidance in {path.relative_to(client)}, shipped from {template}"
        assert (
            "Set a model explicitly on every ad-hoc subagent you start outside Forge's roles"
            in guide
        ), missing
        assert "Sonnet for analysis and research" in guide, missing
        assert "Haiku for sorting and search" in guide, missing
