---
name: sdlc-spec
description: Generate feature specification and test plan. Produces a single spec.md (requirements + design) and test-plan.md per feature.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-spec

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Produces a feature specification (EARS requirements + design in one file) and a structured test plan. Formerly three separate skills (`sdlc-spec` + `sdlc-test-plan`), now one session — the test plan is a structural derivative of the spec and requires no new domain knowledge.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-spec <free-text>`. Use the user's text verbatim as `{feature}` — the directory name for `.sdlc/specs/{feature}/`. Do not normalize, slug, or transform it. If no argument was given, ask: "What's the feature name? I'll use it as the directory name under `.sdlc/specs/`."
- **Approval**: write only after an explicit affirmative ("yes" / "ok" / "approved"). Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/requirements/problem-brief.md` does not exist, stop and ask the user to run `/sdlc-requirements` first.
- **ID stability is load-bearing**: `REQ-*` and `NFR-*` IDs are referenced by source-file headers (`IMPLEMENTS: REQ-003`), test headers (`COVERS: REQ-003`), and inline tags (`@sdlc REQ-003`). On a re-run that updates an existing spec:
  - Continue numbering from the highest existing REQ-* / NFR-* ID. Never renumber or recycle IDs.
  - If a requirement is dropped, leave the ID retired (do not reuse) and add a one-line note: `REQ-NNN: REMOVED ({date}) — {reason}`.
  - For substantive updates to an existing ID, follow the same MODIFIED-with-rationale pattern used by `sdlc-quickfix`.
- **EARS dialect**: use the keyword table below. It is close to but not identical to canonical EARS (e.g. we use `AS` for conditional where canonical EARS uses `IF`). When in doubt, prefer this skill's table over external references.
- **Spec is one file**: `.sdlc/specs/{feature}/spec.md` merges what were previously `requirements.md` and `design.md`. The implementer and reviewer read one source of truth.
- **Test naming**: read `.sdlc/docs/test-strategy.md` and follow its convention. If unspecified, default to the project-language idiom: `test_<function>_<condition>_<expected>` for pytest, `describe('X', () => it('does Y'))` for JS, `TestFooBar` for Go, `#[test] fn foo_does_bar` for Rust, etc. State the chosen convention at the top of the test plan.
- **Property-based tests are conditional**: include PBTs only if `.sdlc/docs/test-strategy.md` or `.sdlc/docs/tech.md` names a property-testing tool (hypothesis, fast-check, proptest, gopter, etc.). Otherwise mark the PBT section `N/A — no property-testing framework configured` and continue.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if present) — requirements must encode rule compliance where relevant; refuse to generate a requirement that would force a rule violation
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/architecture.md`, `.sdlc/docs/adr/*.md`
- `.sdlc/requirements/entity-dictionary.md`, `.sdlc/requirements/problem-brief.md`
- `.sdlc/docs/test-strategy.md` — for test naming convention and PBT tooling

### Phase 2: EARS Requirements

Use these EARS keywords within requirement text (the categories are a thinking aid for you; the output is a flat numbered list):

| Keyword | Pattern | When |
|---------|---------|------|
| WHEN `<t>` THEN SHALL `<r>` | Event-driven | On user action or system event |
| WHERE `<s>` THEN SHALL `<b>` | State-driven | While in a particular state |
| AS `<c>` THEN SHALL `<b>` | Conditional | When condition is true |
| UNLESS `<b>` THEN SHALL `<d>` | Exception | Default with exception |
| ALWAYS SHALL `<i>` | Invariant | System-wide constant |
| SHALL `<m>` | Mandatory | Fallback |

### Phase 3: Design Properties (Think, Don't Write)

Before drafting the spec, silently consider which correctness properties apply to this feature. This is a completeness check for you, the spec writer — the output only lists properties that are actually relevant.

| Property | When it applies | When to skip |
|----------|-----------------|--------------|
| Round-Trip | Data is serialized/deserialized (encode/decode, save/load) | Read-only operations, logging |
| Uniqueness | Identifiers, constraints, deduplication | Stateless transformations |
| Atomicity | Multi-step writes, transactions | Read-only endpoints, idempotent single-writes |
| Validation | External input enters the system | Internal-only calls, already-validated data |
| Idempotency | Operations that clients may retry | Inherently non-idempotent operations (login, payment capture) |

List only the properties that apply — do not emit `N/A` rows for properties that don't.

### Phase 4: Generate the Spec

#### Template: .sdlc/specs/{feature}/spec.md

```markdown
# Feature Spec: {{FEATURE_NAME}}

## Requirements

*Requirements cite the source `AC-*` from the problem brief. Use the EARS keywords in the text — the reader can see whether a requirement is event-driven, invariant, etc. from the keyword, no category headers needed.*

- `REQ-001` (AC-NNN): WHEN {{trigger}} THEN SHALL {{response}}
- `REQ-002` (AC-NNN): ALWAYS SHALL {{invariant}}
- `REQ-003` (AC-NNN): UNLESS {{exception}} THEN SHALL {{default}}
- ...

## Non-Functional Requirements

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-001 | {{NFR}} | {{Target}} | {{code / test / infra / CI / manual}} |

## NFRs Validated Outside Code
- `NFR-NNN`: {{NFR}} — validated by {{mechanism, e.g. terraform module / WAF rule / SLO dashboard}}

## API Surface

*List every endpoint, method, and shape. Use real HTTP status codes, real field names.*

| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| {{M}} | {{P}} | {{R}} | {{S}} | {{A}} |

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| {{Condition}} | {{Status}} | {{Response body shape}} |

## Correctness

*Only the properties from the Phase 3 checklist that actually apply. No N/A rows.*

- **{{Property}}:** {{What the system guarantees and how it's enforced.}}
- ...

## Entities

See `.sdlc/requirements/entity-dictionary.md` — {{EntityA}} ({{key fields}}), {{EntityB}} ({{key fields}}).

### Entity Modifications
*If this feature requires adding fields or changing existing definitions, do NOT silently encode them here. Either stop and ask the user to run `/sdlc-requirements` first, or — with explicit user opt-in — update `.sdlc/requirements/entity-dictionary.md` in this session (following the merge rules of `sdlc-requirements`), then continue.*

- {{Entity}}.{{field}}: ADDED / MODIFIED / REMOVED — {{reason}}, mirrored in `.sdlc/requirements/entity-dictionary.md`.
```

### Phase 5: Test Plan

After the spec is approved, generate the test plan in the same session. The test plan is a structural mapping of the spec — no new domain knowledge is required.

Read `.sdlc/docs/test-strategy.md` for naming conventions and tooling before generating.

#### Template: .sdlc/tests/{feature}/test-plan.md

```markdown
# Test Plan: {{FEATURE_NAME}}

*Test naming convention: {{chosen convention, e.g. pytest `test_<fn>_<condition>_<expected>`}}*

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
*Include only if `.sdlc/docs/test-strategy.md` or `.sdlc/docs/tech.md` names a property-testing tool. Otherwise: `N/A — no property-testing framework configured`.*

| ID | Invariant | Property | Generator |
|----|-----------|----------|-----------|
| PBT-001 | {{invariant}} | {{property}} | {{generator}} |

## Design Property Coverage
*Only the properties listed in the spec's Correctness section. No N/A rows.*

| Property | Covered By | Notes |
|----------|------------|-------|
| {{Property}} | {{UT-/IT-/PBT- ids}} | {{notes}} |

## Test Data Strategy
- **Fixtures**: {{Where fixtures live, naming convention}}
- **Synthetic data**: {{How generated, seed strategy for property-based tests}}
- **Cleanup**: {{How state is reset between tests}}
```

### Phase 6: Validation

Before writing the test plan, check:

- Every `REQ-*` from the spec appears in at least one row's `Req` column (use `grep -o 'REQ-[0-9]\+' .sdlc/specs/{feature}/spec.md` to enumerate, then verify each is referenced in the plan).
- Every `NFR-*` is either covered by a test row or listed under "NFRs Validated Outside Code" with the validation mechanism named.
- Every correctness property from the spec's Correctness section appears in the Design Property Coverage table.
- Test names follow the convention chosen and declared at the top of the plan.
- PBT section is either populated **or** explicitly marked `N/A — no property-testing framework configured`.

Present the test plan to the user for approval before writing.

## Phase Transition

Once `.sdlc/specs/{feature}/spec.md` and `.sdlc/tests/{feature}/test-plan.md` are written and approved, this skill is done. **Do not invoke `/sdlc-implement` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Spec and test plan are complete for `{feature}`: `.sdlc/specs/{feature}/spec.md` and `.sdlc/tests/{feature}/test-plan.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-implement {feature}` to generate code and tests.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
- List `.sdlc/specs/{feature}/` and `.sdlc/tests/{feature}/` to see what was written
- Resume from the first missing document

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `spec.md` | `{root}/.sdlc/specs/{feature}/` | Merged EARS requirements + design (API surface, errors, correctness) |
| `test-plan.md` | `{root}/.sdlc/tests/{feature}/` | Test plan at all levels (unit, integration, E2E, PBT) |
