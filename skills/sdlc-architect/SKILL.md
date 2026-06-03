---
name: sdlc-architect
description: Generate ADRs and architecture documentation. Produces decision records and structural overview from requirements and tech constraints.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-architect

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Transforms requirements and tech constraints into architectural decisions (ADRs) and a living architecture document.

## Conventions (read once, apply throughout)

- **Approval**: write only after an explicit affirmative ("yes" / "ok" / "approved"). Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/docs/tech.md` and `.sdlc/requirements/problem-brief.md` are both missing, stop and ask the user to run `/sdlc-init` and `/sdlc-requirements` first. Do not invent product or tech context.
- **ADR IDs are immutable**: never renumber or overwrite an existing ADR. To change a decision, write a new ADR (with the next available number) whose Status is `Accepted` and which marks the prior ADR as `Superseded`.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if present) — ADRs must cite each `RULE-*` they implement under their **Implements Rules** section, and must never propose a decision that violates a rule.
- `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`
- `.sdlc/requirements/entity-dictionary.md`, `.sdlc/requirements/problem-brief.md`
- Existing files in `.sdlc/docs/adr/`

### Phase 2: Architecture Decision Records

For each major decision, write an ADR. Suggested topics (skip any that don't apply to the project from `.sdlc/docs/tech.md`): database, API style, auth, deployment, frontend framework, observability, packaging.

**Numbering**: read existing files in `.sdlc/docs/adr/` and continue from the highest existing number. Never overwrite an existing ADR — supersede it with a new one that references the old number.

#### Template: .sdlc/docs/adr/ADR-{N}.md

```markdown
# ADR-{{NUMBER}}: {{TITLE}}

## Status
{{Proposed / Accepted / Deprecated / Superseded}}

## Context
{{Why this decision is needed}}

## Decision
{{The choice made, with specific technology/approach}}

## Consequences
### Positive
- {{Gain}}
### Negative
- {{Loss}}

## Implements Rules
*Which `RULE-*` from `.sdlc/rules.md` does this decision satisfy? List them, or write "None — this decision is orthogonal to current rules."*
- {{RULE-NNN}}

## Verification
*How is adherence to this decision enforced? Lint rules, CI gates, code review checklist, runtime assertions, etc.*
- {{Mechanism}}

## References
- {{Link or document}}
```

### Phase 3: Architecture Document

#### Template: .sdlc/docs/architecture.md

```markdown
# Architecture: {{PROJECT_NAME}}

## System Context (C4 Level 1)
{{System boundary and external actors}}

## Container Diagram (C4 Level 2)
| Container | Technology | Responsibility |
|-----------|-----------|----------------|
| {{Name}} | {{Tech}} | {{Role}} |

## Component Diagram (C4 Level 3)
### {{Group}}
| Component | Responsibility | Dependencies |
|-----------|---------------|-------------|
| {{Name}} | {{Role}} | {{Deps}} |

## Key Decisions
| ADR | Title | Status |
|-----|-------|--------|
| ADR-{{N}} | {{Title}} | {{Status}} |

## Data Flow
{{How data moves between components}}

## Deployment
| Environment | Infrastructure | Strategy |
|-------------|---------------|----------|
| Dev | {{Infra}} | {{Strategy}} |
| Staging | {{Infra}} | {{Strategy}} |
| Production | {{Infra}} | {{Strategy}} |
```

### Phase 4: Review

Present each ADR and the architecture document to the user. Each requires explicit approval.

## Phase Transition

Once the ADRs and `.sdlc/docs/architecture.md` are written and approved, this skill is done. **Do not invoke `/sdlc-spec` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Architecture is complete: `.sdlc/docs/adr/ADR-*.md` and `.sdlc/docs/architecture.md`. To continue, exit this chat and start a fresh session, then run `/sdlc-spec <feature-name>` to specify your first feature.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase:
- List `.sdlc/docs/adr/` and `.sdlc/docs/` to see what was written
- Resume from the first missing ADR or the architecture doc

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `ADR-*.md` | `{root}/.sdlc/docs/adr/` | Architecture Decision Records |
| `architecture.md` | `{root}/.sdlc/docs/architecture.md` | High-level architecture overview |