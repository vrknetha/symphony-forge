"""FORGE-PROVIDER-1 SWITCH: AWS runners are off by default, setup refuses what it must, and
test_runner = "forge-aws" routes Linux test jobs and the nightly full run to AWS."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

from aws_fakes import aws_calls, clear_aws_calls, install_fake_aws, set_aws_state

STORY = "FORGE-PROVIDER-1"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="AWS runner tests skip on Windows")
ROOT = Path(__file__).resolve().parents[1]


def _job_runs_on(workflow: str) -> dict[str, str]:
    """Map each top-level GitHub Actions job name to its runs-on value."""
    jobs: dict[str, str] = {}
    current: str | None = None
    in_jobs = False
    for line in workflow.splitlines():
        if line == "jobs:":
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            break
        if in_jobs and (m := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)):
            current = m[1]
        elif current and (m := re.match(r"^    runs-on:\s*(.+?)\s*$", line)):
            jobs[current] = m[1]
    return jobs


def test_1_aws_runners_are_off_by_default(repo, gh, tmp_path, monkeypatch):
    # Old Mainline-only spec and its read file are removed.
    assert not (ROOT / "docs/specs/sandbox-runs.md").exists()
    assert not (ROOT / "docs/specs/sandbox-runs.read.md").exists()

    # Clear AWS region env vars so fake `aws configure get region` drives region checks.
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    install_fake_aws(repo.bin, {"region": "ap-south-1", "identity": {"Account": "123456789012"}})

    client = tmp_path / "client"
    origin = tmp_path / "client-origin.git"
    client.mkdir()
    repo.git("init", "-q", "--bare", str(origin))
    repo.git("init", "-q", "-b", "main", str(client))
    repo.git("remote", "add", "origin", str(origin), cwd=client)

    # New repo: forge init leaves aws_runners unset and makes no AWS or runner-related GitHub call.
    gh.respond("api", "repos/{owner}/{repo}/branches/main/protection", stdout="{}")
    gh.respond("api", "--method", "PUT", "repos/{owner}/{repo}/branches/main/protection", stdout="{}")
    init = repo.forge("init", "--actions", "yes", cwd=client)
    assert init.returncode == 0, init.stderr
    assert aws_calls(repo.bin) == []
    # Only branch-protection calls may occur during init; no repo/runner/app calls.
    for call in gh.calls():
        assert any("branches/main/protection" in arg for arg in call), call
    gh_after_init = len(gh.calls())

    config_text = (client / "forge.toml").read_text(encoding="utf-8")
    assert "aws_runners" not in config_text
    assert repo.forge("sync", cwd=client).returncode == 0
    default_workflow = (client / ".github/workflows/forge.yml").read_text(encoding="utf-8")
    assert "forge-aws" not in default_workflow
    assert _job_runs_on(default_workflow) == {
        "tests": '"ubuntu-24.04"',
        "forge-pr-check": '"ubuntu-24.04"',
        "full-suite": '"ubuntu-24.04"',
        "full-suite-result": '"ubuntu-24.04"',
    }
    assert aws_calls(repo.bin) == []
    assert len(gh.calls()) == gh_after_init
    # Guide in both host skills documents aws_runners and waiting for verified setup before forge-aws.
    for rel in (".claude/skills/forge/SKILL.md", ".codex/skills/forge/SKILL.md"):
        guide = (client / rel).read_text(encoding="utf-8")
        assert "aws_runners" in guide and "forge lanes --aws setup" in guide and 'test_runner = "forge-aws"' in guide

    # Option refusals on `forge lanes`.
    both = repo.forge("lanes", "--box", "setup", "--aws", "setup", cwd=client)
    assert both.returncode != 0
    assert "Use --box or --aws, not both." in both.stderr
    bare_opt = repo.forge("lanes", "--max-machines", "2", cwd=client)
    assert bare_opt.returncode != 0
    assert "Use --max-machines, --budget, --email and --region only with --aws setup." in bare_opt.stderr

    # Off setting refuses before calling aws or gh.
    off = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert off.returncode != 0
    assert "AWS runners are off in this repo's forge.toml." in off.stderr
    assert aws_calls(repo.bin) == []
    assert len(gh.calls()) == gh_after_init

    # Turn on aws_runners alone: workflow bytes do not change.
    base_toml = (client / "forge.toml").read_text(encoding="utf-8")

    def write_toml(extra: str) -> None:
        keys = {line.split("=")[0].strip() for line in extra.splitlines() if "=" in line}
        kept = "\n".join(line for line in base_toml.splitlines()
                         if not (("=" in line) and line.split("=")[0].strip() in keys)) + "\n"
        (client / "forge.toml").write_text(extra + kept, encoding="utf-8")

    write_toml('aws_runners = "123456789012/ap-south-1"\n')
    assert repo.forge("sync", cwd=client).returncode == 0
    assert (client / ".github/workflows/forge.yml").read_text(encoding="utf-8") == default_workflow

    # Refusal: test_runner set to a label other than forge-aws.
    write_toml('aws_runners = "123456789012/ap-south-1"\ntest_runner = "custom-runner"\n')
    other = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert other.returncode != 0
    assert "forge.toml sets test_runner to custom-runner, so test jobs would not use AWS." in other.stderr

    # Refusal (note 66): non-Linux runner (Windows, macOS) or non-Linux test command.
    for bad_runner in ("windows-2022", "macos-14"):
        write_toml(f'aws_runners = "123456789012/ap-south-1"\nrunner = "{bad_runner}"\n')
        non_linux = repo.forge("lanes", "--aws", "setup", cwd=client)
        assert non_linux.returncode != 0
        assert bad_runner in non_linux.stderr and "Linux" in non_linux.stderr
    write_toml('aws_runners = "123456789012/ap-south-1"\ntest = "powershell -File run.ps1"\n')
    win_cmd = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert win_cmd.returncode != 0
    assert "non-Linux test command" in win_cmd.stderr and "Linux" in win_cmd.stderr

    # Refusal: origin is not a GitHub repository URL.
    write_toml('aws_runners = "123456789012/ap-south-1"\n')
    no_gh_origin = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert no_gh_origin.returncode != 0
    assert "origin remote does not point to a GitHub repository" in no_gh_origin.stderr

    # Point origin at a public GitHub repo; GH_REPO pointing to a private repo must not bypass check.
    repo.git("remote", "set-url", "origin", "https://github.com/acme/public-demo.git", cwd=client)
    monkeypatch.setenv("GH_REPO", "acme/private-other")
    gh.respond("api", "repos/acme/private-other",
               stdout=json.dumps({"id": 99, "full_name": "acme/private-other", "private": True}))
    gh.respond("api", "repos/acme/public-demo",
               stdout=json.dumps({"id": 42, "full_name": "acme/public-demo", "private": False}))
    pub = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert pub.returncode != 0
    assert "acme/public-demo is public." in pub.stderr
    assert "public repositories" in pub.stderr
    assert gh.calls("api", "repos/acme/public-demo")
    assert not gh.calls("api", "repos/acme/private-other")
    assert not gh.calls("api", "repos/{owner}/{repo}")

    # Refusal: GitHub answers for a different repo than origin.
    gh.respond("api", "repos/acme/public-demo",
               stdout=json.dumps({"id": 99, "full_name": "acme/private-other", "private": True}))
    mismatch = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert mismatch.returncode != 0
    assert "acme/private-other" in mismatch.stderr and "acme/public-demo" in mismatch.stderr

    # Switch origin to the private repo for remaining checks.
    repo.git("remote", "set-url", "origin", "https://github.com/acme/demo.git", cwd=client)

    # Refusal: gh api fails.
    gh.respond("api", "repos/acme/demo", stderr="HTTP 401: Bad credentials\n", exit=1)
    gh_err = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert gh_err.returncode != 0
    assert "Forge could not read if acme/demo is private:" in gh_err.stderr
    assert "HTTP 401: Bad credentials" in gh_err.stderr

    # Private repo from here on.
    gh.respond("api", "repos/acme/demo",
               stdout=json.dumps({"id": 42, "full_name": "acme/demo", "private": True}))

    # Refusal: no AWS CLI on PATH.
    (repo.bin / "aws").unlink()
    clean_path = os.pathsep.join(
        part for part in os.environ.get("PATH", "").split(os.pathsep)
        if not (Path(part) / "aws").is_file()
    )
    monkeypatch.setenv("PATH", f"{repo.bin}{os.pathsep}{clean_path}")
    no_cli = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert no_cli.returncode != 0
    assert "Forge needs the AWS CLI version 2 signed in on this laptop." in no_cli.stderr

    # Refusal: AWS CLI version 1.
    install_fake_aws(repo.bin, {"version": "aws-cli/1.32.0 Python/3.11.8", "region": "ap-south-1"})
    v1 = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert v1.returncode != 0
    assert "Forge needs the AWS CLI version 2 signed in on this laptop." in v1.stderr

    # Refusal: failed sts get-caller-identity.
    set_aws_state(repo.bin, {"sts_exit": 255, "region": "ap-south-1"})
    no_auth = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert no_auth.returncode != 0
    assert "Forge needs the AWS CLI version 2 signed in on this laptop." in no_auth.stderr

    # Refusal: wrong account.
    set_aws_state(repo.bin, {"identity": {"Account": "999999999999"}, "region": "ap-south-1"})
    wrong_acct = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert wrong_acct.returncode != 0
    assert "This AWS sign-in is account 999999999999 in ap-south-1; forge.toml names 123456789012/ap-south-1" in wrong_acct.stderr

    # Refusal: wrong region.
    set_aws_state(repo.bin, {"identity": {"Account": "123456789012"}, "region": "us-east-1"})
    wrong_reg = repo.forge("lanes", "--aws", "setup", cwd=client)
    assert wrong_reg.returncode != 0
    assert "This AWS sign-in is account 123456789012 in us-east-1; forge.toml names 123456789012/ap-south-1" in wrong_reg.stderr

    # No aws call created anything across all refusal cases.
    allowed_prefixes = (["--version"], ["sts", "get-caller-identity"], ["configure", "get", "region"])
    for call in aws_calls(repo.bin):
        assert any(call[:len(prefix)] == prefix for prefix in allowed_prefixes), call

    # Matching account and region passes checks (both ubuntu-24.04 and documented self-hosted Linux runner).
    for ok_runner in ("ubuntu-24.04", "self-hosted"):
        write_toml(f'aws_runners = "123456789012/ap-south-1"\nrunner = "{ok_runner}"\n')
        clear_aws_calls(repo.bin)
        set_aws_state(repo.bin, {"identity": {"Account": "123456789012"}, "region": "ap-south-1"})
        ok = repo.forge("lanes", "--aws", "setup", cwd=client)
        assert ok.returncode == 0, ok.stderr
        assert "Nothing created yet." in ok.stdout

    # Workflow label routing with test_runner = "forge-aws" for grouped (2) and one-group (1) repos.
    # Use a splittable command ({group}/{groups}) so groups = 2 genuinely generates a 2-group matrix.
    repo.git("checkout", "-q", "-b", "fix/aws-runner-test", cwd=client)
    for groups in (2, 1):
        write_toml(
            'test = "echo {group}/{groups}"\n'
            'aws_runners = "123456789012/ap-south-1"\n'
            'test_runner = "forge-aws"\n'
            f"groups = {groups}\n"
        )
        assert repo.forge("sync", cwd=client).returncode == 0
        wf = (client / ".github/workflows/forge.yml").read_text(encoding="utf-8")
        assert _job_runs_on(wf) == {
            "docs-check": '"ubuntu-24.04"',
            "tests": "${{ needs.docs-check.outputs.docs-tests == 'true' && 'ubuntu-24.04' || 'forge-aws' }}",
            "tests-passed": '"ubuntu-24.04"',
            "forge-pr-check": '"ubuntu-24.04"',
            "full-suite": '"forge-aws"',
            "full-suite-result": '"ubuntu-24.04"',
        }
        if groups == 2:
            assert "group: [1, 2]" in wf
        else:
            assert "group: [1, 2]" not in wf
