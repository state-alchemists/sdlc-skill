---
name: sdlc-plan
description: Elicit requirements and architecture in one session. Produces the problem brief (PRD), entity dictionary, ADRs, and the architecture document. Run after /sdlc-init, once per project (re-run to extend).
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-plan

> **Execution model**: you execute the Workflow below — reading files, interviewing the user, generating artifacts, getting approval before writing. Lines that say "run `/sdlc-<other>`" are instructions **for the user**; only the user starts the next skill. Deliver the Phase Transition message, then stop.

Turns the product vision into the two things every feature spec cites: **requirements** (problem brief + entity dictionary) and **architecture** (ADRs + architecture document). Formerly `sdlc-requirements` + `sdlc-architect` — they read the same inputs and neither needs a session of its own.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md` — paths, ID scheme, approval tiers.
- **Templates**: fill `.sdlc/templates/problem-brief.md`, `entity-dictionary.md`, `adr.md`, and `architecture.md`. Missing `.sdlc/templates/`? Tell the user to run `/sdlc-init`.
- **Legacy layout**: artifacts only at `docs/` or `requirements/`? Read them in place, write nothing parallel, and tell the user to run `/sdlc-adopt`.
- **Required input**: if no steering documents exist on a non-trivial project, stop and recommend `/sdlc-init`. For a deliberately lightweight project you may proceed by asking the user directly for product name, users, and entities.
- **IDs are load-bearing**: `sdlc-spec` cites `AC-*` and `NFR-*` from the brief. Never renumber or reword an existing one silently.

## Workflow

### Phase 1: Input Discovery

Read, in parallel:
- `.sdlc/rules.md` — ADRs must cite the `RULE-*` they implement and must never propose a decision that violates one.
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`
- `.sdlc/requirements/problem-brief.md`, `.sdlc/requirements/entity-dictionary.md` (if present — this run **merges**, it does not overwrite)
- Existing `.sdlc/docs/adr/ADR-*.md` — for the next free number

### Phase 2: Problem Brief

User stories surface the domain nouns, so write the brief first and let the entity dictionary fall out of it. The brief is **project-level** — it accumulates stories across features.

**Merge on re-run**: keep existing `US-*`/`AC-*`/`NFR-*` verbatim; append new ones with the next free IDs. If this run would change the text of an existing AC, surface it as a **Tier-1 conflict** rather than editing silently — renumbering or rewording breaks the `REQ-* → AC-*` traceability `sdlc-spec` depends on.

Acceptance criteria and NFRs must be precise enough to become EARS requirements later. No "user-friendly", no "fast" — state the threshold.

### Phase 3: Entity Dictionary

Extract every domain noun in the brief. Entity names are PascalCase, fields snake_case; each field gets a type, constraints (required, unique, min/max, regex, FK), and a description.

**Merge, don't overwrite**: untouched entities stay verbatim; new entities append; new fields append to an existing entity. A **conflicting** field definition (different type or constraints) is a **Tier-1** decision — surface it and ask which wins.

### Phase 4: Architecture Decision Records

One ADR per major decision. Suggested topics, skipping any the project does not have (check `tech.md`): database, API style, auth, deployment, frontend framework, observability, packaging.

**Numbering**: continue from the highest existing ADR. Never overwrite an ADR — supersede it with a new one that references the old number (a supersession is **Tier-1**).

Each ADR cites the `RULE-*` it implements and states how adherence is verified.

### Phase 5: Architecture Document

Fill `.sdlc/templates/architecture.md` into `.sdlc/docs/architecture.md`. Its Key Decisions table indexes the ADRs from Phase 4. Include only environments that actually exist per `test-strategy.md`.

### Phase 6: Validation

Before writing, cross-check:
- Every recurring capitalized noun in the brief is an entity, or deliberately excluded.
- Every entity field referenced by an acceptance criterion exists in the dictionary.
- Acceptance criteria and NFRs are testable (no subjective language).
- User stories read "As a {user}, I want {goal} so that {reason}".
- Every ADR cites its rules and its verification mechanism.

Present all four documents as **one Tier-2 batch**. Resolve Tier-1 conflicts (AC rewordings, entity conflicts, ADR supersessions) first, individually.

## Phase Transition

> Planning is complete: `.sdlc/requirements/problem-brief.md`, `.sdlc/requirements/entity-dictionary.md`, `.sdlc/docs/adr/ADR-*.md`, and `.sdlc/docs/architecture.md`.
> To continue: exit this chat, start a fresh session, and run `/sdlc-spec <feature>` (e.g. `User Auth` → slug `user-auth`) to specify your first feature.

After delivering this message, end your turn.

## Error Recovery

Interrupted mid-phase: list `.sdlc/requirements/` and `.sdlc/docs/adr/` to see what was written, then resume from the first missing artifact.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `problem-brief.md` | `.sdlc/requirements/` | PRD: user stories, `AC-*`, `NFR-*` sources |
| `entity-dictionary.md` | `.sdlc/requirements/` | Domain entities, fields, constraints |
| `ADR-*.md` | `.sdlc/docs/adr/` | Architecture Decision Records |
| `architecture.md` | `.sdlc/docs/` | C4 overview, data flow, deployment |
