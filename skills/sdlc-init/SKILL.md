---
name: sdlc-init
description: Generate steering documents and project constitution for SDLC-driven development. Produces product.md, tech.md, test-strategy.md, AGENTS.md, .sdlc/rules.md, .sdlc/CONVENTIONS.md, and the .sdlc/tools/ validator through systematic project interrogation.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-init

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Generates the four steering documents that anchor all subsequent SDLC phases, the project constitution (`.sdlc/rules.md`), the shared conventions file (`.sdlc/CONVENTIONS.md`), and the bundled validator (`.sdlc/tools/sdlc-validate.py`) that every downstream skill reads or runs. Formerly two separate skills (`sdlc-init` + `sdlc-rules`), now one session.

## Conventions (read once, apply throughout)

- **Approval tiers** (replaces blanket per-document approval — see `.sdlc/CONVENTIONS.md`):
  - **Tier 1 — explicit per-item approval**: global / hard-to-reverse writes — `.sdlc/rules.md` on a re-run that MODIFIES an existing rule, and any file MOVE. Present, get an affirmative, then write.
  - **Tier 2 — one batched approval**: routine first-time generation. Present the whole set as one grouped preview; a single affirmative writes all of them. The four steering documents are one batch; the rules file + conventions + validator are a second batch.
  - **Tier 3 — no approval**: read-only analysis and validator runs.
  - Anything other than an affirmative ("yes" / "ok" / "approved" / "go ahead") is a change request: incorporate and re-present. Silence or vague replies ("looks fine I guess") are change requests.
- **Artifact paths (migration-aware)**: canonical SDLC artifacts live under `.sdlc/`. Older projects keep steering docs, ADRs, and requirements at the repo root (`docs/`, `docs/adr/`, `requirements/`). If Phase 1 finds artifacts ONLY at legacy roots, the project is on the legacy layout — do NOT create a parallel `.sdlc/` tree (split-brain). Tell the user to run `/sdlc-migrate` first, then resume.
- **Required file missing**: if a file marked **required** for input cannot be found, stop and tell the user which prerequisite step they need first. Do not invent or hallucinate the missing content.
- **Rule IDs are immutable**: once a `RULE-NNN` is written, never renumber it. Continue from the highest existing non-sentinel ID on every re-run.

## Workflow

### Phase 1: Project Discovery

Gather project facts before writing any documents:
- List the contents of the repo root and `src/` (if it exists) to understand any existing structure.
- Read `README.md` and any manifest files present (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, etc.) — in parallel.
- **Detect layout**: check both `.sdlc/docs/` and the legacy `docs/` (and `.sdlc/requirements/` vs `requirements/`). If steering docs or requirements exist ONLY at legacy roots, stop and tell the user: *"This project uses the legacy layout (artifacts at `docs/`, `requirements/`). Run `/sdlc-migrate` to consolidate under `.sdlc/`, then re-run `/sdlc-init` to fill any gaps."* Do not proceed to write `.sdlc/docs/` alongside a legacy `docs/`.
- Decide which branch to take:
  - **Greenfield** (no source code beyond scaffolding, no meaningful README): go to **Phase 2a**.
  - **Brownfield** (existing source / non-trivial README / manifests with real deps): go to **Phase 2b**.

### Phase 2a: Greenfield Interview

Ask these questions **one at a time**:

| Question | Maps to |
|----------|---------|
| What is the product name and what problem does it solve? | product.md (Problem Statement) |
| Who are the target users and what are their primary goals? | product.md (Target Users) |
| What does success look like — functionally, non-functionally (performance/security), and for the business? | product.md (Success Criteria) |
| What is explicitly in scope, and what is explicitly out of scope? | product.md (Scope) |
| Who are the key stakeholders and what is each one's interest? | product.md (Stakeholders) |
| What technology stack do you plan to use? | tech.md |
| Are there any architectural constraints or non-negotiables? | tech.md |
| How is quality measured? | test-strategy.md |
| What environments will exist? | test-strategy.md |

### Phase 2b: Brownfield Draft

The repo has signal already — extract what's there before asking. For each section of each steering document, attempt to derive an answer from manifests, README, source layout, or CI config. Then **present the derived answers to the user as a draft** and ask them to confirm what's correct, correct what's wrong, and fill in what you couldn't infer.

Specifically:
- **Product** (problem / users / scope / stakeholders / success criteria): usually only partially in the README. Confirm name from manifest, draft problem statement from README, then **interview** the rest — these are intent, not artifacts.
- **Tech** (stack / constraints / dependencies): largely derivable from manifests. Confirm rather than interview.
- **Test strategy** (levels / tools / CI gates / environments): partly derivable from CI files (`.github/workflows/`, `.gitlab-ci.yml`, etc.) and test directories. Confirm what's there, interview what's missing.

Do not skip presenting the full draft just because some sections are confident — the user must approve every section (one batched Tier-2 approval).

### Phase 3: Generate Steering Documents

For each document, use the inline template below. Replace bracketed content with discovered/interviewed facts. Present all four documents together as one **Tier-2 batched** preview, then write on a single affirmative.

#### Template: .sdlc/docs/product.md

```markdown
# {{PRODUCT_NAME}} — Product Overview

## Problem Statement
{{What problem does this solve?}}

## Target Users
| User Role | Primary Goal |
|-----------|-------------|
| {{Role 1}} | {{Goal 1}} |
| ... | ... |

## Success Criteria
- **Functional**: {{Measurable outcome}}
- **Non-Functional**: {{Performance, security, etc.}}
- **Business**: {{ROI, adoption, etc.}}

## Scope
### In Scope
- {{Item}}
### Out of Scope
- {{Item}}

## Key Stakeholders
| Stakeholder | Interest |
|-------------|----------|
| {{Name}} | {{Interest}} |
| ... | ... |
```

#### Template: .sdlc/docs/tech.md

```markdown
# {{PROJECT_NAME}} — Technology Overview

## Stack
*Include only rows that apply to this project. A CLI library has no Database; a pure-frontend tool may have no Infrastructure. Do not invent missing rows.*

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | {{Lang}} | {{Ver}} | {{Why}} |
| Framework | {{FW}} | {{Ver}} | {{Why}} |
| Database | {{DB}} | {{Ver}} | {{Why}} |
| Infrastructure | {{Infra}} | {{Ver}} | {{Why}} |
| CI/CD | {{CICD}} | {{Ver}} | {{Why}} |

## Architecture Principles
1. **{{Principle}}** — {{Description}}
2. ...

## Constraints
- {{Constraint}}

## Dependencies
| Dependency | Purpose | License |
|------------|---------|---------|
| {{Dep}} | {{Purpose}} | {{License}} |
| ... | ... | ... |

## Property-Based Testing
*Name a property-testing tool here (hypothesis, fast-check, proptest, gopter, etc.) if the team uses one — `sdlc-spec` reads this to decide whether to emit property-based tests.*
- {{Tool or "None configured"}}
```

#### Template: .sdlc/docs/test-strategy.md

```markdown
# {{PROJECT_NAME}} — Test Strategy

## Testing Levels
| Level | Scope | Tool | Target |
|-------|-------|------|--------|
| Unit | Functions/classes | {{Tool}} | {{%}} |
| Integration | Module boundaries | {{Tool}} | {{%}} |
| E2E | Critical journeys | {{Tool}} | {{N}} scenarios |

## Test Naming Convention
*The single convention `sdlc-spec` and `sdlc-implement` follow. State it explicitly so test names are deterministic.*
- {{e.g. pytest `test_<fn>_<condition>_<expected>`; JS `describe('X', () => it('does Y'))`; Go `TestFooBar`; Rust `#[test] fn foo_does_bar`}}

## CI Gates
| Gate | Trigger | Command | Blocking |
|------|---------|---------|----------|
| Lint | Pre-commit | {{Cmd}} | Yes |
| Unit Tests | Every push | {{Cmd}} | Yes |
| Traceability | Every push / PR | `python3 .sdlc/tools/sdlc-validate.py --strict` | {{Yes/No}} |

## Environments
*Include only the environments the user actually listed. Do not add Staging / UAT / Canary / Sandbox unless the user said they exist.*

| Env | URL | Deploy | Data |
|-----|-----|--------|------|
| {{EnvName}} | {{URL}} | {{Auto / Manual}} | {{Real / Synthetic / Anonymized}} |
| ... | ... | ... | ... |

## Quality Goals
- **Unit coverage**: >= {{N}}%
- **Critical path E2E**: 100% of P0 scenarios
- **Security scanning**: {{Tool}} on every PR
```

#### Template: AGENTS.md

*Outer fence uses `~~~` so the inner code fences inside `## Essential Commands` don't terminate the template prematurely.*

~~~markdown
# {{PROJECT_NAME}}

## Overview
{{1-2 sentence summary}}

## Essential Commands
```bash
# Install
{{cmd}}
# Test
{{cmd}}
# Lint
{{cmd}}
# Run
{{cmd}}
# Validate SDLC traceability
python3 .sdlc/tools/sdlc-validate.py
```

## Architecture
{{Description}}

| Directory | Purpose |
|-----------|---------|
| `src/` | Source code |
| `.sdlc/docs/product.md` | Product vision |
| `.sdlc/docs/tech.md` | Tech decisions |
| `.sdlc/docs/test-strategy.md` | Testing approach |
| `.sdlc/CONVENTIONS.md` | Paths, EARS dialect, ID/traceability scheme |
| `.sdlc/rules.md` | Project invariants |
~~~

`AGENTS.md` lives at the repo root (not under `.sdlc/docs/`). All other steering documents go under `{project_root}/.sdlc/docs/`.

### Phase 4: Project Constitution (Rules)

After steering documents are approved, interview the user for project-wide invariants. Unlike steering documents (which describe the project), rules describe what **must always be true** and **must never happen**. Every downstream skill reads `.sdlc/rules.md` as a precondition.

#### 4a: Input Discovery

Re-read the freshly-written steering documents — they may already imply rules:
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`, `AGENTS.md`
- `.sdlc/rules.md` if it already exists (this run will **update**, not overwrite — preserve existing rule IDs)

#### 4b: Interview for Missing Invariants

Ask the user one question at a time, only those not already covered by the artifacts above. Each answer becomes one (or more) user rule under the named category — except the last, which configures the fixed RULE-999 sentinel, not a new rule:

| Question | Category (becomes RULE-NNN unless noted) |
|----------|------------------------------------------|
| Are there security or compliance requirements (PII, PCI, HIPAA, GDPR) the code must always honor? | Compliance & Security |
| Are there libraries, patterns, or language features the team has explicitly banned (e.g. `eval`, raw SQL, `any` types)? | Forbidden Patterns |
| Are there patterns the team requires (e.g. structured logging, dependency injection, async/await only)? | Required Patterns |
| What is the team's stance on test coverage, lint failures, and dead code? | Quality Gates |
| Are there formatting or naming conventions a reviewer would always flag? | Coding Standards |
| What is the process for overriding a rule (who approves, where it's recorded)? | **Configures RULE-999** (the Override Process sentinel) — record the answer in RULE-999's Statement; do not create a new RULE-NNN for this. |

**Categories** (pin to this enum — do not invent new ones):
- `Forbidden Patterns` — things the code must never do.
- `Required Patterns` — things the code must always do.
- `Compliance & Security` — regulatory or security invariants (PII, PCI, HIPAA, GDPR, secret handling).
- `Quality Gates` — coverage, lint, dead-code policies.
- `Coding Standards` — formatting, naming, idiom conventions.
- `Process` — reserved for the RULE-999 Override Process sentinel; do not add user rules under this category.

#### 4c: Generate `.sdlc/rules.md`

**Numbering**: user rules use IDs `RULE-001` through `RULE-998`. `RULE-999` is reserved for the Override Process sentinel and is always present. On a re-run, continue from the highest existing **non-sentinel** ID — ignore RULE-999 when computing "next ID". Never renumber or recycle IDs.

**Approval**: first-time creation is **Tier 2** (present the whole file once, single affirmative). On a re-run that MODIFIES an existing rule, that modification is **Tier 1** — present a per-rule diff grouped as `### Unchanged`, `### Added`, `### Modified — was / now`, `### RULE-999 — updated/unchanged`, and write only after the user approves the changed items.

#### Template: .sdlc/rules.md

```markdown
# Project Rules — Constitution

> Immutable invariants. Every SDLC skill reads this file and refuses to violate it.
> Override process: see RULE-999 below. Do not edit rule statements without an Override Record.

## How to Use This File
- Every spec, design, test plan, and implementation must respect every rule below.
- `/sdlc-review` will report a `FAIL` for any code that violates a rule.
- To change a rule, follow the Override Process (RULE-999) and append (do not edit) an entry to the Override Log.

## Rules

### RULE-001 — {{Short Title}}
| Field | Value |
|-------|-------|
| Category | {{Forbidden Patterns / Required Patterns / Compliance & Security / Quality Gates / Coding Standards}} |
| Statement | {{The rule, phrased as ALWAYS/NEVER}} |
| Rationale | {{Why this exists — past incident, regulation, team standard}} |
| Enforcement | {{How violations are detected — lint rule, review checklist, CI gate}} |
| Added | {{YYYY-MM-DD}} |

### RULE-002 — ...
...

## Override Process — RULE-999
| Field | Value |
|-------|-------|
| Category | Process |
| Statement | {{The team's override process from the interview: who approves, where it's recorded. Default: "A rule may only be overridden for a single change, recorded as an entry in the Override Log below, with the approver named. The rule statement itself is never edited."}} |
| Rationale | Prevents silent erosion of invariants. |
| Enforcement | Reviewers reject PRs that violate a rule without a matching Override Log entry. |

## Override Log

| Date | Rule | Scope (PR / commit) | Approver | Reason |
|------|------|---------------------|----------|--------|
| ... | RULE-NNN | ... | ... | ... |
```

### Phase 5: Tooling & Conventions

Write two more artifacts as part of the same Tier-2 batch as the rules file:

1. **`.sdlc/tools/sdlc-validate.py`** — copy the `sdlc-validate.py` file bundled alongside this skill into the project at `.sdlc/tools/sdlc-validate.py`. This is the deterministic traceability + EARS validator every later skill runs ("validate → fix → repeat") and that the CI gate in `test-strategy.md` invokes. If the bundled file is not reachable from your runtime, tell the user and link them to the repo copy; do not hand-write a substitute.
2. **`.sdlc/CONVENTIONS.md`** — write the shared-conventions reference below verbatim (it is the single source of truth every skill points to).

#### Template: .sdlc/CONVENTIONS.md

~~~markdown
# SDLC Conventions

Single source of truth for paths, the EARS dialect, the ID/traceability scheme, and approval tiers. Every `sdlc-*` skill reads this file.

## Artifact paths (canonical)
| Artifact | Path |
|----------|------|
| Steering docs | `.sdlc/docs/` |
| ADRs | `.sdlc/docs/adr/` |
| Architecture | `.sdlc/docs/architecture.md` |
| Requirements | `.sdlc/requirements/` |
| Specs | `.sdlc/specs/<slug>/spec.md` |
| Test plans | `.sdlc/tests/<slug>/test-plan.md` |
| Reviews | `.sdlc/reviews/<slug>/report-<ts>.md` |
| Rules | `.sdlc/rules.md` |
| Validator | `.sdlc/tools/sdlc-validate.py` |

**Legacy fallback**: projects created before the `.sdlc/` consolidation keep steering docs at `docs/`, ADRs at `docs/adr/`, requirements at `requirements/`, rules at `rules.md`. Skills read legacy locations if the canonical one is absent, but never write a parallel tree. Run `/sdlc-migrate` to consolidate.

## Feature slugs
A feature directory name is the slug of the feature: lowercase; spaces/underscores → `-`; drop characters outside `[a-z0-9-]`; collapse repeated `-`; trim leading/trailing `-`. Slugs are stable — never renumber or rename once code references `.sdlc/specs/<slug>/`.

## Canonical EARS dialect
| Pattern | Template |
|---------|----------|
| Ubiquitous | The `<system>` SHALL `<response>`. |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |
| Complex | Combine, e.g. WHILE `<state>`, WHEN `<trigger>`, the `<system>` SHALL `<response>`. |

This is canonical EARS (Mavin et al.). Deprecated dialect found in old specs migrates as: `ALWAYS SHALL` → ubiquitous (drop ALWAYS); `AS <c> THEN SHALL` → `IF <c>, THEN … SHALL`; `UNLESS <b> THEN SHALL <d>` → `IF NOT <b>, THEN … SHALL <d>`; old `WHERE <state>` (state-driven) → `WHILE <state>`.

## ID & traceability scheme
- Each `spec.md` declares `**Feature Key:** <KEY>` — an uppercase token `[A-Z][A-Z0-9_-]*`, globally unique across all features. Default suggestion: the uppercased slug.
- Requirement IDs are per-feature (`REQ-001`, `NFR-001`, `UT-001`, `IT-001`, `E2E-001`, `PBT-001`) and disambiguated globally by the key.
- Source header: `IMPLEMENTS: <KEY>:REQ-001, <KEY>:NFR-002`
- Test header: `COVERS: <KEY>:REQ-002, <KEY>:UT-005, <KEY>:IT-001`
- Inline tag: `@sdlc <KEY>:REQ-003, <KEY>:REQ-004`
- IDs are immutable: never renumber or recycle. A removed requirement keeps its ID with a `REMOVED ({date}) — {reason}` note.
- Validate with `python3 .sdlc/tools/sdlc-validate.py [--feature <slug>] [--strict]` — exit 0 clean, 1 warnings (with `--strict`), 2 errors.

## Approval tiers
- **Tier 1 — explicit per-item approval**: global / hard-to-reverse writes — `rules.md` rule modifications, ADR supersessions, entity-dictionary conflict resolutions, overwriting an existing spec, file moves.
- **Tier 2 — one batched approval**: routine first-time generation (steering docs together; spec + test plan together).
- **Tier 3 — no approval**: read-only analysis, validator runs, and review reports (the report is the deliverable, not a source mutation).
Anything other than an affirmative is a change request, at any tier.
~~~

### Phase 6: Approval

Two batched approvals total: (1) the four steering documents (Phase 3), (2) the rules file + conventions + validator (Phases 4–5). On a re-run that modifies existing rules, apply Tier-1 per-rule approval for the changed rules only.

## Phase Transition

Once all artifacts are written and approved, this skill is done. **Do not invoke the next skill yourself.** Tell the user (paraphrase as needed):

> Project setup is complete: `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`, `AGENTS.md`, `.sdlc/rules.md`, `.sdlc/CONVENTIONS.md`, and the validator at `.sdlc/tools/sdlc-validate.py`. To continue:
> 1. Exit this chat and start a fresh session (so context doesn't accumulate — the next skill reads artifacts from disk, not chat history).
> 2. Run `/sdlc-requirements` to begin requirements elicitation.

After delivering this message, end your turn. Do not run any other skill or simulate the next phase.

## Error Recovery

If the session is interrupted mid-phase:
1. Start a new chat
2. List the contents of `.sdlc/docs/`, `.sdlc/tools/`, the repo root, and `.sdlc/` to check which artifacts were already written
3. Resume from the first missing artifact

## Read By

| Skill | What it does with these artifacts |
|-------|-------------------------|
| `sdlc-architect` | ADRs must not contradict rules; cite RULE-* under "Implements Rules" |
| `sdlc-spec` | EARS requirements (canonical dialect) must encode rule compliance where relevant |
| `sdlc-implement` | Generated code must adhere; emits keyed traceability tags; runs the validator |
| `sdlc-quickfix` | Same as implement, applied to deltas |
| `sdlc-review` | Runs the validator; reports `FAIL` on any unrecorded rule violation |

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `product.md` | `{root}/.sdlc/docs/product.md` | Product vision, users, success criteria |
| `tech.md` | `{root}/.sdlc/docs/tech.md` | Technology stack, constraints, PBT tooling |
| `test-strategy.md` | `{root}/.sdlc/docs/test-strategy.md` | Testing approach, naming convention, CI gates |
| `AGENTS.md` | `{root}/AGENTS.md` | AI assistant guide |
| `rules.md` | `{root}/.sdlc/rules.md` | Immutable project invariants |
| `CONVENTIONS.md` | `{root}/.sdlc/CONVENTIONS.md` | Paths, EARS dialect, ID scheme, approval tiers |
| `sdlc-validate.py` | `{root}/.sdlc/tools/sdlc-validate.py` | Deterministic traceability + EARS validator |
