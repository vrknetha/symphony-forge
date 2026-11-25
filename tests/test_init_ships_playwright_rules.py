"""New clients receive shared browser test guidance for both agent hosts."""
import subprocess
from pathlib import Path

STORY = "FIX-PLAYWRIGHT-TESTS-SKILL"


def test_1_init_ships_playwright_rules(repo, gh, tmp_path):
    client, remote = tmp_path / "client", tmp_path / "client.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(client)], check=True)
    repo.git("remote", "add", "origin", str(remote), cwd=client)
    gh.respond("api", stdout="{}")
    result = repo.forge("init", "--actions", "yes", cwd=client)
    assert result.returncode == 0, result.stdout + result.stderr
    for host in (".claude", ".codex"):
        skill = client / host / "skills/playwright-tests/SKILL.md"
        assert skill.is_file(), f"Init did not ship {host}'s Playwright rules"
        source = Path(__file__).resolve().parents[1] / "src/forge/templates/skills/playwright-tests/SKILL.md"
        assert skill.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
