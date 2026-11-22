"""Codex location metadata must not change the identity of a Forge hook."""
import pytest

from test_codex_worker import _codex_repo, _sent, sdk_data  # noqa: F401
from test_codex_turns_trust_forge_hooks import _listed, _sync, _trusted

STORY = "codex-0-169-0-and-later-add-environmenti"
pytestmark = pytest.mark.platform


def test_1_worker_starts_with_environment_metadata_on_forge_hooks(
        repo, monkeypatch, sdk_data, claude_session):
    _, calls = _codex_repo(repo, monkeypatch, sdk_data)
    _sync(repo, repo.path)
    monkeypatch.setenv("STUB_CODEX_HOOK_TRUST", "modified")

    built = repo.forge("work", "BOARD/PAGE")

    assert built.returncode == 0, built.stdout + built.stderr
    assert all("environmentId" in hook for hook in _listed(calls))
    [start] = _sent(calls, "thread/start")
    assert start["config"]["hooks"] == _trusted(calls)
    assert len(_sent(calls, "turn/start")) == 1
