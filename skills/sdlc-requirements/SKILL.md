---
name: sdlc-requirements
description: Elicit and document requirements. Produces problem brief (PRD) and entity dictionary from user interviews or input documents.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-requirements

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Takes raw product vision (from sdlc-init outputs or user input) and produces structured requirements artifacts: problem brief (PRD) and entity dictionary.

## Conventions (read once, apply throughout)

- **Artifact paths (migration-aware)**: read SDLC artifacts from `.sdlc/` (canonical). If an artifact is missing there, check the legacy root (`docs/`, `requirements/`, `rules.md`) — older projects keep them there. If you find legacy-only artifacts, read them in place, do NOT create a parallel `.sdlc/` copy, and tell the user to run `/sdlc-migrate`. See `.sdlc/CONVENTIONS.md` if present.
- **Approval**: brief + entity dictionary are one **Tier-2** batch — present both, write on a single affirmative ("yes" / "ok" / "approved"). An entity-dictionary **conflict resolution** (same entity, different definition) is **Tier-1** — resolve it with the user explicitly before writing. Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/docs/product.md` (or legacy `docs/product.md`) is missing on what looks like a non-trivial project, stop and ask the user to run `/sdlc-init` first. Don't fabricate product context.
- **Project-wide, single-file, merge-on-rerun**: both `problem-brief.md` and `entity-dictionary.md` are one file each, shared across all features. On re-run, **merge** — never overwrite. Preserve existing content not touched by this run; surface conflicts for user decision.
- **Stable IDs**: `US-*` (stories), `AC-*` (acceptance criteria), and `NFR-*` (non-functional requirements) IDs are stable. Continue numbering on re-run; never recycle a retired ID.

## Workflow

### Phase 1: Input Gathering

Read steering documents first if they exist (canonical path, then legacy fallback):
- `.sdlc/docs/product.md` — product context, users, success criteria (NFRs derive from its Success Criteria)
- `.sdlc/docs/tech.md` — technology constraints
- `.sdlc/requirements/problem-brief.md` and `.sdlc/requirements/entity-dictionary.md` (if they exist) — prior content, to be **merged** with this run

If no steering documents exist on a non-trivial project, stop and recommend `/sdlc-init` first. For a deliberate lightweight project, you may proceed by asking the user directly: feature name, users, data entities, existing systems.

### Phase 2: Problem Brief

User stories surface the domain nouns, so write the brief first and let the entity dictionary fall out of it. The brief is **project-level** (it accumulates stories across features), not per-feature.

**Merge on re-run**: if `problem-brief.md` already exists, load it. Keep existing `US-*`/`AC-*`/`NFR-*` entries verbatim; append new stories/criteria with the next free IDs; if a re-run changes the text of an existing AC, surface it as a conflict (Tier-1) rather than silently editing — renumbering or rewording breaks the `REQ-* → AC-*` traceability `sdlc-spec` relies on.

#### Template: .sdlc/requirements/problem-brief.md

```markdown
# Problem Brief: {{PROJECT_NAME}}

## Problem Statement
{{What pain point or opportunity exists?}}

## User Stories
- `US-001`: As a **{{user}}**, I want **{{goal}}** so that **{{reason}}**.

## Acceptance Criteria
*Each AC has a stable ID. `sdlc-spec` cites the AC each `REQ-*` derives from, so renumbering breaks traceability.*

- [ ] `AC-001` (US-001): {{Condition — must be testable: include trigger, action, observable outcome}}
- [ ] `AC-002` (US-001): ...

## Non-Functional Requirements
*The upstream source of `NFR-*` IDs. Derived from product.md Success Criteria (performance, security, reliability). `sdlc-spec` cites these IDs; it does not invent NFRs from nowhere.*

- `NFR-001`: {{Measurable non-functional target — e.g. "P95 page load < 1.5s"}}
- `NFR-002`: ...

## Dependencies
| Dependency | Type | Status |
|------------|------|--------|
| {{Dep}} | {{Type}} | {{Status}} |

## Open Questions
1. {{Question}}
```

Acceptance criteria and NFRs must be precise enough to translate into EARS in the next phase. Avoid subjective language like "user-friendly" or "fast" — state the threshold.

### Phase 3: Entity Dictionary

Extract every domain noun mentioned in the problem brief (users, items, events, etc.) and define it here. Each entity specifies:
- **Name**: Domain concept (PascalCase)
- **Fields**: Attribute names (snake_case)
- **Type**: Data type (string, int, UUID, datetime, enum)
- **Constraints**: Required, unique, min/max, regex, FK
- **Description**: What this represents

**Merge, don't overwrite**: if `entity-dictionary.md` already exists, load it and merge:
- Entities not touched by this run → keep verbatim.
- New entities → append.
- Same entity, new fields → append fields to the existing entity (keep prior fields).
- Same entity, **conflicting** field definition (different type or constraints) → do not silently change. Surface the conflict (Tier-1) and ask which definition wins.

#### Template: .sdlc/requirements/entity-dictionary.md

```markdown
# Entity Dictionary: {{PROJECT_NAME}}

## Entities

### {{EntityName}}
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| {{field_name}} | {{type}} | {{constraints}} | {{desc}} |

## Relationships
| Source | Target | Type | Cardinality | Description |
|--------|--------|------|-------------|-------------|
| {{src}} | {{tgt}} | {{type}} | {{card}} | {{desc}} |

## Validation Rules
- {{Rule}}
```

### Phase 4: Validation

Before writing, cross-reference the two documents:
- Grep the problem brief for capitalized nouns; every recurring one should appear as an entity (or be deliberately excluded).
- Every entity field referenced by acceptance criteria must exist in the dictionary.
- Acceptance criteria and NFRs are testable (no subjective language).
- User stories follow "As a [user], I want [goal] so that [reason]".

Present both documents as one Tier-2 batch before writing. Resolve any merge conflicts (Tier-1) first.

## Phase Transition

Once both artifacts are written and approved, this skill is done. **Do not invoke `/sdlc-architect` yourself.** Tell the user (paraphrase as needed):

> Requirements are complete: `.sdlc/requirements/problem-brief.md` and `.sdlc/requirements/entity-dictionary.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-architect` to begin architecture work.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
1. Start a new chat
2. List `.sdlc/requirements/` to check which artifacts were already written
3. Resume from the first missing artifact

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `problem-brief.md` | `{root}/.sdlc/requirements/problem-brief.md` | Project PRD: user stories, acceptance criteria, NFR sources |
| `entity-dictionary.md` | `{root}/.sdlc/requirements/entity-dictionary.md` | Domain entities, fields, constraints |
