---
name: sdlc-test-plan
description: Generate test plans from feature specifications. Produces structured test plans covering unit, integration, E2E, and property-based tests per feature.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-test-plan

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Transforms feature specifications (EARS requirements + design) into structured test plans.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-test-plan <free-text>`. Use it verbatim as `{feature}`. If missing, ask.
- **Approval**: write only after an explicit affirmative ("yes" / "ok" / "approved"). Silence or vague replies are change requests.
- **Required input missing**: if `specs/{feature}/requirements.md` or `specs/{feature}/design.md` is missing, stop and ask the user to run `/sdlc-spec {feature}` first.
- **Test naming**: read `docs/test-strategy.md` and follow its convention. If unspecified, default to the project-language idiom: `test_<function>_<condition>_<expected>` for pytest, `describe('X', () => it('does Y'))` for JS, `TestFooBar` for Go, `#[test] fn foo_does_bar` for Rust, etc. State the chosen convention at the top of the test plan.
- **Property-based tests are conditional**: include PBTs only if `docs/test-strategy.md` or `docs/tech.md` names a property-testing tool (hypothesis, fast-check, proptest, gopter, etc.). Otherwise mark the PBT section `N/A — no property-testing framework configured` and continue.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if present) — add tests that detect violations of any RULE-* relevant to this feature
- `specs/{feature}/requirements.md` — EARS requirements
- `specs/{feature}/design.md` — design with correctness properties
- `docs/test-strategy.md` — test strategy and CI gates

### Phase 2: Test Plan Generation

Generate a test plan with four sections:

- **Unit Tests**: Map each EARS requirement to at least one test. Cover edge cases for each correctness property.
- **Integration Tests**: Test component boundaries, API endpoints, database operations.
- **End-to-End Tests**: Map to user stories, cover critical user journeys.
- **Property-Based Tests**: Invariants from ALWAYS SHALL, idempotency checks, round-trip tests.

#### Template: tests/{feature}/test-plan.md

```markdown
# Test Plan: {{FEATURE_NAME}}

## Unit Tests
| ID | Req | Test Name | Input | Expected |
|----|-----|-----------|-------|----------|
| UT-001 | REQ-{{N}} | test_{{cmp}}_{{cond}} | {{input}} | {{expected}} |
| UT-002 | REQ-{{N}} | test_{{cmp}}_{{edge}} | {{input}} | {{expected}} |

## Integration Tests
| ID | Scope | Test Name | Setup | Assertion |
|----|-------|-----------|-------|-----------|
| IT-001 | {{boundary}} | test_{{b}}_{{beh}} | {{setup}} | {{assert}} |

## End-to-End Tests
| ID | Story | Scenario | Steps | Expected |
|----|-------|----------|-------|----------|
| E2E-001 | {{story}} | {{scenario}} | {{steps}} | {{outcome}} |

## Property-Based Tests
| ID | Invariant | Property | Generator |
|----|-----------|----------|-----------|
| PBT-001 | {{invariant}} | {{property}} | {{generator}} |

## Design Property Coverage
Map each design.md correctness property to the tests that cover it. Mark `N/A` if the design declared it not applicable.

| Property | Covered By | Notes |
|----------|------------|-------|
| Round-Trip | {{UT-/IT-/PBT- ids}} | {{notes}} |
| Uniqueness | {{ids}} | {{notes}} |
| Atomicity | {{ids}} | {{notes}} |
| Validation | {{ids}} | {{notes}} |
| Idempotency | {{ids}} | {{notes}} |

## Test Data Strategy
- **Fixtures**: {{Where fixtures live, naming convention}}
- **Synthetic data**: {{How generated, seed strategy for property-based tests}}
- **Cleanup**: {{How state is reset between tests}}
```

### Phase 3: Validation

Check:
- Every `REQ-*` from `specs/{feature}/requirements.md` appears in at least one row's `Req` column (use `grep -o 'REQ-[0-9]\+' specs/{feature}/requirements.md` to enumerate, then verify each is referenced in the plan).
- Every `NFR-*` is either covered by a test row or listed under "NFRs Validated Outside Code" with the validation mechanism named.
- Every correctness property from `design.md` appears in the Design Property Coverage table (or is marked N/A with reason).
- Test names follow the convention chosen in the Conventions block above (declared at the top of the plan).
- PBT section is either populated **or** explicitly marked `N/A — no property-testing framework configured`.

Present the test plan to the user for approval before writing.

## Phase Transition

Once `tests/{feature}/test-plan.md` is written and approved, this skill is done. **Do not invoke `/sdlc-implement` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Test plan is complete for `{feature}`: `tests/{feature}/test-plan.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-implement {feature}` to generate code and tests.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted: list `tests/{feature}/` to check if the test plan was written, then resume from the missing artifact.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `test-plan.md` | `{root}/tests/{feature}/` | Test plan with all levels |