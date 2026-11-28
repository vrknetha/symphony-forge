"""A local reviewer gets its SDK from doctor and sync when tools names the other family."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from conftest import _install, patient
from test_setup import _fresh_client

STORY = "who-reviews-or-cold-reads-cannot-be-swit"
pytestmark = pytest.mark.platform

UV_STUB = r"""#!{python}
import json, pathlib, shutil, subprocess, sys

here = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
with (here / "uv-sdk-calls.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\n")
if args[0] == "venv":
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", args[-1]], check=True)
else:
    env = pathlib.Path(args[args.index("--python") + 1]).parent.parent
    shutil.rmtree(env)
    shutil.copytree({seed!r}, env, symlinks=True)
"""


@pytest.mark.parametrize("tools,reader,command", [
    ("codex", "claude", ("doctor", "--fix")),
    ("claude", "codex", ("doctor", "--fix")),
    ("codex", "claude", ("sync",)),
    ("claude", "codex", ("sync",)),
])
def test_3_local_reviews_installs_the_reader_sdk(repo, gh, tmp_path, monkeypatch,
                                                  tools, reader, command):
    client, initialized = _fresh_client(repo, gh, tmp_path)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    (client / "forge.local.toml").write_text(
        f'tools = "{tools}"\nworkers = "{tools}"\nreviews = "{reader}"\n',
        encoding="utf-8")

    data = Path(os.environ["XDG_DATA_HOME"])
    sdk_root = data / "forge" / ("codex-sdk" if reader == "codex" else "claude-sdk")
    sdk_env, = (path for path in sdk_root.iterdir() if path.is_dir())
    sdk_pin = (sdk_env / "forge-sdk-ready").read_text(encoding="utf-8").strip()
    seed = tmp_path / "sdk-seed"
    shutil.copytree(sdk_env, seed, symlinks=True)
    (seed / "forge-sdk-ready").unlink()
    patient(lambda: shutil.rmtree(sdk_env))

    uv_stub = UV_STUB.replace("{python}", sys.executable).replace(
        "{seed!r}", repr(seed.as_posix()))
    _install(repo.bin, "uv", uv_stub)
    calls_path = repo.bin / "uv-sdk-calls.jsonl"
    calls_path.write_text("", encoding="utf-8")
    if reader == "codex":
        gh.respond("auth", "status")
        codex_home = tmp_path / "codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text(
            f'[projects.{json.dumps(str(client.resolve()))}]\ntrust_level = "trusted"\n',
            encoding="utf-8")
        monkeypatch.setenv("CODEX_HOME", str(codex_home))
        program = repo.bin / ("doctor-codex.cmd" if os.name == "nt" else "doctor-codex")
        _install(repo.bin, "doctor-codex", f'#!{sys.executable}\nimport sys\n'
                 f'print("codex-cli {sdk_pin}" if sys.argv[1:] == ["--version"] '
                 'else "Logged in using ChatGPT")\n')
        monkeypatch.setenv("CODEX_BIN", str(program))

    result = repo.forge(*command, cwd=client)

    package = "openai-codex" if reader == "codex" else "claude-agent-sdk"
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    assert any(call[-1] == f"{package}=={sdk_pin}" for call in calls), result.stdout + result.stderr
    label = "Codex" if reader == "codex" else "Claude Agent"
    assert f"Installed the {label} SDK {sdk_pin}" in result.stdout, result.stdout + result.stderr
    if command == ("sync",):
        assert result.returncode == 0, result.stdout + result.stderr
