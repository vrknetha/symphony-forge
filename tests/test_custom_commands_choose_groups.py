"""Custom commands choose groups from discoverable related test files.

Test-audit: Real commits exercise the synced decision, workflow matrix and
forge test --change. Receipt files prove which tests run. Existing coverage
does not run custom pytest commands or the uv-wrapped picker through CI.
Own shards must keep every group. No new production seam is needed.
"""
import json
import os
import re
import subprocess
import sys

import pytest

from test_ci_limits_pull_requests_to_linux import expression
from test_groups_pytest import _branch, _new_client, _settings, _set_base_to_head, _group
from test_merged_default_branch_pull_requests_run_normal_groups import _commit
from test_testplace_workflow import _jobs

STORY = "FIX-CUSTOM-COMMAND-ONE-GROUP"


@pytest.mark.parametrize("command", ["automatic", "picker", "sharded", "mixed", "unknown"])
def test_1_custom_command_uses_related_test_share(repo, gh, tmp_path, monkeypatch, command):
    client = _new_client(repo, gh, tmp_path, "client")
    _branch(repo, client, "custom-groups")
    full = "uv run --frozen --python 3.11 pytest tests -q -o faulthandler_timeout=120"
    if command == "sharded":
        full = "uv run --frozen --python 3.11 pytest tests -q --splits 4 --group {group}"
    elif command == "mixed":
        full = "pytest tests -q --splits 4 --group {group} && python -c \"pass\""
    elif command == "unknown":
        full = "uv run --frozen python run_tests.py --splits {groups} --group {group}"
        (client / "run_tests.py").write_text(
            "import subprocess, sys\n"
            "sys.exit(subprocess.call([sys.executable, '-m', 'pytest', 'tests', '-q', *sys.argv[1:]]))\n",
            "utf-8")
    _settings(client, test=full, groups=4,
              fast_test="uv run --frozen --python 3.11 forge test --pytest {base}"
              if command == "picker" else "")
    locked = subprocess.run(["uv", "lock"], cwd=client, env={**os.environ, "UV_FROZEN": "0"},
                            capture_output=True, text=True, timeout=60)
    assert locked.returncode == 0, locked.stdout + locked.stderr
    (client / "src").mkdir(exist_ok=True)
    (client / "tests").mkdir(exist_ok=True)
    for name in ("central", "leaf", "quarter"):
        (client / f"src/{name}.py").write_text("VALUE = 1\n", "utf-8")
    for i in range(20):
        imports = "# src/central.py\n"
        if i < 4:
            imports += "# src/leaf.py\n"
        if i < 5:
            imports += "# src/quarter.py\n"
        (client / f"tests/test_case_{i}.py").write_text(
            imports + "from pathlib import Path\n"
            "def test_it():\n"
            f"    Path({json.dumps((tmp_path / f'ran-{i}').as_posix())}).write_text('ran', encoding='utf-8')\n",
            "utf-8")
    # Files outside the command's suite cannot enlarge the denominator.
    (client / "examples").mkdir()
    for i in range(12):
        (client / f"examples/test_example_{i}.py").write_text("def test_it(): pass\n", "utf-8")
    synced = repo.forge("sync", cwd=client)
    assert synced.returncode == 0, synced.stdout + synced.stderr
    repo.git("add", "-A", cwd=client)
    setup = repo.git("commit-tree", repo.git("write-tree", cwd=client), "-p",
                     repo.git("rev-parse", "HEAD", cwd=client), "-m", "Set up selection", cwd=client)
    repo.git("update-ref", "HEAD", setup, cwd=client)
    _set_base_to_head(repo, client)
    base = repo.git("rev-parse", "HEAD", cwd=client)
    workflow = (client / ".github/workflows/forge.yml").read_text("utf-8")
    jobs = _jobs(workflow)
    matrix = re.search(r"^        group: (.+)$", jobs["tests"], re.M)[1]
    matrix = matrix.replace("needs.docs-check.outputs.one-group", "github.one_group")
    group_output = re.search(r"^      one-group: (.+)$", jobs["docs-check"], re.M)[1]
    group_output = group_output.replace("steps.docs.outputs.one-group", "github.one_group")
    group_count = re.search(r"^      FORGE_GROUPS: (.+)$", jobs["tests"], re.M)[1]
    group_count = group_count.replace("needs.docs-check.outputs.one-group", "github.one_group")
    cases = [("leaf", "true"), ("quarter", "false"), ("central", "false")]
    if command in {"sharded", "mixed", "unknown"}:
        cases = [("leaf", "false")]
    for name, expected in cases:
        head = _commit(repo, client, tmp_path, [base], {f"src/{name}.py": "VALUE = 2\n"})
        repo.git("checkout", "-q", "--detach", head, cwd=client)
        output = tmp_path / "outputs"
        output.write_text("", "utf-8")
        result = subprocess.run([sys.executable, ".forge/review-tests.py"], cwd=client,
            env={**os.environ, "BASE_SHA": base, "HEAD_SHA": head,
                 "DOCS_ONLY_EXCLUDES": "[]", "GITHUB_OUTPUT": output.as_posix()},
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        values = dict(line.split("=", 1) for line in output.read_text("utf-8").splitlines())
        assert values["one-group"] == expected, (name, values)
        one = expression(group_output, one_group=values["one-group"])
        groups = expression(matrix, one_group=one)
        assert groups == ([1] if expected == "true" else [1, 2, 3, 4])
        count = int(expression(group_count, one_group=one))
        assert count == len(groups)
        # Run exactly the jobs CI selected, with the same total-group value.
        for group in groups:
            done = _group(repo, client, monkeypatch, group, count)
            assert done.returncode == 0, done.stdout + done.stderr
        wanted = {"leaf": set(range(4)), "quarter": set(range(5)),
                  "central": set(range(20))}[name]
        if command == "unknown":
            wanted = set(range(20))
        assert {i for i in range(20) if (tmp_path / f"ran-{i}").exists()} == wanted
        for i in wanted:
            (tmp_path / f"ran-{i}").unlink()
