"""The guide and worker brief state the workarounds and limits found by the v1.2.40 to v1.2.46 audit."""

from pathlib import Path

from conftest import ROOT
from test_setup import _fresh_client

STORY = "guide-catchup-1-2-40-to-46"


def _flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_1_new_repo_guides_and_brief_state_the_audit_items(repo, gh, tmp_path):
    client, made = _fresh_client(repo, gh, tmp_path)
    assert made.returncode == 0, made.stdout + made.stderr
    brief = _flat(ROOT / "src/forge/templates/brief.md")
    for host in (".claude", ".codex"):
        guide = _flat(client / host / "skills/forge/SKILL.md")
        for claim in (
            "after an earlier review it reviews only changes made since that review. An amend with no "
            "new commit does not recheck existing code against the new text",
            "an earlier finding that quotes the old Done-when can still block",
            "A `fast_test` with `--testNamePattern`, `--grep`, `-t` or `-g` keeps all groups. Forge does "
            "not see Vitest's `--test-name-pattern` spelling or a name filter set in the Vitest config",
            "`git fetch origin` first and close both items on one laptop. The `forge land` line that "
            "close prints after Ready can also leave out such an item",
            "update the main checkout to the default branch before you run land",
            "No command retires a started part: to replace one, close its pull request and delete its "
            "branch locally and on origin",
            "(it reports Merged only when the pull request merged)",
            "One round with a note clears every answered question.",
            "clears every question in a paragraph that names that command, even a second question there "
            "that it does not answer",
            "Another machine sees a question cut to 300 characters: the command clears it only when its "
            "name comes before the cut. When it comes after the cut, you cannot see it, so ask the worker "
            "to repeat the question shorter. A question that asks for other commands clears only with a "
            "`--note` round",
            "If GitHub fails to start the review check, close stops at once and says so. It does not wait "
            "again. Push a new commit or reopen the pull request on GitHub, then run `forge close <item>`",
        ):
            assert claim in guide, (host, claim)
    for claim in (
        "A recorded allowance or amendment also clears a second question in the same paragraph.",
        "the `--test-name-pattern` spelling is not seen, so use `--testNamePattern`",
    ):
        assert claim in brief, claim
