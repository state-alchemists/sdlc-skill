---
name: sdlc-init
description: Set up a project for spec-driven development. Installs the .sdlc/ scaffolding (templates, conventions, validator) and generates the steering documents and project constitution through systematic interrogation. Works on greenfield and brownfield projects.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-init

> **Execution model**: you execute the Workflow below — reading files, interviewing the user, generating artifacts, getting approval before writing. Lines that say "run `/sdlc-<other>`" are instructions **for the user**; only the user starts the next skill. Deliver the Phase Transition message, then stop.

Installs the `.sdlc/` scaffolding every other skill depends on, then writes the steering documents (`product.md`, `tech.md`, `test-strategy.md`, `AGENTS.md`) and the project constitution (`rules.md`).

## Before you start

- **Conventions**: `.sdlc/CONVENTIONS.md` (installed in Phase 2) is the single source of truth for paths, the EARS dialect, the ID scheme, and approval tiers. Everything below assumes it.
- **Templates**: every document comes from `.sdlc/templates/<name>.md`. Read the template, fill its `{{placeholders}}`, keep its shape. Never invent a different structure.
- **Idempotent**: safe to re-run. Existing files are never silently overwritten — a re-run fills gaps and presents diffs for anything it would change.
- **Rule IDs are immutable**: once `RULE-NNN` is written, never renumber it. Continue from the highest existing non-sentinel ID.

## Workflow

### Phase 1: Project Discovery

- List the repo root and whatever source directories it actually has. Read `README.md` and any manifest (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, ...) — in parallel. The manifest is what tells you the layout; record anything surprising in `.sdlc/config.json` in Phase 2.
- **Detect layout — by content, never by directory name.** A `docs/` directory is not evidence of anything; most projects have one.

<!-- legacy-detection:start -->
A project is on the **legacy SDLC layout** when either of these holds:

1. **A conclusive marker exists** — `docs/adr/ADR-*.md`; a root `rules.md` containing `RULE-`; `specs/<slug>/spec.md` (or `requirements.md` + `design.md`); `requirements/problem-brief.md` or `requirements/entity-dictionary.md`; or `docs/product.md`, `docs/tech.md` or `docs/test-strategy.md` — names this project writes and almost nothing else does.
2. **A weak marker exists and its own text cross-references the scheme** — `docs/architecture.md` containing `.sdlc/`, `ADR-<n>`, `RULE-<n>`, `US-<n>`, `AC-<n>`, `NFR-<n>` or `Feature Key`.

**`docs/architecture.md` on its own is not evidence.** MkDocs, Docusaurus and Diátaxis all emit that filename by default; far more projects have one than have ever run `/sdlc-init`. Treating it as a marker made `/sdlc-init` refuse to write steering documents on projects that had never used these skills.

Matching is case-sensitive: `ARCHITECTURE.md` is the project's own document, `architecture.md` is the one `/sdlc-init` writes. A near-miss is a miss — and the near-miss that bites is the lowercase collision, not the uppercase one.
<!-- legacy-detection:end -->

- Choose the branch:
  - **Legacy layout confirmed** → Phase 2 only, then the Legacy Transition below. **Name the markers that triggered it**, so the user can say "that one is ours" and you can continue on the brownfield path instead. Install the scaffolding (it is additive and `/sdlc-adopt` needs it), write no steering documents — they would form a parallel tree beside the legacy ones — and route the user to `/sdlc-adopt`.
  - **Suspected but not confirmed** (a weak marker with no scheme reference) → say in one line what you found, then **continue on the brownfield path**. Writing `.sdlc/docs/architecture.md` beside a project's own `docs/architecture.md` is not a parallel tree; it is a project with two documents, which is the normal case.
  - **Greenfield** (no source beyond scaffolding, no meaningful README) → Phase 3a.
  - **Brownfield** (existing source, real README, manifests with real deps) → Phase 3b.

### Phase 2: Install Scaffolding

Copy the files bundled alongside this skill in `assets/` into the project (Tier-2, batched with the Phase 4 documents — present the list, write on one affirmative). On the legacy-layout path this phase runs alone, as its own Tier-2 batch:

| From (this skill) | To (project) |
|---|---|
| `assets/CONVENTIONS.md` | `.sdlc/CONVENTIONS.md` |
| `assets/ANNOTATION.md` | `.sdlc/ANNOTATION.md` |
| `assets/config.json` | `.sdlc/config.json` |
| `assets/templates/*.md` | `.sdlc/templates/` |
| `assets/tools/sdlc-validate.py` | `.sdlc/tools/sdlc-validate.py` |

Not every file upgrades the same way — the difference matters when re-running on a project set up by an older version:

| File | On re-run |
|------|-----------|
| `templates/*.md` | **Never overwrite.** Templates are project-owned; a user who edited `spec.md` keeps their version. Install only what is missing and report what you skipped. |
| `config.json` | **Never overwrite.** It records this project's source/test layout and comment styles — the one file that is genuinely per-project. Install only if missing. |
| `tools/sdlc-validate.py` | **Always refresh.** It is tooling, not content — nobody hand-edits it, and an old copy carries fixed bugs. Say that you replaced it. |
| `ANNOTATION.md` | **Refresh, but show your work** — same as `CONVENTIONS.md`. A user may have added rows for their own file types. |
| `CONVENTIONS.md` | **Refresh, but show your work.** If the existing file differs from the bundled one, present the diff and get an affirmative (**Tier-1**) before replacing — a user may have appended project-specific conventions. If it is identical or absent, just write it. |

If the bundled files are unreachable from your runtime, say so and link the user to the repo — do not hand-write substitutes.

**Legacy Transition** (legacy-layout path only — deliver this instead of the Phase Transition, then end your turn):

> Scaffolding installed: `.sdlc/CONVENTIONS.md`, `.sdlc/templates/`, `.sdlc/tools/sdlc-validate.py`. Your SDLC artifacts are still at the legacy paths, so I have not written steering documents — they would sit in a parallel tree.
> To continue: exit this chat, start a fresh session, and run `/sdlc-adopt` to consolidate under `.sdlc/`. Then re-run `/sdlc-init` to fill any gaps.

### Phase 3a: Greenfield Interview

Ask these **one at a time**:

| Question | Fills |
|----------|-------|
| What is the product name and what problem does it solve? | product.md — Problem Statement |
| Who are the target users and what are their primary goals? | product.md — Target Users |
| What does success look like — functionally, non-functionally, for the business? | product.md — Success Criteria |
| What is explicitly in scope, and explicitly out of scope? | product.md — Scope |
| Who are the key stakeholders and what is each one's interest? | product.md — Key Stakeholders |
| What technology stack do you plan to use? | tech.md |
| Any architectural constraints or non-negotiables? | tech.md |
| How is quality measured? | test-strategy.md |
| What environments will exist? | test-strategy.md |

### Phase 3b: Brownfield Draft

The repo has signal — extract before asking. Derive each section from manifests, README, source layout, and CI config, then **present the derived draft** and ask the user to confirm, correct, and fill gaps.

- **Product** (problem / users / scope / stakeholders): mostly intent, not artifact. Confirm the name, draft the problem statement from the README, **interview** the rest.
- **Tech** (stack / constraints / dependencies): derivable from manifests. Confirm rather than interview.
- **Test strategy** (levels / tools / CI gates / environments): partly derivable from `.github/workflows/`, `.gitlab-ci.yml`, and test directories. Confirm what exists, interview what is missing.

Present the full draft even where you are confident — the user approves every section.

### Phase 4: Steering Documents

Fill `.sdlc/templates/product.md`, `tech.md`, `test-strategy.md`, and `agents.md` with the facts gathered. **Which copy**: read each template from `.sdlc/templates/` when it is already there (a re-run, or a user-edited template — theirs wins), otherwise from this skill's `assets/templates/`, since Phase 2 has not written yet on a first run. `AGENTS.md` goes at the **repo root**; the other three go under `.sdlc/docs/`. Present all four plus the Phase 2 scaffolding as **one Tier-2 batch**.

### Phase 5: Project Constitution

Steering documents describe the project; rules describe what must **always** be true and **never** happen. Every downstream skill reads `.sdlc/rules.md`.

Re-read the freshly written steering documents first — they often imply rules. Then ask, one at a time, only what is not already covered:

| Question | Becomes |
|----------|---------|
| Any security or compliance requirements (PII, PCI, HIPAA, GDPR) the code must always honor? | Compliance & Security |
| Any libraries, patterns, or language features explicitly banned (`eval`, raw SQL, `any`)? | Forbidden Patterns |
| Any patterns the team requires (structured logging, DI, async/await only)? | Required Patterns |
| The team's stance on test coverage, lint failures, and dead code? | Quality Gates |
| Formatting or naming conventions a reviewer would always flag? | Coding Standards |
| The process for overriding a rule (who approves, where it is recorded)? | **RULE-999's Statement** — not a new rule |

**Categories** (pin to this enum): `Forbidden Patterns`, `Required Patterns`, `Compliance & Security`, `Quality Gates`, `Coding Standards`, `Process` (reserved for RULE-999).

**Numbering**: user rules are `RULE-001`–`RULE-998`; `RULE-999` is the always-present Override Process sentinel. On a re-run, continue from the highest non-sentinel ID and never recycle.

Fill `.sdlc/templates/rules.md` into `.sdlc/rules.md`. First creation is Tier-2. A re-run that **modifies** an existing rule is Tier-1 — present a per-rule diff grouped as `### Unchanged`, `### Added`, `### Modified — was / now`, `### RULE-999`, and write only the approved items.

### Phase 6: Verify

Run `python3 .sdlc/tools/sdlc-validate.py` and report the summary. With no specs yet it reports "No SDLC specs found" — that is the expected clean result at this stage.

**Confirm the detected layout.** The validator classifies files as source or test from the conventions in `.sdlc/CONVENTIONS.md` (§ File roles). They cover Python, Go, Maven, Jest, RSpec, .NET and monorepos as shipped. If this project puts tests somewhere those defaults would miss — or keeps helper code in a directory named like a test tree — record it in `.sdlc/config.json` now, before any spec exists, and say what you set and why. Do not assume `src/` and `tests/`.

Then offer the CI gate, once — it is what the validator is for:

> Add this step to your CI workflow to fail a build on broken traceability:
> `python3 .sdlc/tools/sdlc-validate.py --strict`

On a project that already has specs, the refreshed validator may report findings the old copy missed. Two are expected right after an upgrade and both route to `/sdlc-adopt`: `legacy-test-plan` (the feature keeps a separate `test-plan.md`) and `legacy-layout`. Report them, don't fix them here.

## Phase Transition

> Project setup is complete: `.sdlc/docs/`, `AGENTS.md`, `.sdlc/rules.md`, `.sdlc/CONVENTIONS.md`, templates in `.sdlc/templates/`, and the validator at `.sdlc/tools/sdlc-validate.py`. Edit anything in `.sdlc/templates/` to change the shape of what later skills generate.
> To continue: exit this chat, start a fresh session, and run `/sdlc-plan`.

After delivering this message, end your turn.

## Error Recovery

Interrupted mid-phase: start a new chat, list `.sdlc/`, `.sdlc/docs/`, `.sdlc/templates/`, `.sdlc/tools/`, and the repo root to see what was written, then resume from the first missing artifact.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `product.md` | `.sdlc/docs/` | Product vision, users, success criteria |
| `tech.md` | `.sdlc/docs/` | Stack, constraints, property-testing tooling |
| `test-strategy.md` | `.sdlc/docs/` | Testing levels, naming convention, CI gates |
| `AGENTS.md` | repo root | AI assistant guide |
| `rules.md` | `.sdlc/` | Immutable project invariants |
| `CONVENTIONS.md` | `.sdlc/` | Paths, EARS dialect, ID scheme, approval tiers |
| `ANNOTATION.md` | `.sdlc/` | Comment syntax and header placement per language |
| `config.json` | `.sdlc/` | Source/test layout, comment styles, scan overrides |
| `templates/*.md` | `.sdlc/templates/` | Project-owned templates every skill generates from |
| `sdlc-validate.py` | `.sdlc/tools/` | Deterministic traceability + EARS validator |
