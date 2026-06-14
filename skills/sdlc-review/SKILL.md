---
name: sdlc-review
description: Fresh-context review of implemented code against specifications. Validates spec compliance via the bundled validator plus an isolated code-review sub-agent.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-review

> **Execution model**: You (the LLM) execute the **Workflow** sections below — running the validator, delegating to a code-review agent, auditing its findings, and writing the report. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop.

Reviews implemented code against spec artifacts. Two layers: a **deterministic** pass (the bundled validator handles traceability, EARS, and ID hygiene) and a **judgement** pass (a fresh-context code-review sub-agent handles correctness, entity fidelity, ADR and rule compliance). The validator removes the old grep gymnastics and false-pass risk; the agent handles what a parser can't.

## Conventions (read once, apply throughout)

- **Argument → slug**: the user invoked `/sdlc-review <free-text>`. Slugify to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Feature Key**: read from `.sdlc/specs/<slug>/spec.md` — traceability is checked against key-namespaced tags (`{KEY}:REQ-*`).
- **Artifact paths (migration-aware)**: read from `.sdlc/` (canonical); fall back to legacy roots if missing. Found legacy-only? Tell the user to run `/sdlc-migrate` — the validator and keyed-tag checks assume the current layout, so a legacy project will show false traceability gaps until migrated.
- **Required input missing**: if `.sdlc/specs/<slug>/spec.md` is missing, stop and tell the user — there's nothing authoritative to review against. The test plan is read if present but is not strictly required (a spec produced by `/sdlc-document` may not have one yet).
- **Timestamp**: get the current timestamp via the runtime's shell (e.g. `date -u +%Y-%m-%dT%H-%M-%S`). Never invent one.
- **Output path is feature-scoped**: write to `.sdlc/reviews/<slug>/report-<timestamp>.md`. The report is the deliverable (Tier-3 — write and show, no approval needed).

## Workflow

### Phase 1: Input Discovery

Read (canonical, then legacy fallback):
- `.sdlc/rules.md` (if present) — every violation is a FAIL unless the Override Log records an approved exception
- `.sdlc/CONVENTIONS.md` (if present)
- `.sdlc/specs/<slug>/spec.md` — the source of truth (read the Feature Key)
- `.sdlc/tests/<slug>/test-plan.md` — expected coverage (if present)
- `.sdlc/requirements/entity-dictionary.md` — domain model
- `.sdlc/docs/architecture.md`, `.sdlc/docs/adr/*.md` — architecture decisions

### Phase 2: Deterministic Pass (Validator)

Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug> --strict` and capture the full output. This authoritatively covers **Traceability**, **EARS syntax**, and **ID hygiene** — record its ERROR/WARNING/INFO findings directly into the report rather than re-deriving them by hand. If the validator is absent (un-migrated project), fall back to the grep commands below and note the validator was unavailable:
- `grep -rnE "IMPLEMENTS: " src/`
- `grep -rnE "COVERS: " tests/`
- `grep -rnE "@sdlc [A-Z0-9_-]+:(REQ|NFR)-" src/ tests/`

### Phase 3: Identify Changed Files

Determine the feature's files (don't rely on `git diff HEAD` alone — it's empty once the work is committed):
- Files carrying this key's tags: `grep -rlE "{KEY}:(REQ|NFR)-" src/ tests/`
- Plus `git diff --name-only $(git merge-base HEAD main)...HEAD` if a base branch exists, or list `src/` and `tests/`.

### Phase 4: Judgement Pass (Fresh-Context Review)

Delegate to a code-review agent. Progressive disclosure: pass paths + inline the rules; let the agent read the rest. The block below is a **prompt template**.

```
Review the implementation of feature "{slug}" (Feature Key: {KEY}) against its specification.

READ THESE (your source of truth):
- .sdlc/specs/{slug}/spec.md          ← requirements, API surface, error handling, correctness, entities
- .sdlc/tests/{slug}/test-plan.md     ← expected test coverage (if present)
- .sdlc/requirements/entity-dictionary.md
- .sdlc/docs/architecture.md, .sdlc/docs/adr/*.md

PROJECT RULES (.sdlc/rules.md — inlined; any violation is a FAIL unless the Override Log covers it):
[Inline rules.md, or "No rules file present."]

CHANGED FILES:
[List files from Phase 3]

DETERMINISTIC VALIDATOR OUTPUT (already run — do not re-derive traceability; reason about whether each finding is real):
[Paste validator output from Phase 2]

For each check return PASS / FAIL / PARTIAL with file:line evidence:
- Correctness — each correctness property from spec.md is handled (round-trip, uniqueness, atomicity, validation, idempotency — only those the spec lists)
- Entity Fidelity — fields match the entity dictionary (names, types, constraints)
- ADR Compliance — code follows ADR decisions
- Rules Compliance — code respects every RULE-* (any violation needs an Override Log entry)
- Test Coverage — test-plan tests are implemented and passing
(Traceability and EARS are covered by the validator output above — confirm or dispute it, don't redo it.)
```

Hand the prompt to a fresh-context code-review sub-agent (a specialized one if your runtime exposes it, else general-purpose). The point is fresh context: the review must not inherit assumptions from the implementation conversation.

### Phase 5: Audit the Agent's Findings

A sanity audit, not a re-run:
- Confirm the agent addressed all five judgement checks. If any are missing, re-delegate with the gap called out.
- Spot-check 2–3 cited findings against the source files to verify the agent didn't hallucinate paths/lines.
- Treat any PASS rated without evidence as PARTIAL until verified.

### Phase 6: Report

Write to `.sdlc/reviews/<slug>/report-<YYYY-MM-DDTHH-MM-SS>.md` (colons → hyphens for filesystem safety).

#### Template

```markdown
# Review Report: {{FEATURE_NAME}} ({{KEY}})

## Scoped Files
{{List of reviewed files}}

## Validator Summary
{{N errors, M warnings, K info — paste key findings}}

## Spec Compliance
| Check | Status | Notes |
|-------|--------|-------|
| Traceability (validator) | {{status}} | {{notes}} |
| EARS Syntax (validator) | {{status}} | {{notes}} |
| Correctness | {{status}} | {{notes}} |
| Entity Fidelity | {{status}} | {{notes}} |
| ADR Compliance | {{status}} | {{notes}} |
| Rules Compliance | {{status}} | {{notes}} |
| Test Coverage | {{status}} | {{notes}} |

## Findings
| Severity | File | Issue |
|----------|------|-------|
| {{S}} | {{F}} | {{I}} |

## Verdict
- **{{Verdict}}** (APPROVE / REQUEST CHANGES / COMMENT)
```

**Verdict mapping** (deterministic — don't freelance):
- **REQUEST CHANGES** if any validator ERROR, any FAIL check, or any rule violation without an Override Log entry.
- **COMMENT** if no blockers but there are non-blocking findings (validator WARNINGs, PARTIALs, style notes).
- **APPROVE** if all checks PASS and the validator is clean.

## Phase Transition

This is the final phase. Once the report is written and presented, this skill is done. **Do not invoke any other skill yourself.** Tell the user based on the verdict:

- **APPROVE**: "Verdict APPROVE — `<slug>` is ready for PR. Findings: {summary}. Report: `.sdlc/reviews/<slug>/report-<ts>.md`."
- **REQUEST CHANGES**: "Verdict REQUEST CHANGES. Two paths: (1) fix manually using the report, then start a fresh session and re-run `/sdlc-review <slug>`; or (2) start a fresh session and run `/sdlc-implement <slug>` again with the report as input, then re-review."
- **COMMENT**: "Verdict COMMENT — non-blocking; `<slug>` can proceed to PR with the noted caveats. Report: `.sdlc/reviews/<slug>/report-<ts>.md`."

After delivering this message, end your turn.

## Error Recovery

If the review session is interrupted:
- List `.sdlc/reviews/<slug>/` to check if the report was written
- If not, re-read the spec artifacts, re-run the validator, and re-delegate
- Compare with any prior report to track progress

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `report-*.md` | `{root}/.sdlc/reviews/<slug>/` | Review report with findings (feature-scoped) |
