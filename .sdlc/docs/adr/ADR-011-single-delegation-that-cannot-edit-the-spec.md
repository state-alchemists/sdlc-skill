# ADR-011: Implementation is one delegation that may not edit the spec

## Status
Accepted

## Context
Kiro and Spec Kit break implementation into a `tasks.md` with per-task state. That adds an artifact to keep current and invites drift from the spec. Separately, `/sdlc-implement` once told its sub-agent to treat validator errors as failures to fix, inside a retry loop. The cheapest "fix" for `trace-code` was to delete the requirement.

## Decision
- One coherent feature is one coding session. `/sdlc-implement` delegates the whole feature to a single sub-agent.
- The prompt passes file **paths**, not contents. Only `rules.md` is inlined, because it is small and mandatory.
- At most 2 retries, each with the specific failure. Every retry fixes code, never the spec.
- The sub-agent must not modify anything under `.sdlc/`. The orchestrator verifies this with `git diff --name-only -- .sdlc/` and reverts any violation.

## Consequences
### Positive
- Context stays small, and the spec stays the fixed contract the review measures against.
### Negative
- Nothing on disk records progress, so an interrupted run restarts from `git status`.
- A feature too big for one session must be split at `/sdlc-spec` time (about 3–10 `REQ-*`).

## Implements Rules
None — this decision is orthogonal to current rules.

## Verification
- `tests/test_skill_prompts.py`: `case_implement_forbids_editing_the_spec`.

## References
- `skills/sdlc-implement/SKILL.md` · `.sdlc/docs/product.md` § Alternatives & Positioning
