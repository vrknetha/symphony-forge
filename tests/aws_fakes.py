"""Fake `aws` CLI for tests: records every call and answers from a JSON state file."""
from __future__ import annotations

import json
import stat
import sys
from pathlib import Path
from typing import Any

AWS_SCRIPT = """#!{python}
import json, pathlib, sys

here = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
log = here / "aws-calls.jsonl"
with log.open("a", encoding="utf-8") as out:
    out.write(json.dumps(args) + "\\n")

state_path = here / "aws-state.json"
state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {{}}

if args == ["--version"]:
    version = state.get("version", "aws-cli/2.17.0 Python/3.11.8")
    sys.stdout.write(version + "\\n")
    sys.exit(state.get("version_exit", 0))

if args[:2] == ["sts", "get-caller-identity"]:
    if state.get("sts_exit", 0) != 0:
        sys.stderr.write(state.get("sts_stderr", "Unable to locate credentials") + "\\n")
        sys.exit(state["sts_exit"])
    sys.stdout.write(json.dumps(state.get("identity", {{"Account": "123456789012"}})) + "\\n")
    sys.exit(0)

if args[:3] == ["configure", "get", "region"]:
    region = state.get("region", "")
    if region:
        sys.stdout.write(region + "\\n")
        sys.exit(0)
    sys.exit(1)

sys.stderr.write("fake aws: unexpected command: aws " + " ".join(args) + "\\n")
sys.exit(1)
"""


def install_fake_aws(bin_dir: Path, state: dict[str, Any] | None = None) -> Path:
    """Install a fake `aws` script in bin_dir and write its state file."""
    path = bin_dir / "aws"
    path.write_text(AWS_SCRIPT.format(python=sys.executable), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    set_aws_state(bin_dir, state or {})
    return path


def set_aws_state(bin_dir: Path, state: dict[str, Any]) -> None:
    (bin_dir / "aws-state.json").write_text(json.dumps(state), encoding="utf-8")


def aws_calls(bin_dir: Path) -> list[list[str]]:
    log = bin_dir / "aws-calls.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def clear_aws_calls(bin_dir: Path) -> None:
    (bin_dir / "aws-calls.jsonl").unlink(missing_ok=True)
