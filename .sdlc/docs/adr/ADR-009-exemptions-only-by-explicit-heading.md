# ADR-009: Coverage exemptions only by explicit, separate headings

## Status
Accepted

## Context
Some requirements cannot carry an in-code check, such as a backup policy or production paging. An earlier rule exempted an NFR when its "Validated By" cell contained words like `process` or `manual`. Those are ordinary English, so "load test in the checkout process" silently exempted a real test.

## Decision
Only a heading exempts:
- `## NFRs Validated Outside Code` exempts `NFR-*` only. A `REQ-*` placed under it is a WARNING, not an exemption.
- `## Requirements With No In-Code Verification` exempts `REQ-*`. It is a separate heading because exempting what the code exists *for* is a bigger claim, and one shared heading would let a `REQ-*` be exempted just by moving its line. The two heading patterns must never both match one heading.

Every exempted requirement is reported as `outside-code` on every run. The exemptions are independent of the role gate in [ADR-004](ADR-004-tags-count-only-in-real-comments-in-the-right-file.md).

## Consequences
### Positive
- Every exemption is explicit, easy to grep for in review, and visible in each report.
### Negative
- A project with no tests at all has no project-wide off switch. Its requirements stay red until they get a check or a declared exemption.

## Implements Rules
- RULE-003 — A regression case per fix

## Verification
- `tests/test_sdlc_validate.py`: `case_nfr_row_wording_alone_does_not_exempt`, `case_requirement_under_the_nfr_heading_warns_and_does_not_exempt`, `case_functional_and_nfr_exemption_headings_are_disjoint`, `case_the_exemption_is_independent_of_the_role_gate`, `case_functional_exemption_holds_under_a_relaxed_gate`.

## References
- `.sdlc/CONVENTIONS.md` § Requirements validated outside code
