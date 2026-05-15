---
name: sdlc-review
description: Fresh-context review of implemented code against specifications. Validates spec compliance via an isolated code-review sub-agent.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-review

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, delegating to a code-review agent, auditing its findings, and writing the report. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Reviews implemented code against spec artifacts using a fresh-context code-review sub-agent.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-review <free-text>`. Use it verbatim as `{feature}`. If missing, ask.
- **Required input missing**: if `specs/{feature}/requirements.md` is missing, stop and tell the user — there's nothing authoritative to review against.
- **Timestamp**: get the current timestamp via the runtime's shell (e.g. `date -u +%Y-%m-%dT%H-%M-%S`). Never invent a timestamp.
- **Output path is feature-scoped**: write the report to `review/{feature}/report-{timestamp}.md` — not the unscoped `review/` directory. Multi-feature projects accumulate reports per-feature.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if present) — every violation must be reported as a FAIL unless the Override Log records an approved exception
- `specs/{feature}/requirements.md` — EARS requirements (the source of truth)
- `specs/{feature}/design.md` — correctness properties
- `tests/{feature}/test-plan.md` — expected test coverage
- `requirements/entity-dictionary.md` — domain model
- `docs/architecture.md`, `docs/adr/*.md` — architecture decisions

### Phase 2: Identify Changed Files

Use `git diff HEAD` (or list `src/` and `tests/`) to identify what was implemented.

### Phase 3: Fresh-Context Review

Delegate to a code-review agent with full spec context. The block below is a **prompt template** (not a tool call) — replace each `[Inline ...]` placeholder with real file content.

```
Review the implementation of {feature} against its specification.

EARS REQUIREMENTS:
[Inline from specs/{feature}/requirements.md]

DESIGN:
[Inline from specs/{feature}/design.md]

TEST PLAN:
[Inline from tests/{feature}/test-plan.md]

ENTITY DICTIONARY:
[Inline key entities from requirements/entity-dictionary.md]

PROJECT RULES:
[Inline .sdlc/rules.md if present, or write "No rules file present."]

ARCHITECTURE DECISIONS:
[Inline relevant ADRs]

CHANGED FILES:
[List files to review]

For each check below, return a status (PASS / FAIL / PARTIAL) with specific file:line evidence:
- EARS Coverage — every REQ-* and NFR-* has corresponding code + test (or, for NFRs validated outside code, the documented validation mechanism is in place)
- Correctness — each correctness property from design.md is handled (or marked N/A consistently)
- Entity Fidelity — fields match entity-dictionary (names, types, constraints)
- ADR Compliance — code follows ADR decisions
- Rules Compliance — code respects every RULE-* in .sdlc/rules.md (if the file exists); any violation must have a matching entry in the Override Log
- Test Coverage — test-plan tests are implemented and passing
- Traceability — every REQ-* and NFR-* (excluding NFRs validated outside code) appears in at least one source-file `IMPLEMENTS:` header AND one test-file `COVERS:` header; every `@sdlc REQ-*`/`@sdlc NFR-*` inline tag references a real ID in requirements.md
```

Traceability verification commands:
- `grep -rnE "IMPLEMENTS: " src/` → enumerate source-file headers
- `grep -rnE "COVERS: "     tests/` → enumerate test-file headers
- `grep -rnE "@sdlc (REQ|NFR)-" src/ tests/` → enumerate inline tags
- Then for **each** REQ-* / NFR-* in `specs/{feature}/requirements.md`, confirm it appears in at least one `IMPLEMENTS:` line and one `COVERS:` line (unless explicitly marked as validated outside code).

Hand the filled-in prompt to a code-review sub-agent — a fresh-context agent specialized for code review if your runtime exposes one, otherwise a general-purpose agent. The exact delegation tool name varies by runtime; use the one available to you. The point is fresh context: the review must not inherit assumptions from the implementation conversation.

### Phase 4: Audit the Agent's Findings

The agent's report is the primary review output. This phase is a sanity audit, not a re-run:

- Confirm the agent addressed **all seven checks** (EARS Coverage, Correctness, Entity Fidelity, ADR Compliance, Rules Compliance, Test Coverage, Traceability). If any are missing, re-delegate with the gap called out — do not redo them by hand.
- Spot-check 2–3 cited findings against the source files to verify the agent didn't hallucinate file paths or line numbers.
- Note any check the agent rated PASS without citing evidence — treat those as PARTIAL until verified.

### Phase 5: Report

Write the report to `review/{feature}/report-{YYYY-MM-DDTHH-MM-SS}.md` (ISO 8601 timestamp, colons replaced with hyphens for filesystem safety). Multiple reviews on the same day won't collide, and multi-feature projects keep reports separated.

#### Template: review/{feature}/report-{timestamp}.md

```markdown
# Review Report: {{FEATURE_NAME}}

## Scoped Files
{{List of reviewed files}}

## Spec Compliance
| Check | Status | Notes |
|-------|--------|-------|
| EARS Coverage | {{status}} | {{notes}} |
| Correctness | {{status}} | {{notes}} |
| Entity Fidelity | {{status}} | {{notes}} |
| ADR Compliance | {{status}} | {{notes}} |
| Rules Compliance | {{status}} | {{notes}} |
| Test Coverage | {{status}} | {{notes}} |
| Traceability | {{status}} | {{notes}} |

## Findings
| Severity | File | Issue |
|----------|------|-------|
| {{S}} | {{F}} | {{I}} |

## Verdict
- **{{Verdict}}** (APPROVE / REQUEST CHANGES / COMMENT)
```

## Phase Transition

This is the final phase. Once the report is written and presented, this skill is done. **Do not invoke any other skill yourself.** Tell the user (paraphrase as needed) based on the verdict:

- **APPROVE**: "Review verdict is APPROVE — `{feature}` is ready for PR / human review. Findings: {short summary}. Report saved to `review/{feature}/report-{timestamp}.md`."
- **REQUEST CHANGES**: "Review verdict is REQUEST CHANGES. The cited findings need to be fixed. Two paths: (1) fix manually using the report at `review/{feature}/report-{timestamp}.md`, then exit this chat, start a fresh session, and run `/sdlc-review {feature}` again; or (2) exit and start a fresh session, then run `/sdlc-implement {feature}` again with the report as input, then re-run `/sdlc-review {feature}`."
- **COMMENT**: "Review verdict is COMMENT. Findings are non-blocking; `{feature}` can proceed to PR with the noted caveats. Report saved to `review/{feature}/report-{timestamp}.md`."

After delivering this message, end your turn.

## Error Recovery

If the review session is interrupted:
- List `review/` to check if the report was written
- If not, re-read the spec artifacts and re-delegate
- Compare with any prior report to track progress

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `report-*.md` | `{root}/review/{feature}/` | Review report with findings (feature-scoped) |