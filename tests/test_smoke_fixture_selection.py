"""Smoke fixture changes select the real starter jobs when comparing commits."""
import subprocess
import sys

from conftest import ROOT

STORY = "FIX-SMOKE-FIXTURES-SHARE-PACKAGES"


def test_1_smoke_fixture_changes_run_the_real_starter_jobs(repo, monkeypatch):
    # The workflow no longer runs on pull requests. Keep checking the selector's
    # explicit base mode with real commits that change only one fixture.
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    for fixture in ("tests/test_starter_tree.py", "tests/test_libs_layout.py"):
        base = repo.git("rev-parse", "HEAD")
        repo.write(fixture, "# Changed smoke fixture\n")
        repo.git("add", fixture)
        repo.git("commit", "-qm", "Change a smoke fixture")
        selected = subprocess.run(
            [sys.executable, str(ROOT / "scripts/smoke_select.py"), base],
            cwd=repo.path, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        assert selected.returncode == 0, selected.stdout + selected.stderr
        outputs = dict(line.split("=", 1) for line in selected.stdout.splitlines())
        assert outputs["starter_smoke"] == "true", fixture
        assert outputs["python_starter_smoke"] == "true", fixture
        assert "tests/test_starter_tree.py" in outputs["starter_smoke_args"]
        assert "tests/test_libs_layout.py" in outputs["starter_smoke_args"]
