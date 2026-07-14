---
status: proposed
confirmed_by: ""
date: 2026-07-14
---

# Implementation model: gpt-5.6-luna at xhigh reasoning

## Context

Implementation was pinned to gpt-5.5 at medium reasoning. OpenAI's GPT-5.6
family (Sol/Terra/Luna) ships a fast, cost-efficient tier — Luna
(gpt-5.6-luna) — supporting the full reasoning ladder up to xhigh. Factory
implementation tasks arrive bounded: approved plan, acceptance criteria,
one review package.

## Decision

Implementation (/codex:rescue) runs gpt-5.6-luna at xhigh reasoning
(.codex/config.toml). Non-bounded work (migrations, cross-domain,
ambiguous failures) is reported back and escalated to a stronger tier
instead of ground out on the fast tier.

## Consequences

- Cheap tier + deep effort on well-specified tasks; cost drops without a
  quality drop where the plan is tight.
- The escalation path is behavioral (implementer reports back), not
  automatic — watch fix-after-review rates in retro for drift.
- Other agents (planner-high, docs-decomposer, functional-checker) keep
  their per-agent pins; this changes only the implementation default.
