"""The v1.2.45 upgrade command launches the new sync; only uv/GitHub are faked."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

from conftest import FORGE_SHIM, ROOT, _install, patient
from test_close import env  # noqa: F401
from test_upgrade_command import RELEASE, unsynced_up, up  # noqa: F401

STORY = "codex-0-169-0-and-later-add-environmenti"
pytestmark = pytest.mark.platform
NOTICE = ("New repos use gpt-6.2-sol for Codex work. Your model settings stay the same. "
          "To switch, ask your agent to set your Sol entries in forge.toml to gpt-6.2-sol. "
          "Use this Forge release or newer: older SDKs reject gpt-6.2-sol.")


@pytest.mark.parametrize("codex_model", ["gpt-6.1-sol", None], ids=["explicit", "default"])
def test_2_upgrade_explains_the_new_codex_default_and_keeps_model_settings(up, tmp_path, codex_model):
    # Current-process tests cannot catch a notice that the newly installed
    # release never runs. The saved upgrade.py is verbatim from v1.2.45.
    original = up.toml()
    if codex_model:
        original = original.replace('models.build = { model = "opus", effort = "high" }',
                                    f'models.build.codex = {{ model = "{codex_model}", effort = "high" }}')
    version = original.split('version = "', 1)[1].split('"', 1)[0]
    original = original.replace(version, "v1.2.45")
    up.on_main("forge.toml", original)
    earlier = tmp_path / "earlier" / "src"
    patient(lambda: shutil.copytree(ROOT / "src/forge", earlier / "forge",
                                    ignore=shutil.ignore_patterns("__pycache__")))
    patient(lambda: shutil.copyfile(ROOT / "tests/fixtures/forge-v1.2.45/upgrade.py",
                                    earlier / "forge/upgrade.py"))
    (earlier / "forge/__init__.py").write_text('__version__ = "1.2.45"\n', encoding="utf-8")
    _install(up.repo.bin, "forge", FORGE_SHIM.format(python=sys.executable, src=str(earlier)))

    data = Path(os.environ["XDG_DATA_HOME"])
    codex = data / "forge/codex-sdk/openai-codex-0.171.0"
    claude = data / "forge/claude-sdk/claude-agent-sdk-0.2.187"
    package_cache = tmp_path / "package-cache"
    patient(lambda: shutil.copytree(codex, package_cache, symlinks=True))
    patient(lambda: shutil.rmtree(codex))
    patient(lambda: shutil.rmtree(claude))
    old_markers = []
    for kind, package, pin in (("codex", "openai-codex", "0.159.2"),
                               ("claude", "claude-agent-sdk", "0.2.161")):
        previous = data / f"forge/{kind}-sdk/{package}-{pin}"
        previous.mkdir(parents=True)
        marker = previous / "forge-sdk-ready"
        marker.write_text(pin + "\n", encoding="utf-8")
        old_markers.append((marker, marker.read_bytes()))

    # Copies stand in for downloaded wheels. Forge decides whether to install.
    uv = up.repo.bin / "uv"
    sdk_install = f'''
if args[0] == "venv":
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", args[-1]], check=True)
    sys.exit(0)
if args[:2] == ["pip", "install"]:
    python = args[args.index("--python") + 1]
    site = pathlib.Path(subprocess.check_output([python, "-c",
        "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip())
    if args[-1] == "openai-codex==0.171.0":
        source = pathlib.Path({json.dumps(str(package_cache))})
        cached_python = source / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cached_site = subprocess.check_output([str(cached_python), "-c",
            "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip()
        shutil.copytree(cached_site, site, dirs_exist_ok=True)
    elif args[-1] == "claude-agent-sdk==0.2.187":
        for name in ("claude_agent_sdk", "claude_agent_sdk-0.2.187.dist-info"):
            shutil.copytree(here / name, site / name, dirs_exist_ok=True)
    else:
        sys.exit("unexpected SDK package: " + args[-1])
    sys.exit(0)
'''
    uv.write_text(uv.read_text("utf-8").replace('if args[0] == "venv":',
                  sdk_install + '\nif args[0] == "venv":', 1),
                  encoding="utf-8")

    done = up.run(RELEASE)

    assert done.returncode == 0, done.stdout + done.stderr
    assert up.show("forge.toml") == original.replace("v1.2.45", RELEASE).strip()
    assert up.toml() == original
    for directory, pin in ((codex, "0.171.0"), (claude, "0.2.187")):
        assert (directory / "forge-sdk-ready").read_text("utf-8").strip() == pin
    assert all(marker.read_bytes() == content for marker, content in old_markers)
    installs = [call["args"] for call in up.uv() if call["args"][:2] == ["pip", "install"]]
    assert {call[-1] for call in installs} == {"openai-codex==0.171.0", "claude-agent-sdk==0.2.187"}
    assert len(installs) == 2
    assert NOTICE in done.stdout.splitlines()

    settings = up.folder / "forge.toml"
    configured = re.sub(r'^models\.build(?:\.codex)? = .*\n', '', settings.read_text("utf-8"), flags=re.M)
    for kind in ("build", "fix", "lite", "design"):
        configured += f'models.{kind}.codex = {{ model = "custom-model", effort = "high" }}\n'
    settings.write_text(configured, encoding="utf-8")
    again = up.repo.forge("sync", cwd=up.folder)
    assert again.returncode == 0, again.stdout + again.stderr
    assert NOTICE not in again.stdout
    assert settings.read_text("utf-8") == configured
    assert len([call for call in up.uv() if call["args"][:2] == ["pip", "install"]]) == 2
