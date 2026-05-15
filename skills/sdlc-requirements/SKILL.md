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

- **Approval**: write only after an explicit affirmative ("yes" / "ok" / "approved"). Silence or vague replies are change requests.
- **Required input missing**: if `docs/product.md` is missing on what looks like a non-trivial project, stop and ask the user to run `/sdlc-init` first. Don't fabricate product context.
- **Entity dictionary is project-wide**: `requirements/entity-dictionary.md` is one file shared across all features. On re-run, **merge** — never overwrite. Preserve existing entities and fields not touched by this run; surface conflicts (same entity, different fields) for user decision.
- **AC IDs are stable**: every Acceptance Criterion gets an `AC-NNN` ID; continue numbering on re-run, never recycle.

## Workflow

### Phase 1: Input Gathering

Read steering documents first if they exist:
- `docs/product.md` — product context, users, success criteria
- `docs/tech.md` — technology constraints
- `requirements/entity-dictionary.md` (if it exists) — prior entities, to be merged with new ones from this run

If no steering documents exist on a non-trivial project, stop and recommend the user run `/sdlc-init` first. For a deliberate lightweight project, you may proceed by asking the user directly: feature name, users, data entities, existing systems.

### Phase 2: Problem Brief

User stories surface the domain nouns, so write the brief first and let the entity dictionary fall out of it.

#### Template: requirements/problem-brief.md

```markdown
# Problem Brief: {{FEATURE_NAME}}

## Problem Statement
{{What pain point or opportunity exists?}}

## User Stories
- `US-001`: As a **{{user}}**, I want **{{goal}}** so that **{{reason}}**.

## Acceptance Criteria
*Each AC has a stable ID. `sdlc-spec` will cite the AC each `REQ-*` derives from, so renumbering breaks traceability.*

- [ ] `AC-001` (US-001): {{Condition — must be testable: include trigger, action, observable outcome}}
- [ ] `AC-002` (US-001): ...

## Dependencies
| Dependency | Type | Status |
|------------|------|--------|
| {{Dep}} | {{Type}} | {{Status}} |

## Open Questions
1. {{Question}}
```

Acceptance criteria should be precise enough to translate into EARS in the next phase. Avoid subjective language like "user-friendly" or "fast" — state the threshold.

### Phase 3: Entity Dictionary

Extract every domain noun mentioned in the problem brief (users, items, events, etc.) and define it here. Each entity specifies:
- **Name**: Domain concept (PascalCase)
- **Fields**: Attribute names (snake_case)
- **Type**: Data type (string, int, UUID, datetime, enum)
- **Constraints**: Required, unique, min/max, regex, FK
- **Description**: What this represents

**Merge, don't overwrite**: if `requirements/entity-dictionary.md` already exists, load it and merge:
- Entities not touched by this run → keep verbatim.
- New entities → append.
- Same entity, new fields → append fields to the existing entity (keep prior fields).
- Same entity, **conflicting** field definition (different type or constraints) → do not silently change. Surface the conflict to the user and ask which definition wins.

#### Template: requirements/entity-dictionary.md

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
- Acceptance criteria are testable (no subjective language).
- User stories follow "As a [user], I want [goal] so that [reason]".

Present each document to the user before writing. Do not write without approval.

## Phase Transition

Once both artifacts are written and approved, this skill is done. **Do not invoke `/sdlc-architect` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Requirements are complete: `requirements/problem-brief.md` and `requirements/entity-dictionary.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-architect` to begin architecture work.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
1. Start a new chat
2. List `requirements/` to check which artifacts were already written
3. Resume from the first missing artifact

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `problem-brief.md` | `{root}/requirements/problem-brief.md` | PRD with user stories |
| `entity-dictionary.md` | `{root}/requirements/entity-dictionary.md` | Domain entities, fields, constraints |