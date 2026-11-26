# Review separates severity, merge status and proof that comes after merge

2 parts · Risks: none one-way; two accepted limits · New moving parts: none

## What changes for you

- When a Done-when item needs proof that exists only after the merge (for example the full CI run on the main branch, or a nightly report), the review no longer raises a blocking "Not done" finding. It shows the item as "pending after merge", with the check to run and who owns it. The finding does not block the merge. It stays visible in the close output and in the pull request. (Source: the owner's choice, 26 Nov 2026)
- A later review of the same item does not raise that pending check again as new work. It never counts as another blocking round. Proof that Forge already recorded for the same commit is reused and not asked for again. (Source: the owner's choice, 26 Nov 2026)
- A finding now shows its own severity (P0, P1, and so on) and, separately, whether it blocks the merge. A finding that only crosses the score threshold no longer shows as P0. A real P0, a failed required pull request check and a serious defect still block the merge. (Source: the owner's choice, 26 Nov 2026)
- The Harm floor for migrations applies only when the change adds or edits a migration. A finding that only mentions an old migration keeps the Harm score the reviewer gave it. The floors for security and data loss do not change. (Source: the owner's choice, 26 Nov 2026)
- What each repo gets: a new repo gets all of this from its first review. An existing repo gets it when it upgrades to the release that has this story. No setting changes, no command is added, and saved reviews stay as they are.

Design: none (no screen changes)

## Why

An audit of 981 reviews over 267 items (13 to 26 Nov 2026) found a median of 3 reviews per item and 156 items past two rounds. Of 43 blocking findings checked, 17 were real bugs. Two asked for proof that can exist only after the merge, such as the main branch's full CI run. Today the review raises these as a blocking P0 "Not done", and the close step refuses to clear one by dismissal. Clients rewrite the Done-when to get past it.

The severity shown was also wrong. Any finding past the blocking score threshold is shown as P0, so a pending acceptance check looks like harm to users. A finding that only cited an old migration got "Harm 4, floor: migration", though the change added no migration. This story fixes these two problems. Grouping repeated findings across repair rounds, the split between new and old defects, and three small quirks are not in this story.

## Done when

1. **A check that can run only after the merge shows as "pending after merge", with the check to run and its owner, in the close output and the pull request, and it does not block the merge.**
2. **A later review of the same item does not raise the pending check again as new work, so it adds no blocking round and cannot stop the item at the round limit.**
3. **A blocking finding shows its own severity next to "blocks the merge", so a finding no longer shows as P0 only because it blocks, while a real P0 still shows as P0 and blocks.**
4. **The migration Harm floor applies only when the change adds or edits a migration; a finding that only cites an old migration keeps its reviewer's Harm score.**
5. **A new repo and an existing repo on upgrade get the same behavior, and no saved review needs conversion.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- The reviewer decides that a check can exist only after the merge. Forge does not verify it. A reviewer that still reports "Not done" gets today's behavior: the finding blocks, and the owner can amend the Done-when. The review prompt limits the new label to evidence that cannot exist before the merge, and the pending check stays visible in the pull request.
- Forge does not track a pending check after the merge. The pull request is the record. Someone must run the check and read the result.

## For the builders

### Done-when details

1. The reviewer titles the finding `After merge: <the Done-when item>` and writes `Check: <what to run or read>` and `Owner: <who>` in its body (`src/forge/templates/review.md`, next to the existing paragraph about a pull request check that has not finished, around line 281). `noise.drop` in `src/forge/noise.py` (called at `src/forge/review.py:1061`, after repair findings) gives such a finding priority P2 and `follow_up` "Pending after merge", whatever priority or score it came with, so `score.holds` is false and it never enters `review.blocking`. The text `Not done` is not used for it, so `bound_review` does not mark it `required_done_when`. Close's output and the pull request block (`_block`) list each one under a `Pending after merge:` heading outside the folded section, with its Check and Owner; with no Owner line the entry says "owner not named". Tests (new `tests/test_review_pending_after_merge.py`, run through `forge close` with the stubbed reviewer and GitHub on a new repo): a reviewer finding `After merge: Main's full CI run passes` at P0, Harm 5, with Check and Owner lines gives a clean review, close reaches Ready, the pull request body lists the check and owner outside the fold, and `forge hook pr-check` does not say "blocked by serious findings". A `Not done:` finding on the same Done-when still blocks (existing `test_close_explains_findings_and_requires_done_when.py` case 2 stays).
2. The pending finding keeps its normal identity (title and file), so the settled-finding carry in `review._settled` shows it again in the next round without a new blocking count: the follow-up path already does this for `follow_up` findings. Proof already recorded for the same commit is reused by close's existing saved-review and passed-test reuse (`review.passed_record`, the unchanged-diff `fresh` check in `close.py`); no new code is planned for it. Test in the new file: with `task_review_rounds = 1`, a first close raises a blocking finding and the pending check; a repair commit and a second close show the pending check again, the item is not stopped at the round limit because of it, and a close on an unchanged commit makes no second review call.
3. `score.priority` stays as it is for the stop rules (the same P0 after two worker rounds, the round limit, the history ceilings). Add `score.severity(finding)`, which returns the reviewer's own `priority`, and use it at the four places that show a priority: `close.py` lines 448 and 456, `_block` (line 1122) and `review_skip.py:64`. The serious list in close prints `P1, blocks the merge`. The pull request line keeps its existing `blocks the merge` note next to the severity. The review prompt's Scores section says that the score bar decides whether a finding blocks, and that the priority is the user's severity. Tests (new `tests/test_review_severity_and_migration_floor.py`, through `forge close`): a P1 finding scored Gain 4, Harm 4 shows `P1` and `blocks the merge` in the output and the pull request body, never `P0`; a finding the reviewer calls P0 shows `P0` and blocks.
4. `score.normalise` gets a keyword `migration` (default true, so the cold read of a plan keeps the floor: the plan's proposed change is the risk). `autoreview._finding` passes false. A new `autoreview.migration_floor(findings, tree, start, head)` runs `normalise` with the floor on again for every finding when `git diff --name-only start head` has a path with a `migrations` segment or an `alembic/versions` pair of segments (the glob `migration_warnings.added` already uses for `migrations`). `review.py` calls it once, right after `autoreview.attempt` returns (around line 1003, where `tree`, the start commit and `head` are known). Tests in the new file: a fix whose diff has no migration file and a finding titled "The preference duration is stored wrongly" that cites an old SQL migration in its body, scored Harm 1, keeps `Harm 1` and has no `(floor: migration)`; the same finding on a fix that adds `migrations/0002_duration.sql` shows `Harm 4 (floor: migration)`. Change the case in `tests/test_score_notes.py` (line 108) so its fix adds a migration file. The cold-read case in the same file (line 124) stays.
5. No record format changes: a saved review keeps its fields, and the new labels come from the title prefix and the existing priority and follow_up fields. The suite's one upgrade test is not extended. The new tests run on a new repo only, as the review rule says.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| SEVERITY | Severity shown apart from merge status; migration floor only for migration changes | `score.severity` shown in close and the pull request; `normalise` migration keyword and `autoreview.migration_floor`; `_block` moved out of `close.py` | 3, 4, 5 | `src/forge/score.py`, `src/forge/autoreview.py`, `src/forge/review.py`, `src/forge/close.py`, `src/forge/pr_block.py` (new), `src/forge/review_skip.py`, `src/forge/templates/review.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_review_severity_and_migration_floor.py` (new); changed: `tests/test_score_notes.py` | | no | |
| PENDING | Proof that comes after merge shows as pending and does not block | `After merge:` findings are non-blocking and listed in close and the pull request with check and owner | 1, 2 | `src/forge/noise.py`, `src/forge/pr_block.py`, `src/forge/close.py`, `src/forge/templates/review.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_review_pending_after_merge.py` (new) | SEVERITY | no | |

New moving parts: none

## Notes

- Module sizes (the ceiling is 1,200 lines, `test_5_forge_stays_small`): `close.py` has 1,199 lines and `review.py` has 1,200. SEVERITY moves `_block` (about 40 lines, used once at `close.py:974`) from `close.py` into the new `src/forge/pr_block.py`, so close.py has room; PENDING adds its pending list in `pr_block.py`. `review.py` takes one added call and must end at 1,200 lines or fewer: the builder removes or moves a block of the same size and says which. New logic goes in `score.py` (194 lines), `autoreview.py` (254), `noise.py` (62) and `pr_block.py`.
- Review rule (a change to what a coordinator, worker or reviewer does updates the skill or brief): SEVERITY and PENDING both update `templates/review.md` (the migration floor and Scores text; the `After merge:` rule), `templates/skill.md` and `templates/brief.md` (how a blocking finding is shown, and that a pending check does not block and is run by its owner), and the two synced skill copies.
- Guesses to confirm with the owner. (1) "Reuse valid proof from the same build" is read as the reuse Forge already does for one commit: a saved review and a passed test record. The story adds a test, not new code, for it. If the owner meant fetching the main branch's CI result from GitHub for the same commit and clearing the pending check, that is a separate, larger change. (2) "Visible" means close's output and the pull request, not the board. (3) "User severity" is the reviewer's own priority, with the Gain, Work and Harm line shown beside it as today. (4) A change "carries migration risk" when its diff touches a `migrations` folder or an `alembic/versions` folder.
- Out of scope, by the owner's choice on 26 Nov 2026: grouping repeated variants across repair rounds, defects that existed before the change against ones it introduced, and the three small quirks.
