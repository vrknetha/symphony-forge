"""Close refuses a changed screen file that breaks the owner's code-visible design rules."""
from pathlib import Path

import pytest

from test_close import CLEAN, GREEN, env
from test_polish_parts import _new_app, _read
from test_score_notes import _client_repo as setup_client

STORY = "FIX-OWNER-UI-RULES"
pytestmark = pytest.mark.platform
ROOT = Path(__file__).resolve().parents[1]
SCREEN, CARD = "apps/web/src/owner-rules.tsx", "apps/web/src/card.css"

# One screen line for each way to break a rule, and lines that look close but are not styling:
# link targets, words in text, a delay, a toast time and a theme value.
BAD = [
    ("bold-text", '<p className="font-semibold">a</p>'),
    ("bold-text", "<p style={{ fontWeight: 650 }}>a</p>"),
    ("all-caps", '<p className={cn("text-xs", "uppercase")}>a</p>'),
    ("all-caps", '<p style={{ textTransform: "uppercase" }}>a</p>'),
    ("bg-gradient", '<p className="bg-gradient-to-r from-a to-b">a</p>'),
    ("bg-gradient", '<p style={{ background: "linear-gradient(red, blue)" }}>a</p>'),
    ("raw-hex", '<p style={{ color: "#fff" }}>a</p>'),
    ("raw-hex", '<p className="bg-[#1d4ed8]">a</p>'),
    ("slow-motion", '<p className="duration-300">a</p>'),
    ("slow-motion", '<p style={{ transition: "opacity 400ms ease" }}>a</p>'),
    ("slow-motion", "el.animate(frames, { duration: 500 });"),
]
GOOD = [
    '<p className="font-medium" style={{ fontWeight: 500 }}>a</p>',
    "<p>Use an uppercase letter</p>",
    '<input placeholder="Needs an uppercase letter" />',
    '<a href="#feed">Order #1234</a>',
    '<p style={{ transition: "opacity 150ms ease 500ms" }}>a</p>',
    'toast("Saved", { duration: 4000 });',
]
# Not screens: a design canvas, an email template, a shadcn copy; and a theme value, where hex belongs.
NOT_SCREENS = {
    "docs/design/FIX-OWNER-UI-RULES/src/canvas.html": '<p style="font-weight: 600">Canvas</p>\n',
    "apps/api/templates/email/receipt.html":
        '<p style="font-weight: 700; color: #fff; text-transform: uppercase">Receipt</p>\n',
    "libs/shared/ui/src/components/ui/owner-rules.tsx": '<p className="font-bold">Copy</p>\n',
    "apps/web/src/theme.css": ":root { --brand: #1d4ed8; }\n.dark { --brand: #60a5fa; }\n",
}
STARTER = ROOT / "src/forge/templates/starter/apps/web/src"
WAIVERS = "".join(f"/* forge-ui-ignore {rule}: Brand mark */\n" for rule in dict(BAD))


def test_1_close_refuses_a_changed_screen_with_bold_caps_gradient_hex_or_slow_motion(
    env, tmp_path, monkeypatch,
):
    setup_client(env, tmp_path, False)
    monkeypatch.setenv("IMPECCABLE_HOME", str(tmp_path / "impeccable-home"))
    monkeypatch.setenv("IMPECCABLE_LAUNCHER_PROBE", "1")
    monkeypatch.delenv("IMPECCABLE_BIN", raising=False)
    starter = {f"apps/web/src/{p.name}": p.read_text("utf-8") for p in STARTER.iterdir()}
    item, where = env.start(
        "owner-rules", "fix/owner-rules", ".factory/fixes/owner-rules.json",
        {"kind": "fix", "why": "Keep screens on the owner's design rules",
         "allow_large": "The test owner allows one fixture with every kind of file",
         "done_when": "Changed screens follow the owner's design rules"},
        {**starter, **NOT_SCREENS, CARD: ".card { --accent: #fff; }\n",
         SCREEN: "".join(f"{line}\n" for _, line in BAD + [("", line) for line in GOOD])},
    )
    env.checks(GREEN)
    env.reviews(CLEAN)
    refused = env.close(item)
    output = refused.stdout + refused.stderr
    assert refused.returncode == 1, output
    for number, (rule, _) in enumerate(BAD, 1):
        assert f"{SCREEN}:{number} {rule}:" in output, (number, rule)
        assert f"forge-ui-ignore {rule}: <reason>" in output
    assert f"{CARD}:1 raw-hex:" in output  # a custom property outside the theme rules
    # Nothing else is named: not the screen's other lines, and not a file that is no screen.
    assert output.count(f"{SCREEN}:") == len(BAD), output
    for name in (*NOT_SCREENS, *starter):
        assert name not in output, name

    # A comment with a reason sets each rule aside; the card's own comment sets its rule aside.
    env.commit(where, CARD, "/* forge-ui-ignore raw-hex: Brand mark */\n.card { --accent: #fff; }\n")
    env.commit(where, SCREEN, WAIVERS + "".join(f"{line}\n" for _, line in BAD + [("", g) for g in GOOD]))
    waived = env.close(item)
    assert waived.returncode == 0, waived.stdout + waived.stderr


BASELINE = {
    "Never:": [
        "Gradients. (checked)", "Glow.", "Icons in rounded boxes.", "All caps. (checked)",
        "Eyebrow labels.", "Nested cards.", "Decorative pills.",
        "Bold text: regular and medium weights only. (checked)",
    ],
    "Always:": [
        "Sentence case everywhere.", "Semantic tokens, never a hex value outside the theme. (checked)",
        "Shadows only on things that float.", "Motion under 300 ms. (checked)", "No bounce.",
        "Check the screen at 390 px width.", "Check the screen in dark mode.",
        "Check the screen with the keyboard.",
    ],
}


def test_2_the_app_baseline_lists_the_owners_design_rules(repo, gh, tmp_path):
    client = _new_app(repo, gh, tmp_path, ("--starter",))
    for host in (".claude", ".codex"):
        text = _read(client / host / "skills/app-baseline/SKILL.md")
        section = text.partition("## Owner's design rules")[2].partition("\n## ")[0]
        never, _, always = section.partition("\nAlways:")
        listed = {"Never:": never.partition("\nNever:")[2], "Always:": always}
        for heading, rules in BASELINE.items():
            assert [line[2:] for line in listed[heading].splitlines() if line.startswith("- ")] == rules, (
                host, heading)
