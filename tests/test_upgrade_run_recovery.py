"""Audit: protect actionable upgrade refusals and refused handback lane release.

Existing tests cover live/dead processes and accepted results, not these refusals.
Real commands and a real session need no production seam. Stop must release the
advertised lane and permit upgrade. A stopped intake's later result must be refused.
The legacy case exercises the earlier lane record reader, not an ordinary rule
on a second adopted repo. Only that historical input uses the old record shape.
"""
import json
import re

import pytest

from conftest import patient
from test_close import env  # noqa: F401
from test_fix_agent_runs_wait_in_line import _until
from test_lanes_agents import finish, hold_agents, make_work, person, start  # noqa: F401
from test_queue_land_all import client  # noqa: F401
from test_tools_session_hold import Session
from test_train_land_all import _ready, _stub, train  # noqa: F401
from test_upgrade_command import RELEASE, unsynced_up, up  # noqa: F401

STORY = "upgrade-names-stop-ids"
pytestmark = pytest.mark.platform


@pytest.fixture
def intake(up, tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "upgrade-recovery")
    owner = Session(up.repo, tmp_path / "host", "claude-upgrade-session")
    try:
        result = owner.forge("start", "Save a basket")
        assert result.returncode == 0, result.stdout + result.stderr
        yield owner, json.loads(result.stdout)
    finally:
        owner.close()


def test_1_upgrade_names_each_run_and_its_stop_command(up, intake, person):
    owner, offered = intake
    lanes = owner.forge("lanes", "--json")
    assert lanes.returncode == 0, lanes.stderr
    [run] = json.loads(lanes.stdout)["agents"]["entries"]
    result = up.run(RELEASE)
    assert result.returncode == 1, result.stdout + result.stderr
    assert (f"- {run['repo_name']}: {offered['target']} (read), id {run['id']}\n"
            f"  To end this run: forge stop --id {run['id']}") in result.stderr
    assert up.uv() == []
    command = re.search(r"To end this run: (forge stop --id \S+)", result.stderr)[1]
    stopped = owner.forge(*command.split()[1:])
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    lanes = owner.forge("lanes", "--json")
    assert json.loads(lanes.stdout)["agents"]["entries"] == []
    (up.repo.bin / "uv-install-fails").touch()
    allowed = up.run(RELEASE)
    assert "Installing Forge" in allowed.stderr, allowed.stdout + allowed.stderr
    assert "Forge runs are still in progress" not in allowed.stderr


def test_2_refused_handback_releases_its_round_lane(up, intake, person):
    owner, offered = intake
    target, number = offered["target"], offered["round"]
    lanes = owner.forge("lanes", "--json")
    [run] = json.loads(lanes.stdout)["agents"]["entries"]
    stopped = owner.forge("stop", "--id", run["id"])
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    refused = owner.forge("handback", target, "--round", str(number),
                          "--subagent", "explorer", "--text", "No findings.")
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "There is no open round for this target." in refused.stderr
    lanes = owner.forge("lanes", "--json")
    assert lanes.returncode == 0, lanes.stderr
    assert json.loads(lanes.stdout)["agents"]["entries"] == []
    (up.repo.bin / "uv-install-fails").touch()
    result = up.run(RELEASE)
    assert "Installing Forge" in result.stderr, result.stdout + result.stderr
    assert "Forge runs are still in progress" not in result.stderr


def test_3_upgrade_names_legacy_work_and_its_usable_stop_command(up, tmp_path, person):
    hold_agents(up.env)
    item, name = make_work(up.repo, "Correct a legacy typo")
    worker, output = start(up.repo.path, tmp_path / "work", up.repo, "work", item)
    try:
        _until(lambda: worker.poll() is not None or (up.repo.bin / f"started-{name}").exists(),
               "the legacy worker")
        assert worker.poll() is None, output.read_text("utf-8")
        queue = next((tmp_path / "config").rglob("agent-runs.json"))
        [entry] = json.loads(queue.read_text("utf-8"))
        # Input from the old lane contract, before ids and items were stored.
        legacy = {"kind": "work", "repo": entry["checkout_root"],
                  "forge": entry["forge"], "agent": entry["agent"]}
        patient(lambda: queue.write_text(json.dumps([legacy]), "utf-8"))
        refused = up.run(RELEASE)
        assert refused.returncode == 1, refused.stdout + refused.stderr
        assert f": {item} (work), id " in refused.stderr
        assert refused.stderr.count("To end this run:") == 1
        command = re.search(r"To end this run: (forge stop --id \S+)", refused.stderr)[1]
        stopped = up.repo.forge(*command.split()[1:])
        assert stopped.returncode == 0, stopped.stdout + stopped.stderr
        _until(lambda: worker.poll() is not None, "the stopped worker")
        (up.repo.bin / "uv-install-fails").touch()
        allowed = up.run(RELEASE)
        assert "Installing Forge" in allowed.stderr, allowed.stdout + allowed.stderr
    finally:
        finish(up.repo, [worker])


@pytest.mark.parametrize("operation", ["merge", "merge train"])
def test_4_upgrade_names_and_ends_the_actual_ci_wait(up, train, tmp_path, monkeypatch, operation):
    env = train
    monkeypatch.setenv("FORGE_CHECKS_POLL", "0.1")
    slugs = ("aa", "bb") if operation == "merge train" else ("aa",)
    _ready(env, monkeypatch, slugs)
    if operation == "merge train":
        _stub(env, pending_until=(tmp_path / "ci-go").as_posix())
        args = ("land", "--all")
    else:
        (env.repo.bin / "checks-fix-aa.txt").write_text(
            json.dumps({"name": "tests", "status": "in_progress", "conclusion": None}) + "\n"
            + json.dumps({"name": "forge-pr-check", "status": "completed", "conclusion": "success"}) + "\n",
            "utf-8")
        args = ("merge", "aa")
    waiting, output = start(env.repo.path, tmp_path / "wait", env.repo, *args)
    try:
        _until(lambda: waiting.poll() is not None or "Waiting:" in output.read_text("utf-8"),
               "the CI wait")
        assert waiting.poll() is None, output.read_text("utf-8")
        (env.repo.bin / "uv-install-fails").touch()
        upgrading = up.run(RELEASE)
        assert "Forge runs are still in progress" not in upgrading.stderr, upgrading.stderr
        assert "Installing Forge" in upgrading.stderr, upgrading.stdout + upgrading.stderr
        resume = "forge land --all" if operation == "merge train" else "forge merge aa"
        assert (f"Ended {operation} for aa to install Forge. Run {resume} to resume the CI wait."
                in upgrading.stdout), upgrading.stdout + upgrading.stderr
        _until(lambda: waiting.poll() is not None, "the ended CI wait")
    finally:
        (tmp_path / "ci-go").touch()
        (env.repo.bin / "checks-fix-aa.txt").unlink(missing_ok=True)
        finish(env.repo, [waiting])
