# Input: sdlc-quickfix / login-error-message

## Initial state
`user-authentication` is already specified and implemented. The user runs
`/sdlc-quickfix user-authentication` and describes a one-line change:

> "When login hits an unexpected 500, show a friendly 'Something went wrong, please try again' message instead of leaking the stack trace. Just that."

This is the canonical small change: a single behaviour tweak that the full
spec→implement→review pipeline would bloat into a multi-story spec.

## Files the skill reads

### .sdlc/specs/user-authentication/spec.md (excerpt)
```
**Feature Key:** AUTH

## Requirements
- `REQ-001` (AC-001): WHEN a user submits valid credentials, the system SHALL issue a session token.
- `REQ-014` (AC-018): IF login raises an unhandled error, THEN the system SHALL return HTTP 500.

## Error Handling
| Condition | Status | Body |
| Unhandled login error | 500 | (stack trace) |
```

### .sdlc/rules.md (excerpt)
```
### RULE-002 — Never leak candidate content in client-facing errors
Statement: NEVER include raw content or stack traces in client-facing errors.
```

## Expected behaviour
The skill confirms the scope is tiny (1 requirement modified, no new feature),
writes a dated `quickfix-<ts>.md` with an `ADDED/MODIFIED/REMOVED` delta
(MODIFY REQ-014 so the 500 body is a friendly message, not a stack trace; this
also closes a RULE-002 gap), implements the delta with key-namespaced tags,
runs the suite + validator, and **promotes the delta into spec.md by default**.
It must NOT expand the change into multiple user stories.
