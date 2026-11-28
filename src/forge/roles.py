"""Forge's subagent roles for both hosts, from forge.toml and the host's built-in defaults.

A Codex role whose kind's model belongs to the other family inherits the session's model.
Claude planning uses grill, diagnostics use Sonnet at high effort, and implementation uses its worker settings.
Roles set no tools or permission mode: they inherit the session's.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from forge import repo

REFUSALS = {
    "foreign_role": ("{path} is a role of your own that Forge didn't write, and forge sync writes a "
                     "role of that name; rename or delete your file, then sync again.", "forge sync"),
}

MARK = "Forge writes this role with forge sync from forge.toml's [models]; change forge.toml, not this file."
BUILD = ("Build the bounded task you were handed, in this checkout and nothing more. Follow the repo's "
         "AGENTS.md rules and the standards page. Write the end-to-end test first and watch it fail, "
         "then take the smallest change that makes it pass. A file outside the task's Scope that the "
         "change needs you may change; name it and why in your handoff. Stop only for a one-way step, "
         "a security question or a new moving part. Run tests in the foreground, commit your own work "
         "with a short plain-English message, and never commit to the default branch, skip the git "
         "hooks, push or merge.")
READ_ONLY = ("Change no files: report what you found with exact paths, symbols and evidence, and "
             "leave the change to a building role.")
# role: (kind, description, instructions)
ROLES = {
    "worker": ("build", "Builds a bounded Forge task or fix end to end.", BUILD),
    "coder": ("build", "Builds server-side APIs, data and business logic for a bounded task.",
              BUILD + " Trace every caller of what you change and keep validation and error handling."),
    "fixer": ("lite", "Builds a bounded Forge fix end to end.", BUILD),
    "frontend": ("design", "Builds frontend screens and interaction for a bounded task.",
                 BUILD + " Keep keyboard access, labels and contrast, and handle loading, error and "
                         "empty states."),
    "tester": ("build", "Writes and fixes automated tests for a bounded task.",
               BUILD + " Test behaviour at the boundary the user touches, never internals, and never "
                       "weaken a test to hide a defect."),
    "refactorer": ("build", "Makes behaviour-preserving refactors for a bounded task.",
                   BUILD + " Keep behaviour and validation exactly as they are; the existing tests "
                           "must pass unchanged."),
    "explorer": ("explore", "Explores the codebase and traces dependencies without changing files.",
                 "Answer the question you were handed by reading the repo. " + READ_ONLY),
    "reader": ("grill", "Cold reads a plan for blocking defects without changing files.",
               "Cold read the plan you were handed against the repo rules and standards. Report "
               "only blocking defects with distinct text and new evidence; do not repeat settled "
               "findings. If there are none, return exactly No findings. " + READ_ONLY),
    "planner": ("design", "Turns an approved story into bounded tasks with their tests.",
                "Split the approved story into the fewest tasks that each prove Done-when items end "
                "to end, naming each task's Scope and tests. Plan in plain English. " + READ_ONLY),
    "architect": ("design", "Weighs design choices against the repo's decisions and standards.",
                  "Give one recommendation, its reason and how sure you are, choosing the fewest "
                  "moving parts that meet Done-when, and name any new moving part. " + READ_ONLY),
    "debugger": ("review", "Finds the root cause of a hard failure.",
                 "Reproduce the failure, then trace it to a confirmed root cause and the smallest "
                 "fix, with the test that would fail without it. " + READ_ONLY),
    "security": ("review", "Checks trust boundaries, validation, permissions and secrets.",
                 "Check where input enters, that every data access checks permission, and that "
                 "secrets and personal data stay out of code and logs; state the evidence and the "
                 "smallest safe change. " + READ_ONLY),
    "performance": ("review", "Measures performance problems and finds the smallest fix.",
                    "Measure before you claim, find the cause, and propose the smallest correct "
                    "change with the measurement that proves it. " + READ_ONLY),
}


def model_family(model: str) -> str:
    if model.startswith("gemini"):
        return "antigravity"
    return "claude" if re.match(r"claude|opus|sonnet|haiku|fable", model) else "codex"


def _earlier_builder(item: str, family: str) -> bool:
    """Find past worker choices in Git, since each round replaces the worker in the state."""
    from forge.story import json_of

    top, path = repo.root(), repo.state_path(item)
    branches = [f"task/{item.replace('/', '-')}"] if "/" in item else [f"fix/{item}", f"forge/{item}"]
    refs = [f"refs/heads/{branch}" for branch in branches]
    tips = repo.blob_texts(top, [f"{ref}:{path}" for ref in refs])
    for ref in refs:
        if json_of(tips.get(f"{ref}:{path}")).get("branch") != ref.removeprefix("refs/heads/"):
            continue
        commits = repo.git("log", "--full-history", "--format=%H", ref, "--", path, cwd=top)
        snapshots = repo.blob_texts(top, [f"{sha}:{path}" for sha in commits.splitlines()])
        return any(json_of(text).get("worker") == family for text in snapshots.values())
    return False


def review_family(cfg: dict[str, Any], built_by: str | None, item: str) -> str:
    """Select this repo's reviewer and keep a family from reviewing its own build."""
    selected = cfg.get("reviews")
    codex_bin = os.environ.get("CODEX_BIN") or "codex"
    if not selected and cfg["tools"] == "both":
        return "codex" if shutil.which(codex_bin) else "claude"
    family = selected or cfg["tools"]
    name = {"claude": "Claude Code", "codex": "Codex", "antigravity": "Antigravity"}[family]
    if selected and built_by and (family == built_by or _earlier_builder(item, family)):
        repo.refuse((f"{name} built {item}, so Forge will not let {name} review it.",
                     "ask the owner, then set reviews in forge.local.toml to another family"))
    if family == "antigravity":
        from forge import antigravity
        if message := antigravity.problem():
            repo.refuse((message, antigravity.INSTALL))
    elif not shutil.which(codex_bin if family == "codex" else "claude"):
        if not selected:
            repo.refuse(repo.REFUSALS["tool_missing"], tool=family, name=name)
        repo.refuse(repo.REFUSALS["missing_tool"], tool=name)
    return family


def read_family(cfg: dict[str, Any], here: str, recorded: str) -> tuple[str, bool]:
    from forge import claude_sdk, codex

    configured = cfg.get("reviews")
    if configured == "antigravity":
        return configured, False
    installed = {"claude": here == "claude" or not claude_sdk.sdk_problem(),
                 "codex": here == "codex" or codex.installed()}
    gone = recorded in installed and not installed[recorded]
    other = "claude" if here == "codex" else "codex"
    # Both keeps the earlier reader while it is installed.
    reader = (cfg["tools"] if cfg["tools"] != "both" else
              recorded if recorded in installed and not gone else other if installed[other] else here)
    return configured or reader, gone


def _chosen(cfg: dict[str, Any], kind: str, family: str, building: bool = False) -> tuple[str, str]:
    """(model, effort) for a role on this host; "" leaves it out so the session's own applies."""
    models = cfg.get("models", {})
    if building and kind == "design":  # the frontend role builds on the design model
        entry = repo.design_models(cfg, family)
        return entry["model"], "max" if family == "claude" and entry["effort"] == "ultra" else entry["effort"]
    if kind == "explore":
        entry = repo.worker_models(cfg, kind, family)
        effort = entry["effort"]
        return entry["model"], "max" if family == "claude" and effort == "ultra" else effort
    if family == "claude":
        entry = (repo.CLAUDE_GRILL_DEFAULT if kind == "review" else
                 repo.models(cfg, "grill", family) if kind in ("design", "grill") else
                 repo.worker_models(cfg, kind, family))
        effort = entry.get("effort", "")
        return entry.get("model", ""), "max" if effort == "ultra" else effort
    if kind == "review" and kind not in models:
        entry = repo.DESIGN_DEFAULTS[family]
        return entry["model"], entry["effort"]
    # A kind with no entry for this family gets none: the role inherits the session's settings.
    entry = models.get(kind, {})
    per_family = kind == "design" or any(host in entry for host in repo.FAMILIES)
    if per_family:
        entry = entry.get(family, {})
    model, effort = entry.get("model", ""), entry.get("effort", "")
    # A per-family entry is already the host's own; a single entry names one model for both hosts.
    return (model if model and (per_family or model_family(model) == family) else ""), effort


def subagent_defaults(cfg: dict[str, Any]) -> dict[str, str]:
    """The Codex build subagent budget, falling back to lite when build leaves it out."""
    for kind in ("build", "lite"):
        entry = repo.models(cfg, kind, "codex")
        if entry.get("subagents"):
            return {"model": entry["subagents"], "effort": entry["subagent_effort"]}
    return {}


def ships(top: Path, cfg: dict[str, Any]) -> dict[str, str]:
    wanted = {}
    for name, (kind, description, instructions) in ROLES.items():
        building = instructions.startswith(BUILD)
        model, effort = _chosen(cfg, kind, "codex", building)
        if name in ("worker", "fixer") and not model:  # the built-in model forge work names
            model, effort = repo.worker_models(cfg, kind, "codex").values()
        if building and (budget := subagent_defaults(cfg)):
            model, effort = budget["model"], budget["effort"]
        wanted[f".codex/agents/{name}.toml"] = "".join([
            f"# {MARK}\n", f"name = {json.dumps(name)}\n", f"description = {json.dumps(description)}\n",
            f"model = {json.dumps(model)}\n" * bool(model),
            f"model_reasoning_effort = {json.dumps(effort)}\n" * bool(effort),
            f"developer_instructions = {json.dumps(instructions)}\n"])
        model, effort = _chosen(cfg, kind, "claude", building)
        wanted[f".claude/agents/{name}.md"] = "".join([
            f"---\n# {MARK}\n", f"name: {name}\n", f"description: {json.dumps(description)}\n",
            # Quoted, so no value from forge.toml can add a line such as tools to the frontmatter.
            f"model: {json.dumps(model)}\n" * bool(model),
            f"effort: {json.dumps(effort)}\n" * bool(effort),
            f"---\n\n{instructions}\n"])
    return wanted


def refuse_foreign(top: Path, rels: list[str]) -> None:
    """Refuse before sync writes anything when it would overwrite a role file Forge didn't write."""
    for rel in rels:
        path = top / rel
        if rel.startswith((".codex/agents/", ".claude/agents/")) and path.is_file() and MARK not in (
                path.read_text(encoding="utf-8")):
            repo.refuse(REFUSALS["foreign_role"], path=rel)
