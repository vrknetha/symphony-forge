# Factory State

This directory stores machine-readable run state for the Codex/OpenClaw factory.

Tracked artifacts:
- `run.json` — current issue, phase, branch, PR, and status
- `verify.json` — deterministic verification results
- `reviews/*.json` — quality, performance, and security review outputs
- `tool-history.jsonl` — shell command history recorded by hooks

Commit durable artifacts when they describe the feature run. Do not commit transient local debug output.
