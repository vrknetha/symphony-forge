"""Manual full runs decide the story merge hold alongside scheduled full runs.

Test-audit:
1. Protect the real merge decision from the newest finished full run on main.
2. Unrelated events or an unfinished rerun must not hide a failed full run.
3. Scheduled-only coverage does not mix events, compare their ages or inspect rerun attempts.
4. Fake only GitHub at its external edge. No production seam is needed.
"""
import json

import pytest

from test_close import env  # noqa: F401
from test_merge_command import _merge_at_github
from test_nightly_result_controls_merges import NIGHTLY_RUNS, NIGHTLY_URL, _ready_task

STORY = "nightly-hold-manual-run"


@pytest.mark.platform
@pytest.mark.parametrize("latest,conclusion", [
    ("workflow_dispatch", "success"), ("workflow_dispatch", "failure"),
    ("schedule", "failure"), ("schedule", None), ("schedule", "cancelled"),
], ids=["manual-pass", "manual-failure", "newer-nightly-failure", "rerun-running", "rerun-cancelled"])
def test_1_newest_finished_full_run_decides_story_merge(env, latest, conclusion):
    item = _ready_task(env)
    newest = {"id": 44, "event": latest, "conclusion": conclusion, "run_attempt": 2,
              "created_at": "2026-11-20T05:00:00Z", "head_branch": "main",
              "display_title": "Repair full suite", "html_url": NIGHTLY_URL}
    older = {**newest, "id": 43, "run_attempt": 1,
             "event": "schedule" if latest == "workflow_dispatch" else "workflow_dispatch",
             "conclusion": "failure" if conclusion == "success" else "success",
             "created_at": "2026-11-20T03:00:00Z"}
    endpoint = NIGHTLY_RUNS.format(workflow="forge.yml")
    # Isolate the crowded-page case from the rerun cases, which expose the old status filter.
    unfiltered = ([{**newest, "event": "issue_comment", "conclusion": "success"} for _ in range(100)]
                  if latest == "workflow_dispatch" and conclusion == "failure" else [newest, older])
    env.gh.respond("api", endpoint, stdout=json.dumps({"workflow_runs": unfiltered}))
    for event in ("schedule", "workflow_dispatch"):
        env.gh.respond("api", endpoint, "--method", "GET", "--raw-field", f"event={event}",
                       stdout=json.dumps({"workflow_runs": [run for run in (newest, older)
                                                            if run["event"] == event]}))
    env.gh.respond("api", "repos/{owner}/{repo}/actions/runs/44/attempts/1",
                   stdout=json.dumps({"conclusion": "failure"}))
    _merge_at_github(env, branch=f"task/SHOP-{item.split('/', 1)[-1]}")

    merged = env.repo.forge("merge", item)

    if conclusion == "success":
        assert merged.returncode == 0, merged.stdout + merged.stderr
        assert len(env.gh_calls("pr", "merge")) == 1
    else:
        assert merged.returncode != 0
        assert f"The full run Repair full suite ({NIGHTLY_URL}) failed. Hold this task." in merged.stderr
        assert "After the repair, start a full run by hand on the default branch to clear the hold." in merged.stderr
        assert not env.gh_calls("pr", "merge")
