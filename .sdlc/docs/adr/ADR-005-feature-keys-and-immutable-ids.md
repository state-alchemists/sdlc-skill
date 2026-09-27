# ADR-005: Feature Keys namespace per-feature IDs; IDs are immutable

## Status
Accepted

## Context
Every feature numbers from `REQ-001`, and features are specified in parallel, sometimes touching the same file. Tags are the durable link ([ADR-002](ADR-002-traceability-lives-in-the-code.md)). Renumbering, or reusing a retired number, would silently repoint every tag in the code.

## Decision
- Each `spec.md` declares a globally unique `**Feature Key:**` (`[A-Z][A-Z0-9_-]*`), and tags are written `KEY:REQ-NNN`. Unkeyed tags warn and do not count.
- Before writing a spec, a session claims its key by creating `.sdlc/keys/<KEY>`. A same-key collision on another branch then shows up as a git add/add conflict.
- IDs are never renumbered or recycled. A requirement is retired **in place**: its text begins `REMOVED (date) — reason`.

## Consequences
### Positive
- `AUTH:REQ-001` and `BILL:REQ-001` can sit in the same file without ambiguity.
- History stays readable in the spec itself.
### Negative
- A brief-level `NFR-001` cited by two features becomes two separate targets, each with its own tags.
- A slug starting with a digit (`2fa`) needs an explicitly declared key.

## Implements Rules
None — this decision is orthogonal to current rules.

## Verification
- `tests/test_sdlc_validate.py`: `case_duplicate_feature_key_errors`, `case_slug_that_cannot_make_a_key_errors`, `case_unkeyed_tag_warns`, `case_genuinely_removed_requirement_is_retired`, `case_removed_requirement_keeping_its_citation_is_retired`, `case_test_plan_row_for_a_removed_requirement_errors`.

## References
- `.sdlc/CONVENTIONS.md` § ID & traceability scheme, § Parallel sessions
