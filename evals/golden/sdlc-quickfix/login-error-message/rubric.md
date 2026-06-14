# Rubric: sdlc-quickfix / login-error-message

Grader evaluates the produced `quickfix-<ts>.md` and the promoted `spec.md`. Deterministic subset in `checks.json`.

## quickfix-<timestamp>.md

| Check | Pass criteria |
|-------|---------------|
| Delta format used | Has `## Requirements Delta` with `### ADDED` / `### MODIFIED` / `### REMOVED` headings |
| Scope stayed small | 1–3 requirement changes total; no new `US-*` user stories invented |
| No multi-story inflation | The change is expressed as a delta to REQ-014, not a fresh feature spec |
| Canonical EARS | Any new/changed requirement uses canonical EARS (no ALWAYS/AS/UNLESS) |
| Rule tie-in noted | Rules Compliance section references RULE-002 |
| Key-namespaced | References use `AUTH:` (e.g. `covers AUTH:REQ-014`) |
| Dated filename | File is `quickfix-<ISO-8601-ish timestamp>.md` |

## spec.md (after default promotion)

| Check | Pass criteria |
|-------|---------------|
| Promoted by default | REQ-014's text is updated in `spec.md` (promotion is the default, not opt-in) |
| Error Handling updated | The 500 body is now a friendly message, not "stack trace" |
| ID preserved | REQ-014 keeps its ID (not renumbered) |

## Cross-file

| Check | Pass criteria |
|-------|---------------|
| Quickfix record kept | The dated `quickfix-*.md` is retained even after promotion |
| Validator clean | `sdlc-validate.py --feature user-authentication` shows no EARS warnings or dangling tags for the changed requirement |
