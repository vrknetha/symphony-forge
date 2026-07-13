"""forge doctor — machine prerequisites, with --fix auto-install."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import tempfile
import urllib.request
from pathlib import Path

from .common import run_quiet

DIRENV_VERSION = "2.37.1"


def _check(name: str, ok: bool, detail: str, fix: str, required: bool = True) -> dict:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix, "required": required}


def _platform_name() -> str:
    system = platform.system().lower()

    if system == "windows":
        return "windows"

    # Git Bash/MSYS may report Windows through platform.system(), but keep
    # this fallback for unusual Python builds.
    msystem = os.environ.get("MSYSTEM", "").upper()
    if msystem.startswith(("MINGW", "MSYS", "CYGWIN")):
        return "windows"

    if system == "darwin":
        return "macos"

    if system == "linux":
        return "linux"

    return "unknown"


def _current_shell() -> str:
    shell = Path(os.environ.get("SHELL", "")).name.lower()

    if shell in {"bash", "zsh"}:
        return shell

    # Git Bash often does not populate SHELL consistently.
    if os.environ.get("MSYSTEM"):
        return "bash"

    return "bash"


def _shell_rc(home: Path, shell: str) -> Path:
    return home / (".zshrc" if shell == "zsh" else ".bashrc")


def _hook_line(shell: str) -> str:
    return f'eval "$(direnv hook {shell})"'


def _has_direnv_hook(home: Path) -> bool:
    for rc in (home / ".zshrc", home / ".bashrc"):
        if rc.exists():
            try:
                if "direnv hook" in rc.read_text(encoding="utf-8"):
                    return True
            except OSError:
                pass
    return False


def _append_direnv_hook(home: Path) -> bool:
    shell = _current_shell()
    rc = _shell_rc(home, shell)
    line = _hook_line(shell)

    try:
        existing = rc.read_text(encoding="utf-8") if rc.exists() else ""
        if line not in existing:
            with rc.open("a", encoding="utf-8") as fh:
                fh.write(
                    "\n# direnv (symphony-forge: project-local GSTACK_HOME via .envrc)\n"
                    f"{line}\n"
                )
            print(f"[fix ] added direnv hook to {rc}")
        return True
    except OSError as exc:
        print(f"[warn] could not update {rc}: {exc}")
        return False


def _prepend_user_bin_to_path(home: Path) -> Path:
    user_bin = home / "bin"
    user_bin.mkdir(parents=True, exist_ok=True)

    current = os.environ.get("PATH", "")
    entries = current.split(os.pathsep) if current else []
    user_bin_str = str(user_bin)

    if user_bin_str not in entries:
        os.environ["PATH"] = user_bin_str + os.pathsep + current

    return user_bin


def _install_direnv_windows(home: Path) -> bool:
    user_bin = _prepend_user_bin_to_path(home)
    target = user_bin / "direnv.exe"
    temp_target = user_bin / "direnv.exe.download"

    url = (
        "https://github.com/direnv/direnv/releases/download/"
        f"v{DIRENV_VERSION}/direnv.windows-amd64"
    )

    print(f"[fix ] installing direnv {DIRENV_VERSION} for Windows Git Bash ...")

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "symphony-forge-doctor"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with temp_target.open("wb") as fh:
                shutil.copyfileobj(response, fh)

        # A valid Windows binary is several MB. This rejects HTML/404 text.
        if temp_target.stat().st_size < 1_000_000:
            raise RuntimeError(
                f"downloaded file is unexpectedly small ({temp_target.stat().st_size} bytes)"
            )

        temp_target.replace(target)
        target.chmod(target.stat().st_mode | stat.S_IEXEC)
        print(f"[fix ] installed direnv at {target}")
        return True
    except Exception as exc:
        print(f"[warn] failed to install direnv automatically: {exc}")
        try:
            temp_target.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _install_direnv_macos() -> bool:
    brew = shutil.which("brew")
    if not brew:
        print("[warn] Homebrew is required to auto-install direnv on macOS.")
        return False

    print("[fix ] installing direnv with Homebrew ...")
    code, _ = run_quiet([brew, "install", "direnv"])
    return code == 0


def _install_direnv_linux() -> bool:
    installers: list[tuple[list[str], str]] = []

    if shutil.which("apt-get"):
        prefix = [] if os.geteuid() == 0 else (["sudo"] if shutil.which("sudo") else [])
        if prefix or os.geteuid() == 0:
            installers.append((prefix + ["apt-get", "update"], "apt-get update"))
            installers.append((prefix + ["apt-get", "install", "-y", "direnv"], "apt-get"))
    elif shutil.which("dnf"):
        prefix = [] if os.geteuid() == 0 else (["sudo"] if shutil.which("sudo") else [])
        if prefix or os.geteuid() == 0:
            installers.append((prefix + ["dnf", "install", "-y", "direnv"], "dnf"))
    elif shutil.which("yum"):
        prefix = [] if os.geteuid() == 0 else (["sudo"] if shutil.which("sudo") else [])
        if prefix or os.geteuid() == 0:
            installers.append((prefix + ["yum", "install", "-y", "direnv"], "yum"))
    elif shutil.which("pacman"):
        prefix = [] if os.geteuid() == 0 else (["sudo"] if shutil.which("sudo") else [])
        if prefix or os.geteuid() == 0:
            installers.append((prefix + ["pacman", "-Sy", "--noconfirm", "direnv"], "pacman"))

    if not installers:
        print("[warn] no supported Linux package manager or sudo access found for direnv.")
        return False

    print("[fix ] installing direnv with the system package manager ...")
    for command, label in installers:
        code, _ = run_quiet(command)
        if code != 0:
            print(f"[warn] {label} failed while installing direnv.")
            return False

    return True


def _install_direnv(home: Path) -> bool:
    target_platform = _platform_name()

    if target_platform == "windows":
        installed = _install_direnv_windows(home)
    elif target_platform == "macos":
        installed = _install_direnv_macos()
    elif target_platform == "linux":
        installed = _install_direnv_linux()
    else:
        print("[warn] unsupported platform for automatic direnv installation.")
        return False

    if not installed:
        return False

    # shutil.which reads the current PATH. Windows user-local installation
    # updates PATH in-process through _prepend_user_bin_to_path().
    return shutil.which("direnv") is not None


def _direnv_fix_message() -> str:
    target_platform = _platform_name()

    if target_platform == "windows":
        return (
            "install direnv.exe in ~/bin, add `eval \"$(direnv hook bash)\"` "
            "to ~/.bashrc, reopen Git Bash, then run `direnv allow`"
        )

    if target_platform == "macos":
        shell = _current_shell()
        rc = "~/.zshrc" if shell == "zsh" else "~/.bashrc"
        return (
            f"`brew install direnv` + `eval \"$(direnv hook {shell})\"` in {rc}, "
            "then `direnv allow`"
        )

    return (
        "install direnv with your Linux package manager, add the matching "
        "`eval \"$(direnv hook <shell>)\"` line to your shell rc file, "
        "then run `direnv allow`"
    )


def cmd_doctor(args: argparse.Namespace) -> None:
    home = Path.home()
    checks: list[dict] = []

    def which(binary: str) -> str | None:
        return shutil.which(binary)

    # Core toolchain
    checks.append(_check(
        "git", which("git") is not None, which("git") or "not on PATH",
        "https://git-scm.com — or `xcode-select --install` on macOS"))

    node = which("node")
    node_ok, node_ver = (False, "not on PATH")
    if node:
        code, out = run_quiet([node, "--version"])
        node_ver = out
        node_ok = (
            code == 0
            and out.lstrip("v").split(".")[0].isdigit()
            and int(out.lstrip("v").split(".")[0]) >= 20
        )

    checks.append(_check(
        "node >= 20",
        node_ok,
        node_ver,
        "install Node 20+ (https://nodejs.org or `brew install node`)",
    ))

    checks.append(_check(
        "pnpm",
        which("pnpm") is not None,
        which("pnpm") or "not on PATH",
        "`npm install -g pnpm` (needed once the nx workspace exists)",
        required=False,
    ))

    checks.append(_check(
        "docker",
        which("docker") is not None,
        which("docker") or "not on PATH",
        "Docker Desktop (needed once the nx workspace exists)",
        required=False,
    ))

    # direnv — pins GSTACK_HOME into each repo (.envrc) so gstack output is
    # project-local and committed, not stranded in ~/.gstack.
    if not which("direnv") and args.fix:
        _install_direnv(home)

    direnv = which("direnv")
    hook_ok = _has_direnv_hook(home)

    if direnv and not hook_ok and args.fix:
        hook_ok = _append_direnv_hook(home)

    if direnv and hook_ok and args.fix and Path.cwd().joinpath(".envrc").exists():
        code, out = run_quiet([direnv, "allow", str(Path.cwd())])
        if code == 0:
            print(f"[fix ] allowed {Path.cwd() / '.envrc'}")
        else:
            print(f"[warn] direnv allow failed: {out}")

    if not direnv:
        direnv_detail = "not on PATH"
    elif not hook_ok:
        direnv_detail = f"{direnv} (shell hook missing)"
    else:
        direnv_detail = direnv

    checks.append(_check(
        "direnv + shell hook",
        bool(direnv) and hook_ok,
        direnv_detail,
        _direnv_fix_message(),
    ))

    # Codex — the execution plane
    if not which("codex") and args.fix and which("npm"):
        print("[fix ] installing @openai/codex ...")
        run_quiet(["npm", "install", "-g", "@openai/codex"])

    codex = which("codex")
    if codex:
        code, out = run_quiet([codex, "login", "status"])
        logged_in = code == 0 and "not logged in" not in out.lower()
        checks.append(_check(
            "codex CLI + login",
            logged_in,
            out.splitlines()[-1] if out else "unknown",
            "`codex login` (ChatGPT subscription or API key — login is always manual)",
        ))
    else:
        checks.append(_check(
            "codex CLI + login",
            False,
            "not on PATH",
            "`npm install -g @openai/codex` then `codex login` — or rerun with --fix",
        ))

    # Claude Code — the coordination plane
    claude_bin = which("claude")
    checks.append(_check(
        "claude CLI",
        claude_bin is not None,
        claude_bin or "not on PATH",
        "https://claude.ai/code — install Claude Code",
    ))

    def install_claude_plugin(marketplace_url: str, plugin_ref: str) -> None:
        if not claude_bin:
            return
        run_quiet([claude_bin, "plugin", "marketplace", "add", marketplace_url])
        run_quiet([claude_bin, "plugin", "install", plugin_ref])

    plugin = home / ".claude" / "plugins" / "cache" / "openai-codex" / "codex"
    if not plugin.is_dir() and args.fix and claude_bin:
        print("[fix ] installing codex-plugin-cc ...")
        install_claude_plugin(
            "https://github.com/openai/codex-plugin-cc",
            "codex@openai-codex",
        )

    checks.append(_check(
        "codex-plugin-cc",
        plugin.is_dir(),
        str(plugin) if plugin.is_dir() else "not installed",
        "`claude plugin marketplace add https://github.com/openai/codex-plugin-cc && "
        "claude plugin install codex@openai-codex` — or rerun with --fix "
        "(leave the review gate disabled)",
    ))

    # Required skills
    gstack = home / ".claude" / "skills" / "gstack"
    if not gstack.is_dir() and args.fix:
        print("[fix ] installing gstack ...")
        code, _ = run_quiet([
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/garrytan/gstack.git",
            str(gstack),
        ])
        if code == 0 and (gstack / "setup").exists():
            run_quiet([str(gstack / "setup")])

    checks.append(_check(
        "gstack skills",
        gstack.is_dir(),
        str(gstack) if gstack.is_dir() else "not installed",
        "`git clone --depth 1 https://github.com/garrytan/gstack.git "
        "~/.claude/skills/gstack && ~/.claude/skills/gstack/setup` "
        "(needed for /office-hours discovery) — or rerun with --fix",
    ))

    # Optional tools are reported but are not installed by the normal
    # `doctor --fix` path. This keeps machine setup focused on required items.
    autoreview = home / ".codex" / "skills" / "autoreview"
    checks.append(_check(
        "autoreview skill",
        autoreview.is_dir(),
        str(autoreview) if autoreview.is_dir() else "not installed",
        "clone https://github.com/openclaw/agent-skills and copy skills/autoreview "
        "to ~/.codex/skills/ (escalation-tier review; see harness.yaml)",
        required=False,
    ))

    skill_packs = [
        (
            "mattpocock skills",
            "mattpocock/skills",
            ["--all"],
            home / ".claude" / "skills" / "ask-matt",
        ),
        (
            "anthropic frontend-design",
            "anthropics/skills",
            ["-s", "frontend-design", "-a", "*", "-y"],
            home / ".claude" / "skills" / "frontend-design",
        ),
        (
            "emilkowalski skills",
            "emilkowalski/skills",
            ["--all"],
            home / ".claude" / "skills" / "emil-design-eng",
        ),
    ]

    for name, repo, extra, sentinel in skill_packs:
        checks.append(_check(
            name,
            sentinel.is_dir(),
            "installed" if sentinel.is_dir() else "not installed",
            f"`npx -y skills add {repo} -g --copy {' '.join(extra)}`",
            required=False,
        ))

    ponytail_cache = home / ".claude" / "plugins" / "cache"

    def ponytail_ok() -> bool:
        return ponytail_cache.is_dir() and any(ponytail_cache.glob("*ponytail*"))

    checks.append(_check(
        "ponytail plugin",
        ponytail_ok(),
        "installed" if ponytail_ok() else "not installed",
        "`claude plugin marketplace add https://github.com/DietrichGebert/ponytail && "
        "claude plugin install ponytail@ponytail` "
        "(prototype phase 0b only — see harness.yaml)",
        required=False,
    ))

    width = max(len(c["name"]) for c in checks)
    failures = 0

    for check in checks:
        mark = "OK " if check["ok"] else ("MISS" if check["required"] else "opt ")
        print(f"[{mark}] {check['name']:<{width}}  {check['detail']}")

        if not check["ok"]:
            print(f"       fix: {check['fix']}")
            if check["required"]:
                failures += 1

    if failures:
        print(f"\nforge doctor: {failures} required tool(s) missing.")
        raise SystemExit(1)

    print("\nforge doctor: ready. Next: forge.py init --name <project> --target <dir>")
