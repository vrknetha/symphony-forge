"""A design part's redraw changes only the plan's Design tree id; that keeps the approval."""
import json
import re
from pathlib import Path

from test_design_first import SVG, _publish_default
from test_setup import _fresh_client
from test_worker import install_claude
from test_story import DOC, claude_plan, hook, new_story, setup

STORY = "design-redraw-keeps-approval"


def test_1_design_redraw_keeps_the_approval(repo, gh, tmp_path, claude_payload):
    client, made = _fresh_client(repo, gh, tmp_path)
    assert made.returncode == 0, made.stdout + made.stderr
    repo.path = client
    repo.git("switch", "-qc", "fix/design-settings")
    repo.write(".factory/fixes/design-settings.json", json.dumps({
        "kind": "fix", "branch": "fix/design-settings", "why": "Set design settings",
        "done_when": "Settings are ready"}))
    setup(repo, kind="client", keys=("SHOP",))
    repo.write("forge.toml", (repo.path / "forge.toml").read_text("utf-8")
               + 'checks = ["tests", "forge-pr-check"]\n')
    assert repo.forge("sync").returncode == 0
    repo.git("add", "-A")
    if repo.git("diff", "--cached", "--name-only"):
        repo.git("commit", "-qm", "Install the design renderer")
    _publish_default(repo, repo.git("remote", "get-url", "origin"))
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "--ff-only", "fix/design-settings")
    shop = new_story(repo, "SHOP")
    doc = shop / "plans/SHOP.md"
    folder = shop / "docs/design/SHOP"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "basket.svg").write_text(SVG, encoding="utf-8")

    def tree_id():
        repo.git("add", "docs/design/SHOP", cwd=shop)
        tree = repo.git("write-tree", cwd=shop)
        return repo.git("rev-parse", f"{tree}:docs/design/SHOP", cwd=shop)

    first = tree_id()
    text = "\n".join(line for line in DOC.split("\n") if not line.startswith("Design:"))
    text = text.replace("\n## Why", f"\nDesign: docs/design/SHOP/ ({first})\n\n## Why")
    doc.write_text(text, encoding="utf-8")
    assert repo.forge("read", "SHOP").returncode == 0

    # A redraw before the first approval still needs a new cold read.
    (folder / "basket.svg").write_text(SVG.replace("Basket", "Early"), encoding="utf-8")
    early = text.replace(first, tree_id())
    doc.write_text(early, encoding="utf-8")
    assert "forge read SHOP" in repo.forge("next", cwd=shop).stdout
    doc.write_text(text, encoding="utf-8")
    (folder / "basket.svg").write_text(SVG, encoding="utf-8")
    tree_id()
    assert hook(repo, claude_plan(claude_payload, text)).returncode == 0

    started = repo.forge("task", "start", "SHOP/SAVE")
    assert started.returncode == 0, started.stdout + started.stderr
    task = Path(re.search(r" in (.+)\n", started.stdout)[1])

    def redraw(label, extra=None):
        """The design part redraws the screens in its own checkout and commits the new tree id."""
        (task / "docs/design/SHOP/basket.svg").write_text(SVG.replace("Basket", label), encoding="utf-8")
        repo.git("add", "docs/design/SHOP", cwd=task)
        tree = repo.git("write-tree", cwd=task)
        new = repo.git("rev-parse", f"{tree}:docs/design/SHOP", cwd=task)
        plan = (task / "plans/SHOP.md").read_text(encoding="utf-8").replace(first, new)
        (task / "plans/SHOP.md").write_text(extra(plan) if extra else plan, encoding="utf-8")
        repo.git("add", "-A", cwd=task)
        repo.git("commit", "-qm", "Redraw the basket screens", cwd=task)
        gh.respond("pr", "list", stdout="[]")
        return repo.forge("close", "SHOP/SAVE")

    # A redraw plus another change to the approved text voids the approval.
    closed = redraw("Other", lambda plan: plan.replace("can save a basket and", "can save a basket safely and"))
    assert closed.returncode == 1 and "design folder changed" in closed.stderr.lower(), closed.stdout + closed.stderr
    repo.git("reset", "-q", "--hard", "HEAD~1", cwd=task)

    # A redraw that changes only the tree id closes and keeps the approval and the read.
    closed = redraw("Saved baskets")
    assert "design folder changed" not in closed.stderr.lower(), closed.stdout + closed.stderr
    assert "tree id no longer matches" not in closed.stderr.lower(), closed.stdout + closed.stderr
    recorded = (task / ".factory/stories/SHOP/story.json").read_text(encoding="utf-8")
    assert json.loads(recorded)["approval"]["hash"] != json.loads(
        repo.git("show", "story/SHOP:.factory/stories/SHOP/story.json"))["approval"]["hash"]

    # A follow-up work round and a second close both accept the redraw already kept in the part.
    install_claude(repo)
    config = task / "forge.toml"
    kept = re.sub(r'(?m)^(workers|tools) = .*\n', "", config.read_text("utf-8"))
    config.write_text('tools = "claude"\nworkers = "claude"\n' + kept, encoding="utf-8")
    worked = repo.forge("work", "SHOP/SAVE", cwd=task)
    assert worked.returncode == 0, worked.stdout + worked.stderr
    repo.git("checkout", "forge.toml", cwd=task)
    assert "changed" not in worked.stderr.lower() and "approved one" not in worked.stderr, worked.stdout + worked.stderr
    gh.respond("pr", "list", stdout="[]")
    again = repo.forge("close", "SHOP/SAVE")
    assert "design folder changed" not in again.stderr.lower(), again.stdout + again.stderr
    assert "tree id no longer matches" not in again.stderr.lower(), again.stdout + again.stderr
