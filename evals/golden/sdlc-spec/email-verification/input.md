# Input: sdlc-spec / email-verification

## Initial state
Existing project (auth already specified). User runs `/sdlc-spec email verification` in a fresh chat. The slug becomes `email-verification`.

## Files the skill reads

### .sdlc/requirements/problem-brief.md (excerpt)
```
## User Stories
- `US-007`: As a new user, I want to verify my email so that my account is trusted.

## Acceptance Criteria
- [ ] `AC-021` (US-007): On signup, a verification email with a single-use token is sent within 30s.
- [ ] `AC-022` (US-007): Clicking a valid, unexpired token marks the email verified.
- [ ] `AC-023` (US-007): An expired or reused token is rejected with a clear error.
- [ ] `AC-024` (US-007): Unverified users cannot access protected resources.

## Non-Functional Requirements
- `NFR-009`: Verification tokens expire after 24h.
- `NFR-010`: Verification email delivery is monitored (deliverability dashboard).
```

### .sdlc/requirements/entity-dictionary.md (excerpt)
```
### User
| Field | Type | Constraints | Description |
| email_verified | bool | default false | Whether the email was confirmed |
### VerificationToken
| Field | Type | Constraints | Description |
| token | string | unique, indexed | Single-use token |
| user_id | UUID | FK User | Owner |
| expires_at | datetime | required | Expiry timestamp |
```

### .sdlc/rules.md (excerpt)
```
### RULE-004 — Never log raw tokens
Statement: NEVER write a verification token value to any log sink.
### RULE-007 — Structured logging only
```

### .sdlc/docs/tech.md (excerpt)
```
## Property-Based Testing
- hypothesis
```

## Expected behaviour
The skill declares a Feature Key (e.g. `EMAILVERIFY`), writes `.sdlc/specs/email-verification/spec.md` (canonical EARS, REQs citing AC-021..AC-024, NFR-009/010 cited from the brief), and `.sdlc/tests/email-verification/test-plan.md` mapping every REQ to tests. Because `hypothesis` is configured, a Property-Based Tests section is populated (e.g. token single-use / round-trip). NFR-010 is listed under "NFRs Validated Outside Code" (deliverability dashboard).
