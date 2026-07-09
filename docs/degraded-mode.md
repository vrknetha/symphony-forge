# Degraded Mode

Use this when `codex-plugin-cc` is unavailable. The coordinator is thinner, but the artifacts and gates do not change.

## Exploration

Ask read-only questions directly:

```bash
codex exec -s read-only "What files implement the billing workflow, and what tests cover it?"
```

## Implementation

Run Codex with the implementer prompt plus the bounded task text:

```bash
codex exec "$(cat .agents/prompts/implementer.md)

Task:
Implement the approved leaf task from .factory/decomposition.json."
```

## Testing and Review

Use the existing specialist agents and record their JSON outputs:

```bash
python3 .agents/scripts/record_test_from_json.py --kind automated --input /tmp/automated.json
python3 .agents/scripts/verify.py
python3 .agents/scripts/record_review_from_json.py --aspect quality --input /tmp/quality.json
python3 .agents/scripts/record_review_from_json.py --aspect performance --input /tmp/performance.json
python3 .agents/scripts/record_review_from_json.py --aspect security --input /tmp/security.json
python3 .agents/scripts/record_test_from_json.py --kind functional --input /tmp/functional.json
python3 .agents/scripts/pr_ready.py
```

## Gates

Discovery and prototype stay lightweight. Before planning, record accepted client sign-off:

```bash
python3 .agents/scripts/record_signoff.py
```

After that, keep the normal `.factory` artifacts and run the same gates. Do not bypass `verify.py`, review artifacts, or `pr_ready.py`.
