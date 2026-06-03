---
name: sdlc-init
description: Generate steering documents and project constitution for SDLC-driven development. Produces product.md, tech.md, test-strategy.md, AGENTS.md, and .sdlc/rules.md through systematic project interrogation.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-init

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Generates the four steering documents that anchor all subsequent SDLC phases, plus the project constitution (`.sdlc/rules.md`) that every downstream skill reads as a precondition. Formerly two separate skills (`sdlc-init` + `sdlc-rules`), now one session covering both project definition and invariants.

## Conventions (read once, apply throughout)

- **Approval**: When the skill says "obtain approval before writing", treat as approved only an affirmative reply (e.g. "yes", "ok", "approved", "go ahead"). Anything else — including silence, vague responses ("looks fine I guess"), or partial edits — is a change request: incorporate the change and re-present. Never write without an explicit affirmative.
- **Required file missing**: If a file marked **required** for input cannot be found, stop and tell the user which prerequisite step they need to complete first. Do not invent or hallucinate the missing content.
- **Rule IDs are immutable**: once a `RULE-NNN` is written, never renumber it. Continue from the highest existing non-sentinel ID on every re-run.

## Workflow

### Phase 1: Project Discovery

Gather project facts before writing any documents:
- List the contents of the repo root and `src/` (if it exists) to understand any existing structure.
- Read `README.md` and any manifest files present (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, etc.) — read them in parallel.
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

The repo has signal already — extract what's there before asking. For each section of each steering document, attempt to derive an answer from manifests, README, source layout, or CI config. Then **present the derived answers to the user as a draft** and ask them to:
- Confirm what's correct.
- Correct what's wrong.
- Fill in anything you couldn't infer.

Specifically:
- **Product** (problem / users / scope / stakeholders / success criteria): usually only partially in the README. Confirm name from manifest, draft problem statement from README, then **interview** the rest — these are intent, not artifacts.
- **Tech** (stack / constraints / dependencies): largely derivable from manifests. Confirm rather than interview.
- **Test strategy** (levels / tools / CI gates / environments): partly derivable from CI files (`.github/workflows/`, `.gitlab-ci.yml`, etc.) and test directories. Confirm what's there, interview what's missing.

Do not skip presenting the full draft just because some sections are confident — the user must approve every section.

### Phase 3: Generate Steering Documents

For each document, use the inline template below. Replace bracketed content with discovered/interviewed facts. Present each document to the user for approval before writing.

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

## CI Gates
| Gate | Trigger | Command | Blocking |
|------|---------|---------|----------|
| Lint | Pre-commit | {{Cmd}} | Yes |
| Unit Tests | Every push | {{Cmd}} | Yes |

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
```

## Architecture
{{Description}}

| Directory | Purpose |
|-----------|---------|
| `src/` | Source code |
| `.sdlc/docs/product.md` | Product vision |
| `.sdlc/docs/tech.md` | Tech decisions |
| `.sdlc/docs/test-strategy.md` | Testing approach |
~~~

`AGENTS.md` lives at the repo root (not under `.sdlc/docs/`). All other steering documents go under `{project_root}/.sdlc/docs/`.

### Phase 4: Project Constitution (Rules)

After steering documents are approved, interview the user for project-wide invariants. Unlike steering documents (which describe the project), rules describe what **must always be true** and **must never happen**. Every downstream skill reads `.sdlc/rules.md` as a precondition.

#### 4a: Input Discovery

Re-read the freshly-written steering documents — they may already imply rules:
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`
- `AGENTS.md`
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
| What is the process for overriding a rule (who approves, where it's recorded)? | **Configures RULE-999** (the Override Process sentinel) — do not create a new RULE-NNN for this. |

**Categories** (pin to this enum — do not invent new ones):
- `Forbidden Patterns` — things the code must never do.
- `Required Patterns` — things the code must always do.
- `Compliance & Security` — regulatory or security invariants (PII, PCI, HIPAA, GDPR, secret handling).
- `Quality Gates` — coverage, lint, dead-code policies.
- `Coding Standards` — formatting, naming, idiom conventions.
- `Process` — reserved for the RULE-999 Override Process sentinel; do not add user rules under this category.

#### 4c: Generate `.sdlc/rules.md`

**Numbering**: user rules use IDs `RULE-001` through `RULE-998`. `RULE-999` is reserved for the Override Process sentinel and is always present. On a re-run, continue from the highest existing **non-sentinel** ID — i.e. ignore RULE-999 when computing "next ID". Never renumber or recycle IDs.

If updating an existing `.sdlc/rules.md`: read the current file, build the new version, and present a summary grouped as `### Unchanged`, `### Added`, `### Modified — was / now`, `### RULE-999 — updated/unchanged`. Write only after the user approves.

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
| Category | {{Forbidden / Required / Compliance / Quality / Coding Standard}} |
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
| Statement | A rule may only be overridden for a single change, recorded as an entry in the Override Log below, with the approver named. The rule statement itself is never edited. |
| Rationale | Prevents silent erosion of invariants. |
| Enforcement | Reviewers reject PRs that violate a rule without a matching Override Log entry. |

## Override Log

| Date | Rule | Scope (PR / commit) | Approver | Reason |
|------|------|---------------------|----------|--------|
| ... | RULE-NNN | ... | ... | ... |
```

### Phase 5: Approval

Present the populated rules file to the user before writing. Each new or modified rule requires explicit approval (see Conventions).

If updating an existing `.sdlc/rules.md`: read the current file, build the new version in memory, and present a **unified diff** to the user (e.g. by listing rules under headings: `### Unchanged`, `### Added`, `### Modified — was / now`, `### RULE-999 — updated/unchanged`). Write only after the user approves the diff. Do not overwrite without showing what changes.

## Phase Transition

Once all five artifacts are written and approved, this skill is done. **Do not invoke the next skill yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Project setup is complete: `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`, `AGENTS.md`, and `.sdlc/rules.md`. Every downstream skill reads `.sdlc/rules.md` as a precondition. To continue:
> 1. Exit this chat and start a fresh session (so context doesn't accumulate — the next skill reads artifacts from disk, not chat history).
> 2. Run `/sdlc-requirements` to begin requirements elicitation.

After delivering this message, end your turn. Do not run any other skill or simulate the next phase.

## Error Recovery

If the session is interrupted mid-phase:
1. Start a new chat
2. List the contents of `.sdlc/docs/`, the repo root, and `.sdlc/` to check which artifacts were already written
3. Resume from the first missing artifact

## Read By

| Skill | What it does with rules |
|-------|-------------------------|
| `sdlc-architect` | ADRs must not contradict rules; cite RULE-* under "Implements Rules" |
| `sdlc-spec` | EARS requirements must encode rule compliance where relevant |
| `sdlc-implement` | Generated code must adhere; reject prompts that would violate |
| `sdlc-quickfix` | Same as implement, applied to deltas |
| `sdlc-review` | Reports `FAIL` on any unrecorded rule violation |

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `product.md` | `{root}/.sdlc/docs/product.md` | Product vision, users, success criteria |
| `tech.md` | `{root}/.sdlc/docs/tech.md` | Technology stack, constraints |
| `test-strategy.md` | `{root}/.sdlc/docs/test-strategy.md` | Testing approach, CI gates |
| `AGENTS.md` | `{root}/AGENTS.md` | AI assistant guide |
| `rules.md` | `{root}/.sdlc/rules.md` | Immutable project invariants |
