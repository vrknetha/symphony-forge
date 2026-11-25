"""Accepting a stopped review goes on to checks even when close replays the branch."""
import json

from test_close import STORY_DOC, blocked, env, finding  # noqa: F401
from test_hotspot_stop import saved, seed

STORY = "abb-neon-accept"


def test_1_accept_skips_replayed_review_and_reaches_checks(env):
    config = (env.repo.path / "forge.toml").read_text("utf-8")
    env.commit(env.repo.path, "forge.toml", "task_review_rounds = 1\n" + config)
    env.repo.git("push", "-q", "origin", "main")
    seed(env, "src/a.py")
    item, where = env.start_approved_task(STORY_DOC)
    base = env.repo.git("rev-parse", "origin/main", cwd=where)
    story, task_name = item.split("/")
    state_path = where / f".factory/stories/{story}/tasks/{task_name}.json"
    state = json.loads(state_path.read_text("utf-8"))
    state.update(stacked_on="SHOP/T0", base=base)
    env.commit(where, state_path.relative_to(where).as_posix(), json.dumps(state, indent=2) + "\n")
    env.commit(where, "app.py", "print(1)\n")
    env.commit(where, "src/a.py", "pass\npass  # defect\n")
    defect = {**finding("P1", "Remaining defect", "src/a.py", line=2),
              "body": "Gain 4, Work 1, Harm 2\nNormal saves lose the basket."}
    env.reviews(blocked(defect))
    stopped = env.close(item)
    assert stopped.returncode == 1, stopped.stdout + stopped.stderr
    assert saved(where, item)["status"] == "hotspot"

    # Simulate the parent task merging to main with a non-conflicting change to a reviewed file.
    env.commit(env.repo.path, ".factory/stories/SHOP/tasks/T0.json",
               json.dumps({"status": "merged"}) + "\n", "Merge SHOP/T0")
    env.commit(env.repo.path, "src/a.py", "pass  # parent\npass\n", "Parent change to src/a.py")
    env.repo.git("push", "-q", "origin", "main")
    before = len(env.review_calls())
    replay_defect = {**finding("P1", "Replayed defect", "src/a.py", line=3),
                     "body": "Gain 4, Work 1, Harm 2\nNormal saves lose the basket."}
    env.reviews(blocked(replay_defect))
    accepted = env.close(item, "--resolve", "accept", "--reason", "Owner accepts the remaining risk")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert "Ready:" in accepted.stdout
    assert "One more round, split or accept?" not in accepted.stderr
    assert len(env.review_calls()) == before
