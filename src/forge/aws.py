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
ORIGIN_REPO = re.compile(
    r"^(?:(?:https?|ssh)://(?:[^/@]+@)?(?P<url_host>[^/:@]+)(?::[0-9]+)?/"
    r"|[^@/:]+@(?P<ssh_host>[^/:@]+):)"
    r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
NON_LINUX_RUNNER = re.compile(r"^(?:windows|macos)(?:$|-)", re.I)
NON_LINUX_CMD = re.compile(
    r"(?i)(?:^|[\s;&|])(?:powershell(?:\.exe)?|cmd(?:\.exe)?\s+/c|pwsh(?:\.exe)?\b[^\n]*\.ps1|\S+\.(?:bat|cmd|ps1))(?=$|[\s;&|\"'])"
)

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
        "forge.toml uses {detail}, and AWS runners run Linux (Ubuntu 24.04) jobs only.",
        "use Linux tests and a Linux runner before turning on AWS runners",
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


def _origin_repo(top: Path) -> tuple[str, str] | None:
    """Return the GitHub hostname and owner/repo from the checkout's origin remote."""
    done = repo.run("git", "remote", "get-url", "origin", cwd=top)
    if done.returncode != 0:
        return None
    match = ORIGIN_REPO.fullmatch(done.stdout.strip())
    return (match["url_host"] or match["ssh_host"], match["slug"]) if match else None


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
    if NON_LINUX_RUNNER.match(runner):
        repo.refuse(REFUSALS["not_linux"], detail=f"runner {runner}")
    for key in ("test", "fast_test"):
        if cfg[key] and NON_LINUX_CMD.search(cfg[key]):
            repo.refuse(REFUSALS["not_linux"], detail=f"a non-Linux {key} command")

    origin = _origin_repo(top)
    if origin is None:
        repo.refuse(REFUSALS["gh_failed"], owner_repo=top.name,
                    detail="origin remote does not point to a GitHub repository")
    origin_host, origin_slug = origin
    gh_env = {key: value for key, value in os.environ.items() if key != "GH_REPO"}
    gh_done = repo.run("gh", "api", f"repos/{origin_slug}", "--hostname", origin_host, cwd=top, env=gh_env)
    if gh_done.returncode != 0:
        repo.refuse(REFUSALS["gh_failed"], owner_repo=origin_slug,
                    detail=_last_line(gh_done.stderr or gh_done.stdout))
    try:
        info = json.loads(gh_done.stdout)
    except ValueError:
        repo.refuse(REFUSALS["gh_failed"], owner_repo=origin_slug,
                    detail=_last_line(gh_done.stdout or gh_done.stderr))
    if not isinstance(info, dict) or not isinstance(info.get("private"), bool):
        repo.refuse(REFUSALS["gh_failed"], owner_repo=origin_slug,
                    detail="unexpected GitHub response")
    full_name = info.get("full_name")
    if not isinstance(full_name, str) or full_name.casefold() != origin_slug.casefold():
        repo.refuse(REFUSALS["gh_failed"], owner_repo=origin_slug,
                    detail=f"GitHub answered for {full_name or 'another repo'}, not {origin_slug}")
    if not info["private"]:
        repo.refuse(REFUSALS["public_repo"], owner_repo=full_name)

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
