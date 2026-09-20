---
name: sdlc-spec
description: Generate a feature specification. Produces a single spec.md holding canonical EARS requirements, design, and the test plan for one feature.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-spec

> **Execution model**: you execute the Workflow below — reading files, interviewing the user, generating the spec, getting approval before writing. Lines that say "run `/sdlc-<other>`" are instructions **for the user**; only the user starts the next skill. Deliver the Phase Transition message, then stop.

Produces **one file per feature**: `.sdlc/specs/<slug>/spec.md`, holding EARS requirements, design, and the test plan. One source of truth for the implementer and the reviewer.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md` — paths, EARS dialect, ID scheme, approval tiers.
- **Template**: fill `.sdlc/templates/spec.md`. Missing `.sdlc/templates/`? Tell the user to run `/sdlc-init`.
- **Argument → slug**: slugify the free text the user passed (lowercase; spaces/underscores → `-`; drop characters outside `[a-z0-9-]`; collapse repeats; trim). Tell the user the slug if it differs from their input. No argument? Ask "What's the feature name?". Slugs are **stable** — never rename once code references the directory.
- **Feature Key**: every spec declares `**Feature Key:** <KEY>`, matching `[A-Z][A-Z0-9_-]*` and globally unique (the validator enforces both). Default to the uppercased slug; a shorter alias is fine (`user-authentication` → `AUTH`). A slug starting with a digit cannot become a key — `2fa` → `2FA` does not parse as a keyed tag — so pick one (`TWOFA`). Check existing specs' keys first.
- **Required input**: no `.sdlc/requirements/problem-brief.md`? Recommend `/sdlc-plan` — without a brief there are no `AC-*` to cite. If the user would rather proceed (a project `/sdlc-adopt` documented from code, or a deliberately lightweight one), write the requirements without citations and say so; the validator checks citations only when a brief exists.
- **ID stability**: `REQ-*`/`NFR-*` IDs are referenced by source headers, test headers, and inline tags. On a re-run, continue from the highest existing ID, never renumber, and retire a dropped requirement in place — its text **begins** `REMOVED ({date}) — {reason}`, directly after the `(AC-NNN)` citation if it has one: `` - `REQ-004` (AC-012): REMOVED (2026-03-01) — superseded by REQ-009.`` Anything else between the ID and `REMOVED` leaves the requirement active and demanding coverage.
- **Legacy layout**: a feature with a separate `.sdlc/tests/<slug>/test-plan.md` predates the merge. Read it, fold it into the spec's `## Test Plan` section, and tell the user to run `/sdlc-adopt` for the rest of the project.

## Workflow

### Phase 1: Input Discovery

Read, in parallel:
- `.sdlc/rules.md` — requirements must encode rule compliance; refuse to write a requirement that forces a rule violation
- `.sdlc/docs/product.md`, `tech.md`, `architecture.md`, `adr/*.md`
- `.sdlc/requirements/problem-brief.md`, `entity-dictionary.md`
- `.sdlc/docs/test-strategy.md` — test naming convention and property-testing tooling

Pick or confirm the Feature Key now.

### Phase 2: EARS Requirements

Use the canonical dialect, keywords in **uppercase**:

| Pattern | Template | When |
|---------|----------|------|
| Ubiquitous | The `<system>` SHALL `<response>`. | Always-active invariant |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. | A user action or system event |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. | Holds while in a state |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. | Tied to an optional/configured feature |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. | Error, guard, exception |
| Complex | WHILE `<state>`, WHEN `<trigger>`, the `<system>` SHALL `<response>`. | Multiple clauses |

A flat numbered list — the keyword tells the reader the category, so no category headers. Every requirement cites the `AC-*` it derives from, and every cited `AC-*` must exist in the problem brief — the validator errors on one that does not. Keywords are uppercase; lowercase `when` or `shall` is prose and the validator warns.

### Phase 3: Design Properties (think, don't write)

Silently check which correctness properties apply. This is a completeness check; the spec lists only the ones that do.

| Property | Applies when | Skip when |
|----------|--------------|-----------|
| Round-Trip | Data is serialized/deserialized | Read-only operations, logging |
| Uniqueness | Identifiers, constraints, deduplication | Stateless transformations |
| Atomicity | Multi-step writes, transactions | Read-only endpoints, single idempotent writes |
| Validation | External input enters the system | Internal, already-validated data |
| Idempotency | Clients may retry | Inherently non-idempotent operations (login, payment capture) |

No `N/A` rows in the output.

### Phase 4: Write the Spec

Fill `.sdlc/templates/spec.md`. Notes on the sections that carry traps:

- **Non-Functional Requirements**: cite `NFR-*` IDs from the brief; don't invent new ones. "Validated By" names the mechanism that performs validation — naming CI exempts nothing, because CI is where validation runs, not what performs it.
- **NFRs Validated Outside Code**: only NFRs validated by infra or process. Listing an NFR here is the **only** way it becomes exempt from `IMPLEMENTS:`/`COVERS:` — what the table's "Validated By" cell says exempts nothing.
- **Entities**: reference the entity dictionary. If the feature needs a new field, either stop and ask the user to run `/sdlc-plan`, or — with explicit **Tier-1** opt-in — update the dictionary in this session, then continue.
- **Test Plan**: a structural mapping of the requirements above it, in the same file. Every `REQ-*` appears in at least one row's `Req` column. Property-based tests only if `tech.md` or `test-strategy.md` names a tool — otherwise mark that subsection `N/A — no property-testing framework configured`. State the naming convention from `test-strategy.md` at the top.

### Phase 5: Validation

Before presenting, check:
- Every `REQ-*` is covered by a test-plan row, and every test-plan row will become a real test (the validator warns about a planned `UT-*`/`IT-*` no test file `COVERS:`).
- Every `NFR-*` is covered by a test row **or** listed under "NFRs Validated Outside Code".
- Every correctness property appears in Design Property Coverage.
- Every requirement uses an uppercase canonical EARS keyword (no `ALWAYS SHALL`, `AS … THEN`, `UNLESS`).

Then run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>`. No code exists yet, so expect `trace-code`/`trace-test` errors — `sdlc-implement` resolves those. Everything else should be clean.

Present the spec as one **Tier-2** batch. Overwriting an existing `spec.md` is **Tier-1** — show a diff first.

## Phase Transition

> Spec complete for `<slug>` (Feature Key `{{KEY}}`): `.sdlc/specs/<slug>/spec.md`, including its test plan.
> To continue: exit this chat, start a fresh session, and run `/sdlc-implement <slug>`.

After delivering this message, end your turn.

## Choosing the feature slice

Features come from the `US-*` stories in the problem brief — you pick the slice.
- **Too small** → use `/sdlc-quickfix` instead.
- **Too big** → EARS sprawls and `sdlc-implement`'s single delegation struggles.
- **Sweet spot** → one user-visible capability, ~3–10 `REQ-*`, one coding session.

## Error Recovery

Interrupted mid-phase: read `.sdlc/specs/<slug>/spec.md` to see how far it got, then resume from the first missing section.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `spec.md` | `.sdlc/specs/<slug>/` | EARS requirements, design, and test plan; declares the Feature Key |
