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

- **Argument → slug**: the user invoked `/sdlc-spec <free-text>`. Slugify it for the directory name `.sdlc/specs/<slug>/`: lowercase; spaces/underscores → `-`; drop characters outside `[a-z0-9-]`; collapse repeated `-`; trim leading/trailing `-`. If the slug differs from the raw input, tell the user the slug you'll use. If no argument was given, ask: "What's the feature name?" Slugs are **stable** — once code references `.sdlc/specs/<slug>/`, never rename.
- **Feature Key (ID namespace)**: every `spec.md` declares `**Feature Key:** <KEY>` — an uppercase token `[A-Z][A-Z0-9_-]*`, **globally unique** across all features (the validator enforces this). Default suggestion: the uppercased slug; you may propose a shorter alias (e.g. slug `user-authentication` → key `AUTH`). All traceability tags are key-namespaced (`@sdlc AUTH:REQ-003`) so IDs never collide across features. See `.sdlc/CONVENTIONS.md`.
- **Artifact paths (migration-aware)**: read from `.sdlc/` (canonical); fall back to legacy roots (`docs/`, `requirements/`, `rules.md`, `specs/`) if missing there. Found legacy-only? Read in place, don't create a parallel `.sdlc/` copy, tell the user to run `/sdlc-migrate`.
- **Approval**: spec + test plan are one **Tier-2** batch (present both, write on a single affirmative). **Overwriting an existing `spec.md`** on a re-run is **Tier-1** — present a diff and get an explicit affirmative. Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/requirements/problem-brief.md` (or legacy `requirements/problem-brief.md`) does not exist, stop and ask the user to run `/sdlc-requirements` first.
- **ID stability is load-bearing**: `REQ-*` / `NFR-*` IDs are referenced by source headers (`IMPLEMENTS: AUTH:REQ-003`), test headers (`COVERS: AUTH:REQ-003`), and inline tags (`@sdlc AUTH:REQ-003`). On a re-run that updates an existing spec:
  - Continue numbering from the highest existing REQ-* / NFR-* ID. Never renumber or recycle.
  - If a requirement is dropped, leave the ID retired with a one-line note: `REQ-NNN: REMOVED ({date}) — {reason}`.
  - For substantive updates to an existing ID, follow the MODIFIED-with-rationale pattern used by `sdlc-quickfix`.
- **Canonical EARS** (Mavin et al.) — use the keyword table below; do NOT use the deprecated dialect (`ALWAYS SHALL`, `AS … THEN`, `UNLESS … THEN`, `WHERE`=state). If a re-run reads an old-dialect spec, migrate the touched requirements to canonical form (see `.sdlc/CONVENTIONS.md` for the mapping) and leave untouched ones for `/sdlc-migrate` or a later pass.
- **Spec is one file**: `.sdlc/specs/<slug>/spec.md` merges what were previously `requirements.md` + `design.md`. One source of truth for implementer and reviewer.
- **Test naming**: read the convention from `.sdlc/docs/test-strategy.md`. If unspecified, default to the project-language idiom. State the chosen convention at the top of the test plan.
- **Property-based tests are conditional**: include PBTs only if `.sdlc/docs/test-strategy.md` or `.sdlc/docs/tech.md` names a property-testing tool (hypothesis, fast-check, proptest, gopter, etc.). Otherwise mark the PBT section `N/A — no property-testing framework configured`.

## Workflow

### Phase 1: Input Discovery

Read (canonical path, then legacy fallback):
- `.sdlc/rules.md` (if present) — requirements must encode rule compliance where relevant; refuse to generate a requirement that would force a rule violation
- `.sdlc/CONVENTIONS.md` (if present) — paths, EARS dialect, ID scheme
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/architecture.md`, `.sdlc/docs/adr/*.md`
- `.sdlc/requirements/entity-dictionary.md`, `.sdlc/requirements/problem-brief.md`
- `.sdlc/docs/test-strategy.md` — test naming convention and PBT tooling

Pick or confirm the **Feature Key** now (check existing specs' keys so it's unique).

### Phase 2: EARS Requirements (canonical)

| Pattern | Template | When |
|---------|----------|------|
| Ubiquitous | The `<system>` SHALL `<response>`. | Always-active invariant |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. | On a user action or system event |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. | While in a particular state |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. | Behaviour tied to an optional/configured feature |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. | Error / guard / exception handling |
| Complex | Combine, e.g. WHILE `<state>`, WHEN `<trigger>`, the `<system>` SHALL `<response>`. | Multiple clauses |

The output is a flat numbered list; the keyword shows the reader whether a requirement is event-driven, an invariant, etc. — no category headers needed.

### Phase 3: Design Properties (Think, Don't Write)

Before drafting, silently consider which correctness properties apply. This is a completeness check — the output only lists properties that actually apply.

| Property | When it applies | When to skip |
|----------|-----------------|--------------|
| Round-Trip | Data is serialized/deserialized (encode/decode, save/load) | Read-only operations, logging |
| Uniqueness | Identifiers, constraints, deduplication | Stateless transformations |
| Atomicity | Multi-step writes, transactions | Read-only endpoints, idempotent single-writes |
| Validation | External input enters the system | Internal-only calls, already-validated data |
| Idempotency | Operations clients may retry | Inherently non-idempotent operations (login, payment capture) |

List only the properties that apply — do not emit `N/A` rows.

### Phase 4: Generate the Spec

#### Template: .sdlc/specs/{slug}/spec.md

```markdown
# Feature Spec: {{FEATURE_NAME}}

**Feature Key:** {{KEY}}

## Requirements

*Requirements cite the source `AC-*` from the problem brief. Use the canonical EARS keywords in the text — no category headers needed.*

- `REQ-001` (AC-NNN): WHEN {{trigger}}, the {{system}} SHALL {{response}}.
- `REQ-002` (AC-NNN): The {{system}} SHALL {{invariant}}.
- `REQ-003` (AC-NNN): IF {{condition}}, THEN the {{system}} SHALL {{response}}.
- ...

## Non-Functional Requirements

*NFR IDs come from the problem brief's Non-Functional Requirements section — cite them, don't invent new ones here.*

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-001 | {{NFR}} | {{Target}} | {{code / test / infra / CI / manual}} |

## NFRs Validated Outside Code
*NFRs validated by infra/process, not application code. The validator exempts these from the `IMPLEMENTS:` requirement.*
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
*If this feature requires adding fields or changing existing definitions, do NOT silently encode them here. Either stop and ask the user to run `/sdlc-requirements` first, or — with explicit user opt-in (Tier-1) — update `.sdlc/requirements/entity-dictionary.md` in this session (following the merge rules of `sdlc-requirements`), then continue.*

- {{Entity}}.{{field}}: ADDED / MODIFIED / REMOVED — {{reason}}, mirrored in `.sdlc/requirements/entity-dictionary.md`.
```

### Phase 5: Test Plan

After the spec is approved, generate the test plan in the same session (it's a structural mapping of the spec — no new domain knowledge). Read `.sdlc/docs/test-strategy.md` for naming conventions and tooling first.

#### Template: .sdlc/tests/{slug}/test-plan.md

```markdown
# Test Plan: {{FEATURE_NAME}}

**Feature Key:** {{KEY}}
*Test naming convention: {{chosen convention}}*

## Unit Tests
| ID | Req | Test Name | Input | Expected |
|----|-----|-----------|-------|----------|
| UT-001 | REQ-{{N}} | test_{{cmp}}_{{cond}} | {{input}} | {{expected}} |

## Integration Tests
| ID | Scope | Test Name | Setup | Assertion |
|----|-------|-----------|-------|-----------|
| IT-001 | {{boundary}} | test_{{b}}_{{beh}} | {{setup}} | {{assert}} |

## End-to-End Tests
| ID | Story | Scenario | Steps | Expected |
|----|-------|----------|-------|----------|
| E2E-001 | {{story}} | {{scenario}} | {{steps}} | {{outcome}} |

## Property-Based Tests
*Include only if a property-testing tool is configured. Otherwise: `N/A — no property-testing framework configured`.*

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
- **Synthetic data**: {{How generated, seed strategy}}
- **Cleanup**: {{How state is reset between tests}}
```

### Phase 6: Validation

Before writing the test plan, check:
- Every `REQ-*` from the spec appears in at least one row's `Req` column.
- Every `NFR-*` is either covered by a test row or listed under "NFRs Validated Outside Code".
- Every correctness property from the spec appears in the Design Property Coverage table.
- Test names follow the declared convention.
- PBT section is populated **or** explicitly marked `N/A — no property-testing framework configured`.
- Every requirement uses a canonical EARS keyword (no `ALWAYS`/`AS`/`UNLESS`).

If `.sdlc/tools/sdlc-validate.py` exists, run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` after writing to confirm EARS syntax and ID hygiene (it can't check code coverage yet — no code exists — so expect "no IMPLEMENTS" findings, which `sdlc-implement` will resolve). Present the test plan (Tier-2 batch with the spec) before writing.

## Phase Transition

Once `.sdlc/specs/<slug>/spec.md` and `.sdlc/tests/<slug>/test-plan.md` are written and approved, this skill is done. **Do not invoke `/sdlc-implement` yourself.** Tell the user (paraphrase as needed):

> Spec and test plan are complete for `<slug>` (Feature Key `{{KEY}}`): `.sdlc/specs/<slug>/spec.md` and `.sdlc/tests/<slug>/test-plan.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-implement <slug>`.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
- List `.sdlc/specs/<slug>/` and `.sdlc/tests/<slug>/` to see what was written
- Resume from the first missing document

## Choosing the `<feature>` slice

Features come from the `US-*` user stories in the problem brief — you pick the slice (no automated breakdown).
- **Too small** → use `/sdlc-quickfix` instead.
- **Too big** → EARS sprawls and `sdlc-implement`'s single delegation struggles.
- **Sweet spot** → one user-visible capability, ~3–10 `REQ-*` entries, one coding session.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `spec.md` | `{root}/.sdlc/specs/<slug>/` | Merged EARS requirements + design; declares Feature Key |
| `test-plan.md` | `{root}/.sdlc/tests/<slug>/` | Test plan at all levels (unit, integration, E2E, PBT) |
