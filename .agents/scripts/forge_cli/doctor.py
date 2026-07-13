"""forge doctor — machine prerequisites, with --fix auto-install."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .common import run_quiet


def _check(name: str, ok: bool, detail: str, fix: str, required: bool = True) -> dict:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix, "required": required}


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
        node_ok = code == 0 and out.lstrip("v").split(".")[0].isdigit() and int(out.lstrip("v").split(".")[0]) >= 20
    checks.append(_check("node >= 20", node_ok, node_ver, "install Node 20+ (https://nodejs.org or `brew install node`)"))
    checks.append(_check(
        "pnpm", which("pnpm") is not None, which("pnpm") or "not on PATH",
        "`npm install -g pnpm` (needed once the nx workspace exists)", required=False))
    checks.append(_check(
        "docker", which("docker") is not None, which("docker") or "not on PATH",
        "Docker Desktop (needed once the nx workspace exists)", required=False))

    # Codex — the execution plane
    if not which("codex") and args.fix and which("npm"):
        print("[fix ] installing @openai/codex ...")
        run_quiet(["npm", "install", "-g", "@openai/codex"])
    codex = which("codex")
    if codex:
        code, out = run_quiet([codex, "login", "status"])
        logged_in = code == 0 and "not logged in" not in out.lower()
        checks.append(_check("codex CLI + login", logged_in, out.splitlines()[-1] if out else "unknown",
                             "`codex login` (ChatGPT subscription or API key — login is always manual)"))
    else:
        checks.append(_check("codex CLI + login", False, "not on PATH",
                             "`npm install -g @openai/codex` then `codex login` — or rerun with --fix"))

    # Claude Code — the coordination plane
    claude_bin = which("claude")
    checks.append(_check(
        "claude CLI", claude_bin is not None, claude_bin or "not on PATH",
        "https://claude.ai/code — install Claude Code"))

    def install_claude_plugin(marketplace_url: str, plugin_ref: str) -> None:
        run_quiet([claude_bin, "plugin", "marketplace", "add", marketplace_url])
        run_quiet([claude_bin, "plugin", "install", plugin_ref])

    plugin = home / ".claude" / "plugins" / "cache" / "openai-codex" / "codex"
    if not plugin.is_dir() and args.fix and claude_bin:
        print("[fix ] installing codex-plugin-cc ...")
        install_claude_plugin("https://github.com/openai/codex-plugin-cc", "codex@openai-codex")
    checks.append(_check(
        "codex-plugin-cc", plugin.is_dir(), str(plugin) if plugin.is_dir() else "not installed",
        "`claude plugin marketplace add https://github.com/openai/codex-plugin-cc && "
        "claude plugin install codex@openai-codex` — or rerun with --fix "
        "(leave the review gate disabled)"))

    # Skills
    gstack = home / ".claude" / "skills" / "gstack"
    if not gstack.is_dir() and args.fix:
        print("[fix ] installing gstack ...")
        code, _ = run_quiet(["git", "clone", "--depth", "1",
                             "https://github.com/garrytan/gstack.git", str(gstack)])
        if code == 0 and (gstack / "setup").exists():
            run_quiet([str(gstack / "setup")])  # best-effort; skills work from clone
    checks.append(_check(
        "gstack skills", gstack.is_dir(), str(gstack) if gstack.is_dir() else "not installed",
        "`git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && ~/.claude/skills/gstack/setup` "
        "(needed for /office-hours discovery) — or rerun with --fix"))
    autoreview = home / ".codex" / "skills" / "autoreview"
    if not autoreview.is_dir() and args.fix:
        print("[fix ] installing autoreview ...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = run_quiet(["git", "clone", "--depth", "1",
                                 "https://github.com/openclaw/agent-skills.git", tmp + "/as"])
            src = Path(tmp) / "as" / "skills" / "autoreview"
            if code == 0 and src.is_dir():
                shutil.copytree(src, autoreview)
    checks.append(_check(
        "autoreview skill", autoreview.is_dir(), str(autoreview) if autoreview.is_dir() else "not installed",
        "clone https://github.com/openclaw/agent-skills and copy skills/autoreview to "
        "~/.codex/skills/ — or rerun with --fix (escalation-tier review; see harness.yaml)",
        required=False))
    # Skill packs installed via the `skills` CLI; the sentinel dir marks presence.
    skill_packs = [
        ("mattpocock skills", "mattpocock/skills", ["--all"],
         home / ".claude" / "skills" / "ask-matt"),
        ("anthropic frontend-design", "anthropics/skills",
         ["-s", "frontend-design", "-a", "*", "-y"],
         home / ".claude" / "skills" / "frontend-design"),
    ]
    for name, repo, extra, sentinel in skill_packs:
        if not sentinel.is_dir() and args.fix and which("npx"):
            print(f"[fix ] installing {repo} ...")
            run_quiet(["npx", "-y", "skills", "add", repo, "-g", "--copy", *extra])
        checks.append(_check(
            name, sentinel.is_dir(),
            "installed" if sentinel.is_dir() else "not installed",
            f"`npx -y skills add {repo} -g --copy {' '.join(extra)}` — or rerun with --fix",
            required=False))
    ponytail_cache = home / ".claude" / "plugins" / "cache"

    def ponytail_ok() -> bool:
        return ponytail_cache.is_dir() and any(ponytail_cache.glob("*ponytail*"))

    if not ponytail_ok() and args.fix and claude_bin:
        print("[fix ] installing ponytail ...")
        install_claude_plugin("https://github.com/DietrichGebert/ponytail", "ponytail@ponytail")
    checks.append(_check(
        "ponytail plugin", ponytail_ok(),
        "installed" if ponytail_ok() else "not installed",
        "`claude plugin marketplace add https://github.com/DietrichGebert/ponytail && "
        "claude plugin install ponytail@ponytail` — or rerun with --fix "
        "(prototype phase 0b only — see harness.yaml)",
        required=False))

    width = max(len(c["name"]) for c in checks)
    failures = 0
    for c in checks:
        mark = "OK " if c["ok"] else ("MISS" if c["required"] else "opt ")
        print(f"[{mark}] {c['name']:<{width}}  {c['detail']}")
        if not c["ok"]:
            print(f"       fix: {c['fix']}")
            if c["required"]:
                failures += 1
    if failures:
        print(f"\nforge doctor: {failures} required tool(s) missing.")
        raise SystemExit(1)
    print("\nforge doctor: ready. Next: forge.py init --name <project> --target <dir>")
