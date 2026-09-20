---
name: sdlc-review
description: Fresh-context review of implemented code against its spec. Runs the deterministic validator, then delegates judgement checks to an isolated review sub-agent, and writes a report.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-review

> **Execution model**: you execute the Workflow below — running the validator, delegating to a review agent, auditing its findings, writing the report. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

Two layers: a **deterministic** pass (the validator covers traceability, EARS, and ID hygiene) and a **judgement** pass (a fresh-context sub-agent covers correctness, entity fidelity, ADR and rule compliance). The validator removes grep gymnastics and false passes; the agent handles what a parser cannot.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md`.
- **Template**: fill `.sdlc/templates/review-report.md`.
- **Argument → slug**: slugify to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Fresh context is the point**: the judgement pass must not inherit assumptions from the implementation conversation.
- Reviews are **Tier-3** — the report is the deliverable, not a source mutation. No approval needed to write it.

## Workflow

### Phase 1: Input Discovery

Read `.sdlc/rules.md` (every violation is a FAIL unless the Override Log records an exception), `.sdlc/CONVENTIONS.md`, `.sdlc/specs/<slug>/spec.md` (source of truth — read the Feature Key and the `## Test Plan` section), `.sdlc/requirements/entity-dictionary.md`, `.sdlc/docs/architecture.md`, and `.sdlc/docs/adr/*.md`.

### Phase 2: Deterministic Pass

Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug> --strict` and capture the full output. This authoritatively covers **traceability**, **EARS syntax**, and **ID hygiene** — record its findings in the report rather than re-deriving them. Findings are scoped to this feature while every spec stays parsed, so a finding about another feature's key is a real defect, not scoping noise. If the validator is absent, note that, tell the user to run `/sdlc-init`, and fall back to:
- `grep -rnE "IMPLEMENTS: " src/`
- `grep -rnE "COVERS: " tests/`
- `grep -rnE "@sdlc [A-Z0-9_-]+:(REQ|NFR)-" src/ tests/`

### Phase 3: Identify Changed Files

`git diff HEAD` is empty once the work is committed, so scope by tag and by branch:
- `grep -rlE "{KEY}:(REQ|NFR)-" src/ tests/`
- plus `git diff --name-only $(git merge-base HEAD main)...HEAD` if a base branch exists, else list `src/` and `tests/`.

### Phase 4: Judgement Pass

Delegate to a fresh-context code-review agent. Pass paths, inline the rules, let the agent read the rest. The block below is a prompt template.

```
Review the implementation of feature "{slug}" (Feature Key: {KEY}) against its specification.

READ THESE (your source of truth):
- .sdlc/specs/{slug}/spec.md          ← requirements, design, and the test plan
- .sdlc/requirements/entity-dictionary.md
- .sdlc/docs/architecture.md, .sdlc/docs/adr/*.md

PROJECT RULES (.sdlc/rules.md — inlined; any violation is a FAIL unless the Override Log covers it):
[Inline rules.md, or "No rules file present."]

CHANGED FILES:
[List from Phase 3]

DETERMINISTIC VALIDATOR OUTPUT (already run — do not re-derive traceability; reason about whether each finding is real):
[Paste Phase 2 output]

For each check return PASS / FAIL / PARTIAL with file:line evidence:
- Correctness — each property in the spec's Correctness section is actually handled
- Entity Fidelity — field names, types, and constraints match the entity dictionary
- ADR Compliance — the code follows the recorded decisions
- Rules Compliance — every RULE-* is respected (a violation needs an Override Log entry)
- Test Coverage — the spec's Test Plan rows exist as tests and pass
(Traceability and EARS are covered by the validator output above — confirm or dispute it, do not redo it.)
```

### Phase 5: Audit the Findings

A sanity audit, not a re-run:
- Confirm all five judgement checks were addressed; re-delegate if one is missing.
- Spot-check 2–3 cited findings against the source to verify the agent did not hallucinate paths or lines.
- Treat any PASS asserted without evidence as PARTIAL until verified.

### Phase 6: Report

Write `.sdlc/reviews/<slug>/report-<YYYY-MM-DDTHH-MM-SS>.md` from `.sdlc/templates/review-report.md` (colons → hyphens for filesystem safety).

**Verdict mapping** — deterministic, do not freelance:
- **REQUEST CHANGES** — any validator ERROR, any FAIL check, or any rule violation without an Override Log entry.
- **COMMENT** — no blockers, but validator WARNINGs, PARTIALs, or style notes exist.
- **APPROVE** — all checks PASS and the validator is clean.

## Phase Transition

Tell the user based on the verdict:
- **APPROVE**: "Verdict APPROVE — `<slug>` is ready for PR. Report: `.sdlc/reviews/<slug>/report-<ts>.md`."
- **REQUEST CHANGES**: "Verdict REQUEST CHANGES. Either fix manually using the report and re-run `/sdlc-review <slug>` in a fresh session, or start a fresh session and run `/sdlc-implement <slug>` with the report as input, then re-review."
- **COMMENT**: "Verdict COMMENT — non-blocking; `<slug>` can proceed to PR with the noted caveats. Report: `.sdlc/reviews/<slug>/report-<ts>.md`."

After delivering this message, end your turn.

## Error Recovery

Interrupted: list `.sdlc/reviews/<slug>/`. No report → re-read the spec, re-run the validator, re-delegate. Compare against any prior report to track progress.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `report-*.md` | `.sdlc/reviews/<slug>/` | Findings, per-check status, and verdict |
