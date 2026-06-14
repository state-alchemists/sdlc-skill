# Rubric: sdlc-spec / email-verification

Grader evaluates `.sdlc/specs/email-verification/spec.md` and `.sdlc/tests/email-verification/test-plan.md`. Deterministic subset in `checks.json`.

## spec.md

| Check | Pass criteria |
|-------|---------------|
| Feature Key declared | A `**Feature Key:**` line with an uppercase token |
| Slug correct | File lives at `.sdlc/specs/email-verification/spec.md` (slugified, no spaces) |
| REQs cite ACs | Every `REQ-*` cites a source `AC-0NN` from the brief (AC-021..AC-024) |
| Canonical EARS only | Every requirement uses WHEN / WHILE / WHERE / IF…THEN / ubiquitous SHALL |
| No deprecated dialect | No `ALWAYS SHALL`, no `AS … THEN`, no `UNLESS` |
| NFRs cited not invented | NFR IDs match the brief (NFR-009, NFR-010); none invented |
| Outside-code NFR placed | NFR-010 (deliverability dashboard) is under "NFRs Validated Outside Code" |
| Correctness: no N/A rows | Correctness section lists only applicable properties (expect Uniqueness + Validation + Idempotency for token reuse), no `N/A` rows |
| Rule compliance encoded | A requirement or note reflects RULE-004 (never log raw tokens) |

## test-plan.md

| Check | Pass criteria |
|-------|---------------|
| Feature Key declared | Matches spec.md's key |
| Every REQ mapped | Each `REQ-*` appears in at least one test row's `Req` column |
| PBT populated | Because `hypothesis` is configured, a Property-Based Tests section has ≥1 row (NOT marked N/A) |
| Naming convention stated | A test-naming convention line is present |
| Design property coverage | Each correctness property from the spec appears in the coverage table |

## Cross-file

| Check | Pass criteria |
|-------|---------------|
| Validator clean on IDs/EARS | `sdlc-validate.py --feature email-verification` reports no EARS warnings and no duplicate/recycled IDs (code-coverage ERRORs are expected pre-implementation) |
