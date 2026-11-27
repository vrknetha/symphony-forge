"""Init's CI selector chooses groups without installing or loading app tests.

Test-audit: The public CI outputs must handle test changes with Forge records
on a fresh checkout. Preinstalled runners and sync hid both failures before.
This runs init's generated shell command and matrix, without a production seam
or a fake choosing the result. Extra source files and commands that cannot
select changed tests keep all groups.
"""
import json
import os
import re
import subprocess

import pytest

from test_ci_limits_pull_requests_to_linux import expression
from test_groups_pytest import _remote_client
from test_merged_default_branch_pull_requests_run_normal_groups import _commit
from test_testplace_workflow import _jobs

STORY = "FIX-TS-TEST-ONLY-ONE-GROUP"
CHANGE = ("npm ci && npx --no-install vitest run --changed {base} "
          "--shard={group}/{groups}")


@pytest.mark.platform
def test_1_javascript_test_changes_choose_one_group(repo, gh, tmp_path):
    client = tmp_path / "client"
    _remote_client(repo, client, tmp_path / "client.git")
    version = repo.forge("--version").stdout.split()[-1]
    # Settings exist before init, so its first generated workflow must be correct.
    settings = {"version": version, "repo": "client", "groups": 4, "test_place": "ci",
        "checks": ["tests", "forge-pr-check"], "fast_test": CHANGE,
        "test": "npm ci && npx --no-install vitest run --shard={group}/{groups}"}
    (client / "forge.toml").write_text("".join(
        f"{name} = {json.dumps(value)}\n" for name, value in settings.items()), "utf-8")
    gh.respond("api", stdout="{}")
    gh.respond("api", "repos/{owner}/{repo}/branches/main/protection", exit=1,
               stdout='{"message":"Branch not protected","status":"404"}')
    initialized = repo.forge("init", "--starter", "--actions", "yes", cwd=client)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    initial = repo.git("rev-parse", "HEAD", cwd=client)
    names = [f"ci-tests/case.{kind}.{ext}" for kind in ("test", "spec")
             for ext in ("ts", "tsx", "js", "jsx")]
    names += ["ci-tests/__tests__/plain.ts", "ci-tests/config.test.ts"]
    changes = {name: "throw new Error('The selector must not load app tests');\n" for name in names}
    record = ".factory/fixes/javascript-config-groups.json"
    changes.update({record: json.dumps({"kind": "fix", "branch": "fix/javascript-groups",
        "why": "Change JavaScript tests", "status": "working"}) + "\n",
        "plans/spotted/javascript-config-groups.json": '{"items": []}\n',
        "plans/javascript-groups.md": "Build notes for this fix.\n"})
    workflow = (client / ".github/workflows/forge.yml").read_text("utf-8")
    jobs = _jobs(workflow)
    job = jobs["docs-check"]
    select = re.search(r"^        run: (.+)$", job, re.M)[1]
    excludes = re.search(r"^          DOCS_ONLY_EXCLUDES: '(.*)'$", job, re.M)[1]
    matrix = re.search(r"^        group: (.+)$", jobs["tests"], re.M)[1]
    matrix = matrix.replace("needs.docs-check.outputs.one-group", "github.one_group")
    group_output = re.search(r"^      one-group: (.+)$", job, re.M)[1]
    group_output = group_output.replace("steps.docs.outputs.one-group", "github.one_group")
    # The CI job can fall back to plain Python when its isolated Forge install fails.
    # A private, offline cache exercises that real fallback with no app dependencies.
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"DOCS_ONLY_EXCLUDES": excludes,
        "GITHUB_EVENT_NAME": "pull_request", "PR_REUSE": "false", "UV_OFFLINE": "1",
        "UV_CACHE_DIR": (tmp_path / "uv-cache").as_posix()})
    for fast, expected in ((CHANGE, "true"), ("", "false"),
                           (CHANGE + " --testNamePattern=smoke", "false")):
        settings["fast_test"] = fast
        # Each command is in the base, not an extra non-test change in the PR.
        base = _commit(repo, client, tmp_path, [initial], {"forge.toml": "".join(
            f"{name} = {json.dumps(value)}\n" for name, value in settings.items())})
        for source in (False, True):
            files = {**changes, **({"ci-tests/source.ts": "export const value = 1;\n"} if source else {})}
            head = _commit(repo, client, tmp_path, [base], files)
            repo.git("checkout", "-q", "--detach", head, cwd=client)
            output = tmp_path / "outputs"
            output.write_text("", "utf-8")
            decision = subprocess.run(select, shell=True, cwd=client,
                env={**environment, "BASE_SHA": base, "HEAD_SHA": head,
                     "GITHUB_OUTPUT": output.as_posix()}, capture_output=True, text=True, timeout=60)
            assert decision.returncode == 0, decision.stdout + decision.stderr
            values = dict(line.split("=", 1) for line in output.read_text("utf-8").splitlines())
            want = "false" if source else expected
            assert values["one-group"] == want, values
            assert values.get("docs-only") != "true", values
            one = expression(group_output, one_group=values["one-group"])
            assert expression(matrix, one_group=one) == ([1] if want == "true" else [1, 2, 3, 4])
            assert not (client / "node_modules").exists()
