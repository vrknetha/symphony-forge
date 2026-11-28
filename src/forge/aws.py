"""AWS Actions runners for a private repo: setup checks and entry point."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from forge import repo

AWS_LABEL = "forge-aws"
ACCOUNT_REGION = re.compile(r"^(\d{12})/([a-z]{2}(?:-[a-z]+)+-\d)$")

REFUSALS = {
    "off": (
        "AWS runners are off in this repo's forge.toml.",
        'ask the owner, then turn them on in a settings fix: aws_runners = "<account>/<region>"',
    ),
    "bad_setting": (
        'forge.toml\'s aws_runners must be "<12-digit account>/<region>", not {value!r}.',
        "ask the owner to fix aws_runners in a settings fix",
    ),
    "other_runner": (
        "forge.toml sets test_runner to {runner}, so test jobs would not use AWS.",
        'ask the owner to set test_runner = "forge-aws" or remove it, in a settings fix',
    ),
    "not_linux": (
        "forge.toml sets runner to {runner}, and AWS runners run Linux (Ubuntu 24.04) jobs only.",
        'ask the owner to set runner = "ubuntu-24.04" in a settings fix',
    ),
    "public_repo": (
        "{owner_repo} is public. GitHub says self-hosted runners should almost never be used for "
        "public repositories, because anyone can open a pull request against them. AWS runners "
        "work for private repos only.",
        "use a private repo",
    ),
    "gh_failed": (
        "Forge could not read if {owner_repo} is private: {detail}. It refuses to go on.",
        "gh auth login",
    ),
    "no_aws": (
        "Forge needs the AWS CLI version 2 signed in on this laptop.",
        "aws login",
    ),
    "wrong_account": (
        "This AWS sign-in is account {account} in {region}; forge.toml names "
        "{expected_account}/{expected_region}, which pays for this repo's runners.",
        "sign in to {expected_account}, or ask the owner to change aws_runners",
    ),
}


def main(args: Any) -> int:
    """`forge lanes --aws setup|off|status`."""
    top = repo.root()
    if args.aws == "setup":
        return setup(top, args)
    print("Nothing created yet.")
    return 0


def _repo_name(top: Path) -> str:
    """Best-effort owner/repo from origin URL for error messages before GitHub answers."""
    done = repo.run("git", "remote", "get-url", "origin", cwd=top)
    url = done.stdout.strip() if done.returncode == 0 else ""
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", url)
    return match[1] if match else top.name


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "no details"


def setup(top: Path, args: Any) -> int:
    """Check every precondition before creating any AWS or GitHub resource."""
    repo.check_pin(top, words="lanes")
    cfg = repo.config(top)

    setting = cfg["aws_runners"]
    if not setting:
        repo.refuse(REFUSALS["off"])
    match = ACCOUNT_REGION.fullmatch(setting)
    if not match:
        repo.refuse(REFUSALS["bad_setting"], value=setting)
    expected_account, expected_region = match[1], match[2]

    test_runner = cfg["test_runner"]
    if test_runner and test_runner != AWS_LABEL:
        repo.refuse(REFUSALS["other_runner"], runner=test_runner)

    runner = cfg["runner"]
    if not runner.startswith("ubuntu-"):
        repo.refuse(REFUSALS["not_linux"], runner=runner)

    gh_done = repo.run("gh", "api", "repos/{owner}/{repo}", cwd=top)
    if gh_done.returncode != 0:
        repo.refuse(REFUSALS["gh_failed"], owner_repo=_repo_name(top),
                    detail=_last_line(gh_done.stderr or gh_done.stdout))
    try:
        info = json.loads(gh_done.stdout)
    except ValueError:
        repo.refuse(REFUSALS["gh_failed"], owner_repo=_repo_name(top),
                    detail=_last_line(gh_done.stdout or gh_done.stderr))
    if not isinstance(info, dict) or not isinstance(info.get("private"), bool):
        repo.refuse(REFUSALS["gh_failed"], owner_repo=_repo_name(top),
                    detail="unexpected GitHub response")
    owner_repo = info.get("full_name") or _repo_name(top)
    if not info["private"]:
        repo.refuse(REFUSALS["public_repo"], owner_repo=owner_repo)

    if shutil.which("aws") is None:
        repo.refuse(REFUSALS["no_aws"])
    version = repo.run("aws", "--version", cwd=top)
    if version.returncode != 0 or not (version.stdout + version.stderr).strip().startswith("aws-cli/2."):
        repo.refuse(REFUSALS["no_aws"])

    identity = repo.run("aws", "sts", "get-caller-identity", "--output", "json", cwd=top)
    if identity.returncode != 0:
        repo.refuse(REFUSALS["no_aws"])
    try:
        caller = json.loads(identity.stdout)
    except ValueError:
        repo.refuse(REFUSALS["no_aws"])
    account = caller.get("Account") if isinstance(caller, dict) else None
    if not isinstance(account, str) or not account:
        repo.refuse(REFUSALS["no_aws"])

    region = (getattr(args, "region", None) or os.environ.get("AWS_REGION")
              or os.environ.get("AWS_DEFAULT_REGION") or "")
    if not region:
        configured = repo.run("aws", "configure", "get", "region", cwd=top)
        region = configured.stdout.strip() if configured.returncode == 0 else ""
    if account != expected_account or region != expected_region:
        repo.refuse(REFUSALS["wrong_account"], account=account, region=region or "no region",
                    expected_account=expected_account, expected_region=expected_region)

    print("Nothing created yet.")
    return 0
