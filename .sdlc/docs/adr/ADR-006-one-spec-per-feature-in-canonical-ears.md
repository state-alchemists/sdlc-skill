# ADR-006: One spec.md per feature, in canonical uppercase EARS

## Status
Accepted

## Context
Split requirements/design/test-plan files, as in Kiro and the earlier layout here, drift apart, and the implementer and reviewer must hunt across them. Free-prose requirements cannot be checked for testability. The earlier dialect (`ALWAYS SHALL`, `UNLESS`, state-driven `WHERE`) was not canonical EARS.

## Decision
One `.sdlc/specs/<slug>/spec.md` holds requirements, design and the `## Test Plan`. Requirements use canonical EARS (Mavin et al.) with **uppercase** keywords. Only uppercase counts as a keyword, so "as" and "unless" in ordinary prose never misfire. The validator warns on the deprecated dialect, lowercase keywords, several SHALLs in one requirement, a missing subject, non-EARS openers and unverifiable words. Headings are matched by meaning, and `config.json` can rename them.

## Consequences
### Positive
- One file is the whole contract for implementation and review.
- Requirement shape is machine-checkable.
### Negative
- EARS checks are warnings, and they check shape, not meaning.
- Legacy `test-plan.md` files are still read as a fallback until `/sdlc-adopt` folds them into the spec.

## Implements Rules
None — this decision is orthogonal to current rules.

## Verification
- `tests/test_sdlc_validate.py`: `case_canonical_ears_is_not_flagged_as_deprecated`, `case_canonical_composite_where_if_then_is_not_deprecated`, `case_lowercase_shall_is_flagged`, `case_compound_requirement_is_flagged`, `case_folded_test_plan_ids_are_valid_targets`, `case_legacy_test_plan_ids_are_valid_targets`, `case_renamed_test_plan_heading_still_resolves`.

## References
- `.sdlc/CONVENTIONS.md` § Canonical EARS dialect
