"""The review block in a pull request body."""
from __future__ import annotations

from typing import Any

from forge import review_skip, score

BEGIN, END = "<!-- forge:begin -->", "<!-- forge:end -->"


def render(result: dict[str, Any], check: str) -> str:
    """Forge's block in the pull request body: the open blocking findings plainly first, or one
    `Review: clean` line, then the dismissed and advisory findings folded away, then the worker's
    functional check from its commit message. Each finding is a bullet naming its --dismiss number
    in text, since GitHub renumbers an ordered list."""
    because = {d["finding"]: d for d in result["dismissals"]}
    blocking, rest, below = [], [], {"follow-up": [], "live with": []}
    for n, finding in enumerate(result["findings"], 1):
        outcome = "follow-up" if finding.get("follow_up") else score.bar(score.of(finding))
        scores = score.of(finding)
        line = "Gain {}, Work {}, Harm {}".format(*scores) if scores else ""
        is_blocking = n not in because and (
            finding.get("required_done_when") or score.holds(finding, result.get("blocking_level")))
        note = (f"dismissed because {because[n]['because']}"
                + (" (evidence from the base)" if because[n].get("from_base") else "")
                if n in because
                else "blocks the merge" if is_blocking
                else finding.get("follow_up") or line if outcome in below
                else "advisory: " + " ".join(score.strip(finding.get("body", "")).split()))
        note += f"; {line}" if line and note != line else ""
        (blocking if is_blocking else below[outcome] if n not in because and outcome in below
         else rest).append(f"- Finding {n} ({score.severity(finding)}): {finding['title']} "
                           f"({finding['file']}:{finding['line']}): {note}")
    if result.get("skipped"):
        lines = [BEGIN, f"Review: {review_skip.label(result, reason=True)}."]
    elif result["status"] == "reviewing":
        lines = [BEGIN, "Review: running; CI is running alongside it."]
    elif result["status"] == "blocked":
        lines = [BEGIN, "The review found serious problems.", "", *blocking]
    else:
        lines = [BEGIN, f"Review: clean, {len(because)} dismissed, {len(rest) - len(because) + sum(map(len, below.values()))} advice."]
    folded = [*rest, *[line for name, title in (("follow-up", "Follow-ups:"), ("live with", "Lived with:"))
                       if below[name] for line in ("", title, *below[name])]]
    folded = folded[1:] if folded[:1] == [""] else folded
    if folded:
        lines += ["", "<details>", "<summary>Dismissed and advisory findings</summary>", "", *folded,
                  "", "</details>"]
    return "\n".join([*lines, *(["", check] if check else []), END])
