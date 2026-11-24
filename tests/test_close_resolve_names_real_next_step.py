"""A choice recorded outside a stopped review loop is refused with the next step forge next gives."""
STORY = "resolve-refusal-next-step"

from test_close import blocked, env, finding  # noqa: F401
from test_close_holds_after_three_blocked_reviews import client_item


def next_line(env, text):
    return [line for line in text.splitlines() if line.startswith("Next:")][-1]


def test_1_open_findings_below_the_limit_send_the_item_back_to_work(env, tmp_path):
    item, where = client_item(env, tmp_path, False)
    env.commit(where, "app.py", "print('round 1')\n")
    env.reviews(blocked(finding("P1", "First defect", "app.py")))
    assert env.close(item).returncode == 1
    refused = env.close(item, "--resolve", "split", "--reason", "Split it")
    assert refused.returncode == 1
    assert "review stopped at the round limit" in refused.stderr and "stuck worker loop" in refused.stderr
    assert next_line(env, refused.stderr) == f"Next: forge work {item}"
    assert next_line(env, env.repo.forge("next", cwd=where).stdout) == f"Next: forge work {item}"


def test_2_an_unreviewed_item_is_sent_to_close(env, tmp_path):
    item, where = client_item(env, tmp_path, False)
    env.commit(where, "app.py", "print('built')\n")
    refused = env.close(item, "--resolve", "accept", "--reason", "Accept it")
    assert refused.returncode == 1
    assert next_line(env, refused.stderr) == f"Next: forge close {item}"


def test_3_a_repeated_choice_is_refused_as_already_recorded(env, tmp_path):
    item, where = client_item(env, tmp_path, False)
    for number in (1, 2):
        env.commit(where, "app.py", f"print('round {number}')\n")
        env.reviews(blocked({**finding("P1", "Defect", "app.py"),
                             "body": "Gain 4, Work 1, Harm 2\nNormal saves lose work."}))
        assert env.close(item).returncode == 1
    reason = "The owner wants one more round"
    assert env.close(item, "--resolve", "more", "--reason", reason).returncode == 0
    again = env.close(item, "--resolve", "more", "--reason", reason)
    assert again.returncode == 1
    assert "already recorded" in again.stderr
    step = next_line(env, again.stderr)
    assert "--resolve" not in step
    assert step == next_line(env, env.repo.forge("next", cwd=where).stdout)
