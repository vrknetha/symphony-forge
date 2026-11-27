"""Pull requests use Linux and keep their required checks."""
import json
import re
import tomllib
from pathlib import Path

STORY = "FIX-FORGE-CI-LINUX-PRS"
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/forge-next.yml"


def expression(text, **github):
    """Evaluate one workflow ${{ }} expression for the given github.* values."""
    inner = re.fullmatch(r"\$\{\{(.+)\}\}", text.strip(), re.S)
    assert inner, f"Not an expression: {text}"
    # ponytail: covers the ==, &&, || and fromJSON this workflow uses, not GitHub's full grammar.
    code = re.sub(r"github\.[\w.]+", lambda name: repr(github.get(name[0][7:])), inner[1])
    code = code.replace("needs.selection.outputs.test-only", repr(github.get("test_only", "false")))
    code = code.replace("always()", "True")
    code = code.replace("needs.docs-check.result", repr(github.get("docs_result", "success")))
    code = code.replace("needs.docs-check.outputs.docs-only", repr(github.get("docs_only", "false")))
    return eval(code.replace("&&", " and ").replace("||", " or "), {"fromJSON": json.loads})


def test_2_pull_requests_keep_closes_named_checks():
    settings = tomllib.loads((ROOT / "forge.toml").read_text(encoding="utf-8"))
    checks = settings["checks"]
    place = settings.get("test_place", "ci" if any(
        check != "forge-pr-check" for check in checks) else "local")
    assert "forge-pr-check" in checks
    workflow = (ROOT / ".github/workflows/forge.yml").read_text(encoding="utf-8")
    # The required test gate answers only to pull requests. Evaluate the emitted
    # event condition and name without fixing its syntax.
    jobs = dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)",
                           workflow.split("\njobs:\n", 1)[1], re.M | re.S))
    for name in ("tests", "forge-pr-check"):
        if name not in checks or (name == "tests" and place == "local"):
            continue
        job = (jobs.get("tests-passed", jobs["tests"]) if name == "tests" else jobs[name])
        condition = re.search(r"^    if: (.+)$", job, re.M)[1]
        expected_event = "pull_request" if name == "tests" else "pull_request_target"
        for event in ("pull_request", "pull_request_target", "push", "schedule", "workflow_dispatch"):
            assert bool(expression("${{ " + condition + " }}", event_name=event)) == (
                event == expected_event)
        if name == "tests":
            emitted_name = re.search(r"^    name: (.+)$", job, re.M)[1]
            assert expression(emitted_name, event_name="pull_request") == "tests"
            assert expression(emitted_name, event_name="pull_request_target") == "tests (other event)"
        else:
            assert "name: Review pull request\n" in job
            assert "-f context=forge-pr-check" in job
        assert 'runs-on: "ubuntu-24.04"' in job


def test_3_only_a_pull_request_cancels_its_previous_run():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    block = re.search(r"^concurrency:\n((?:  .+\n)+)", workflow, re.M)
    assert block, "Missing workflow-level concurrency"
    settings = dict(line.strip().split(": ", 1) for line in block[1].splitlines())

    def run(event, ref, run_id, number=None):
        github = {"workflow": "forge-next", "event_name": event, "ref": ref, "run_id": run_id,
                  "event.pull_request.number": number}
        group = re.sub(r"\$\{\{.+?\}\}", lambda part: str(expression(part[0], **github)),
                       settings["group"])
        return group, expression(settings["cancel-in-progress"], **github)

    pr, newer_pr = run("pull_request", "refs/pull/5/merge", 3, 5), run(
        "pull_request", "refs/pull/5/merge", 4, 5)
    assert pr[0] == newer_pr[0] and newer_pr[1]
    tag = run("push", "refs/tags/v1.2.3", 5)
    newer_tag = run("push", "refs/tags/v1.2.3", 8)
    assert tag[0] != newer_tag[0] and not tag[1], "Release tag runs must stay independent"
    for event in ("schedule", "workflow_dispatch"):
        first, second = run(event, "refs/heads/main", 6), run(event, "refs/heads/main", 7)
        assert len({first[0], second[0], pr[0], tag[0]}) == 4 and not second[1]
