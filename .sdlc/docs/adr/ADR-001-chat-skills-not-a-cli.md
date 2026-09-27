# ADR-001: Chat skills are the interface, not a CLI

## Status
Accepted

## Context
The workflow is interviews, judgement calls and approvals. A CLI can do none of that, and a chat can. More than thirty AI coding tools now load `SKILL.md` files from `~/.<tool>/skills/`, but no two of them expose tools, sub-agents or permission gates the same way.

## Decision
The product is seven Markdown skills (`skills/sdlc-*/SKILL.md`). They describe **what** to do (read this, ask that, wait for approval, delegate this prompt), never **which** tool to call. Only three things run in a shell: the installer, the validator and the eval runner. Skills never call one another: each ends with a paste-ready action block, and the user starts the next phase.

## Consequences
### Positive
- One copy runs under zrb, Claude Code, Codex, Gemini, Copilot, OpenCode and the rest.
- There is no second surface to keep in step with the chat.
### Negative
- Approval tiers are instructions the model follows, not enforced gates.
- Nothing enforces the session discipline ("review in a fresh session"); the user has to remember it.
- Behaviour depends on the host model, and only the evals ([ADR-012](ADR-012-deterministic-evals.md)) can catch a regression.

## Implements Rules
None — this decision is orthogonal to current rules.

## Verification
- `tests/test_skill_prompts.py`: `case_no_skill_hardcodes_the_source_or_test_layout`, `case_every_transition_is_an_action_block`.
- `tests/test_install.sh`: "targets the documented skills directories".

## References
- `README.md` § Runtime compatibility · `.sdlc/docs/product.md` § Out of Scope
