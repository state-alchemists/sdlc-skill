# ADR-002: Traceability tags live in source and test comments

## Status
Accepted

## Context
Accountability means showing which code serves which requirement. Spec Kit's V-Model extension and the OpenFastTrace lineage store that link in a matrix or manifest beside the code. A matrix has to be regenerated and merged, and it can drift from the code without anyone noticing.

## Decision
The link lives in the code itself:
- Source files carry `IMPLEMENTS: KEY:REQ-001`.
- Test files carry `COVERS: KEY:REQ-002, KEY:UT-005`.
- The function that fulfils a requirement carries `@sdlc KEY:REQ-003`.

The validator reads these back and fails the build in both directions: a requirement with no implementation or test, a tag pointing at nothing, and a requirement citing an `AC-*` the problem brief does not define. An AC that no requirement cites is reported as INFO, not failed: it is usually backlog not yet specified.

## Consequences
### Positive
- A reviewer reading `file:line` sees the same claim the gate checks. No generated artifact can disagree with the code.
- Git merges tags like any other code.
### Negative
- Tags are unversioned: reword a requirement and its old tags still pass. Re-checking meaning is left to `/sdlc-review` and the drift report.
- Every tagged file gains header lines that must respect each language's syntax, which is why `ANNOTATION.md` exists.

## Implements Rules
- RULE-008 — The repository passes its own gate

## Verification
- `tests/test_sdlc_validate.py`: `case_unknown_ac_citation_errors`, `case_acceptance_criterion_no_requirement_cites_is_reported`, `case_planned_test_that_nothing_covers_warns`, `case_requirement_mentioning_a_removed_thing_stays_active`.

## References
- `.sdlc/docs/product.md` § Alternatives & Positioning
