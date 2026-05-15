---
name: sdlc-init
description: Generate steering documents for SDLC-driven development. Produces product.md, tech.md, test-strategy.md, and AGENTS.md through systematic project interrogation.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-init

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Generates the four steering documents that anchor all subsequent SDLC phases. These define the "what", "how", and "how-verified" of the project before any feature work begins.

## Conventions (read once, apply throughout)

- **Approval**: When the skill says "obtain approval before writing", treat as approved only an affirmative reply (e.g. "yes", "ok", "approved", "go ahead"). Anything else — including silence, vague responses ("looks fine I guess"), or partial edits — is a change request: incorporate the change and re-present. Never write without an explicit affirmative.
- **Required file missing**: If a file marked **required** for input cannot be found, stop and tell the user which prerequisite step they need to complete first. Do not invent or hallucinate the missing content.

## Workflow

### Phase 1: Project Discovery

Gather project facts before writing any documents:
- List the contents of the repo root and `src/` (if it exists) to understand any existing structure.
- Read `README.md` and any manifest files present (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, etc.) — read them in parallel.
- Decide which branch to take:
  - **Greenfield** (no source code beyond scaffolding, no meaningful README): go to **Phase 1a**.
  - **Brownfield** (existing source / non-trivial README / manifests with real deps): go to **Phase 1b**.

### Phase 1a: Greenfield Interview

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

### Phase 1b: Brownfield Draft

The repo has signal already — extract what's there before asking. For each section of each steering document, attempt to derive an answer from manifests, README, source layout, or CI config. Then **present the derived answers to the user as a draft** and ask them to:
- Confirm what's correct.
- Correct what's wrong.
- Fill in anything you couldn't infer.

Specifically:
- **Product** (problem / users / scope / stakeholders / success criteria): usually only partially in the README. Confirm name from manifest, draft problem statement from README, then **interview** the rest — these are intent, not artifacts.
- **Tech** (stack / constraints / dependencies): largely derivable from manifests. Confirm rather than interview.
- **Test strategy** (levels / tools / CI gates / environments): partly derivable from CI files (`.github/workflows/`, `.gitlab-ci.yml`, etc.) and test directories. Confirm what's there, interview what's missing.

Do not skip presenting the full draft just because some sections are confident — the user must approve every section.

### Phase 2: Generate Steering Documents

For each document, use the inline template below. Replace bracketed content with discovered/interviewed facts. Present each document to the user for approval before writing.

#### Template: docs/product.md

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

#### Template: docs/tech.md

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

#### Template: docs/test-strategy.md

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
| `docs/product.md` | Product vision |
| `docs/tech.md` | Tech decisions |
| `docs/test-strategy.md` | Testing approach |
~~~

`AGENTS.md` lives at the repo root (not under `docs/`). All other steering documents go under `{project_root}/docs/`.

## Phase Transition

Once all four artifacts are written and approved, this skill is done. **Do not invoke the next skill yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Steering documents are complete: `docs/product.md`, `docs/tech.md`, `docs/test-strategy.md`, and `AGENTS.md`. To continue:
> 1. Exit this chat and start a fresh session (so context doesn't accumulate — the next skill reads artifacts from disk, not chat history).
> 2. **Strongly recommended**: run `/sdlc-rules` to capture project-wide invariants (security, forbidden patterns, coding standards). Every downstream skill reads `.sdlc/rules.md` as a precondition.
> 3. Then start another fresh chat and run `/sdlc-requirements` to begin requirements elicitation.

After delivering this message, end your turn. Do not run any other skill or simulate the next phase.

## Error Recovery

If the session is interrupted mid-phase:
1. Start a new chat
2. List the contents of `docs/` and the repo root to check which artifacts were already written
3. Resume from the first missing artifact

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `product.md` | `{root}/docs/product.md` | Product vision, users, success criteria |
| `tech.md` | `{root}/docs/tech.md` | Technology stack, constraints |
| `test-strategy.md` | `{root}/docs/test-strategy.md` | Testing approach, CI gates |
| `AGENTS.md` | `{root}/AGENTS.md` | AI assistant guide |