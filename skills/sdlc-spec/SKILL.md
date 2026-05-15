---
name: sdlc-spec
description: Generate feature specifications in EARS format with design docs. Produces requirements.md and design.md per feature.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-spec

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Produces detailed feature specifications using EARS (Easy Approach to Requirements Syntax). Each feature gets two documents: requirements (EARS) and design (correctness properties).

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-spec <free-text>`. Use the user's text verbatim as `{feature}` — the directory name for `specs/{feature}/`. Do not normalize, slug, or transform it. If no argument was given, ask: "What's the feature name? I'll use it as the directory name under `specs/`."
- **Approval**: write only after an explicit affirmative ("yes" / "ok" / "approved"). Silence or vague replies are change requests.
- **Required input missing**: if `requirements/problem-brief.md` does not exist, stop and ask the user to run `/sdlc-requirements` first.
- **ID stability is load-bearing**: `REQ-*` and `NFR-*` IDs are referenced by source-file headers (`IMPLEMENTS: REQ-003`), test headers (`COVERS: REQ-003`), and inline tags (`@sdlc REQ-003`). On a re-run that updates an existing `specs/{feature}/requirements.md`:
  - Continue numbering from the highest existing REQ-* / NFR-* ID. Never renumber or recycle IDs.
  - If a requirement is dropped, leave the ID retired (do not reuse) and add a one-line note: `REQ-NNN: REMOVED ({date}) — {reason}`.
  - For substantive updates to an existing ID, follow the same MODIFIED-with-rationale pattern used by `sdlc-quickfix`.
- **EARS dialect**: the keyword table below is this project's working set. It is close to but not identical to canonical EARS (e.g. we use `AS` for conditional where canonical EARS uses `IF`). When in doubt, prefer this skill's table over external references.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if present) — EARS requirements must encode rule compliance where relevant; refuse to generate a requirement that would force a rule violation
- `docs/product.md`, `docs/tech.md`, `docs/architecture.md`, `docs/adr/*.md`
- `requirements/entity-dictionary.md`, `requirements/problem-brief.md`

### Phase 2: EARS Requirements

Use these EARS keywords:

| Keyword | Pattern | When |
|---------|---------|------|
| WHEN `<t>` THEN SHALL `<r>` | Event-driven | On user action or system event |
| WHERE `<s>` THEN SHALL `<b>` | State-driven | While in a particular state |
| AS `<c>` THEN SHALL `<b>` | Conditional | When condition is true |
| UNLESS `<b>` THEN SHALL `<d>` | Exception | Default with exception |
| ALWAYS SHALL `<i>` | Invariant | System-wide constant |
| SHALL `<m>` | Mandatory | Fallback |

#### Template: specs/{feature}/requirements.md

*The example IDs below (REQ-001…REQ-006, NFR-001) are illustrative, not slots. Use as many requirements per category as the feature needs (including zero). IDs are globally sequential across all categories — a feature may have REQ-001, REQ-002, REQ-003 all in the same category, or skip categories entirely. Each REQ should cite the source `AC-*` from the problem brief where applicable.*

```markdown
# Feature Requirements: {{FEATURE_NAME}}

## EARS Requirements

### Invariants (ALWAYS SHALL)
- `REQ-001` (from AC-NNN): ALWAYS SHALL {{invariant}}

### Event-Driven (WHEN/THEN SHALL)
- `REQ-NNN` (from AC-NNN): WHEN {{trigger}} THEN SHALL {{response}}

### State-Driven (WHERE/THEN SHALL)
- `REQ-NNN` (from AC-NNN): WHERE {{state}} THEN SHALL {{behavior}}

### Conditional (AS/THEN SHALL)
- `REQ-NNN` (from AC-NNN): AS {{condition}} THEN SHALL {{behavior}}

### Exception (UNLESS/THEN SHALL)
- `REQ-NNN` (from AC-NNN): UNLESS {{exception}} THEN SHALL {{default}}

### Mandatory (SHALL)
- `REQ-NNN` (from AC-NNN): {{requirement}}

## Non-Functional Requirements
*NFRs use the same global ID space as REQs (or a separate `NFR-NNN` sequence). They flow through traceability the same way: source files that satisfy an NFR get an `IMPLEMENTS: NFR-NNN` line; NFRs validated purely by infra/CI rather than code are listed under "NFRs Validated Outside Code" with the validation mechanism.*

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-001 | {{NFR}} | {{Target}} | {{code / test / infra / CI / manual}} |

## NFRs Validated Outside Code
- `NFR-NNN`: {{NFR}} — validated by {{mechanism, e.g. terraform module / WAF rule / SLO dashboard}}
```

### Phase 3: Design Document

Address five correctness properties: round-trip, uniqueness, atomicity, validation, idempotency. If a property does not apply to this feature (e.g. a read-only endpoint has no atomicity concerns), write `N/A — <reason>` rather than fabricating content. Also include API surface and error handling.

#### Template: specs/{feature}/design.md

```markdown
# Design: {{FEATURE_NAME}}

## Correctness Properties

### Round-Trip
{{Can data be serialized/deserialized without loss?}}

### Uniqueness
{{Are identifiers and constraints enforced?}}

### Atomicity
{{Are operations all-or-nothing?}}

### Validation
{{Are inputs checked before processing?}}

### Idempotency
{{Can operations be safely retried?}}

## API Surface
| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| {{M}} | {{P}} | {{R}} | {{S}} | {{A}} |

## Error Handling
| Error | Code | Status | Recovery |
|-------|------|--------|----------|
| {{E}} | {{C}} | {{S}} | {{R}} |

## Data Model
Inline the entities and fields this feature touches (copied from `requirements/entity-dictionary.md`). Implementers reading this doc in a fresh context should not need to open the full dictionary.

| Entity | Fields Used | Notes |
|--------|-------------|-------|
| {{Entity}} | {{field_a, field_b}} | {{constraints relevant here}} |

### Entity Modifications
*If this feature requires **adding new fields** or **changing existing field definitions**, do NOT silently encode them here — that would create a fork between the spec and the entity dictionary. Either:*
*1. **Stop and ask** the user to run `/sdlc-requirements` first to update `requirements/entity-dictionary.md`, then re-run `/sdlc-spec` against the updated dictionary; or*
*2. With explicit user opt-in in this run, update `requirements/entity-dictionary.md` first (following the merge rules of `sdlc-requirements`), then continue.*

*List the modifications here for traceability:*
- {{Entity}}.{{field}}: ADDED / MODIFIED / REMOVED — {{reason}}, mirrored in `requirements/entity-dictionary.md`.
```

### Phase 4: Review

Present both documents to the user. Each requires explicit approval.

## Phase Transition

Once `requirements.md` and `design.md` are written and approved, this skill is done. **Do not invoke `/sdlc-test-plan` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Spec is complete for `{feature}`: `specs/{feature}/requirements.md` and `specs/{feature}/design.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-test-plan {feature}` to begin test planning.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
- List `specs/{feature}/` to see what was written
- Resume from the missing document (`requirements.md` or `design.md`)

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `requirements.md` | `{root}/specs/{feature}/` | EARS-format requirements |
| `design.md` | `{root}/specs/{feature}/` | Design with correctness properties |