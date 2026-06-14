---
name: sdlc-quickfix
description: Lightweight delta-format path for small changes (bug fixes, tweaks, single-property changes). Produces an ADDED/MODIFIED/REMOVED delta against existing specs, implements it, runs a focused review, and promotes the delta into the canonical spec by default.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-quickfix

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, writing the delta, delegating to a coding agent, performing the inline review, and promoting the delta. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. When this skill ends, deliver the Phase Transition message and stop.

For changes that don't justify the full pipeline — bug fixes, copy tweaks, error-message changes, single-property additions. Uses an `ADDED/MODIFIED/REMOVED` delta against existing specs, avoiding the failure mode of inflating a one-line fix into a multi-story spec. The delta is **promoted into the canonical spec by default** so the spec never silently drifts behind the code.

**Use this skill when:**
- The change touches one feature already specified.
- The change can be described in 1–3 EARS requirements.
- A full re-spec would be more paperwork than the change itself.

**Do NOT use this skill when:**
- Introducing a new feature → use `/sdlc-spec`.
- Changing architectural decisions → use `/sdlc-architect` and a new ADR.
- Touching multiple features → split or run the full pipeline.

## Conventions (read once, apply throughout)

- **Argument → slug**: the user invoked `/sdlc-quickfix <free-text>`. Slugify to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Feature Key**: read the `**Feature Key:**` from `.sdlc/specs/<slug>/spec.md`; all tags are key-namespaced (`@sdlc KEY:REQ-NNN`). See `.sdlc/CONVENTIONS.md`.
- **Artifact paths (migration-aware)**: read from `.sdlc/` (canonical); fall back to legacy roots if missing. Found legacy-only? Tell the user to run `/sdlc-migrate` first.
- **Approval**: the delta (Phase 3) and the inline-review verdict (Phase 5) each need an affirmative (Tier-1 for the delta — it changes requirements; Tier-3 for the review report). Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/specs/<slug>/spec.md` does not exist, this is not a quickfix — stop and recommend `/sdlc-spec <slug>`.
- **Timestamp**: get the current time via the runtime's shell. Never invent.
- **Retry cap**: if the agent fails the inline review (Phase 5), re-delegate at most **twice** (3 attempts total). Then stop and report the blocker.
- **Next-ID source of truth**: when assigning a new `REQ-*`/`UT-*`/etc., compute the next number from the **maximum ID across BOTH `spec.md`/`test-plan.md` AND every `quickfix-*.md`** under the feature dir. This prevents two unpromoted quickfixes from minting the same ID. (Promote-by-default makes unpromoted accumulation rare, but the rule holds regardless.)
- **Modification ownership**:
  - **Phase 4 (delegated agent)**: must NOT touch `spec.md` or `test-plan.md` — only code and test files.
  - **Phase 6 (you, the orchestrator)**: edit the canonical spec/test-plan yourself, after the agent returns and the inline review is clean.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if exists) — non-negotiable invariants
- `.sdlc/specs/<slug>/spec.md` — existing spec to delta against (read the Feature Key)
- `.sdlc/tests/<slug>/test-plan.md` — existing test plan
- existing `.sdlc/specs/<slug>/quickfix-*.md` — to compute the next free ID
- `.sdlc/requirements/entity-dictionary.md` — if the change touches an entity
- Source files in `src/` the change will touch (`git grep` the affected symbol)

### Phase 2: Scope Confirmation

State in one or two sentences exactly what is changing and what is not. Ask for confirmation. If the scope feels larger than 1–3 EARS additions/modifications, recommend the full pipeline instead.

### Phase 3: Write the Delta

#### Template: .sdlc/specs/{slug}/quickfix-{YYYY-MM-DDTHH-MM-SS}.md

```markdown
# Quickfix: {{ONE-LINE DESCRIPTION}}

**Date**: {{YYYY-MM-DD}}
**Feature**: {{slug}}  **Key**: {{KEY}}
**Trigger**: {{Bug ticket / user request / observation}}

## Behaviour Change Summary
{{One short paragraph: what the system did before, what it will do after, why.}}

## Requirements Delta
*Use canonical EARS (WHEN / WHILE / WHERE / IF…THEN / ubiquitous SHALL).*

### ADDED
- `REQ-{{next-N}}`: {{EARS statement}}

### MODIFIED
- `REQ-{{existing-N}}` — was: "{{old text}}"
- `REQ-{{existing-N}}` — now: "{{new text}}"

### REMOVED
- `REQ-{{existing-N}}` — reason: {{why}}

## Design Impact
*Delta table — list only properties this change actually affects; mark the rest "unchanged". (Unlike spec.md's Correctness section, a delta is allowed to state "unchanged" so the before/after is auditable.)*

| Property | Before | After |
|----------|--------|-------|
| {{Property touched}} | {{state}} | {{state}} |

## Test Delta

### ADDED
- `UT-{{next-N}}`: test_{{function}}_{{condition}} — covers {{KEY}}:REQ-{{N}}

### MODIFIED
- `UT-{{existing-N}}` — updated expectation: {{describe}}

### REMOVED
- `UT-{{existing-N}}` — reason: {{why}}

## Rules Compliance
- {{Each RULE-* plausibly touched, with a one-line note on why the change still complies. If none, "No applicable rules."}}

## Non-Regression Hints
{{Which existing tests must keep passing; which adjacent behaviours to verify manually.}}
```

### Phase 4: Single Delegation

Present the delta (Tier-1 approval). On approval, delegate. The delegation prompt is a **template**.

```
Implement the following quickfix delta against an existing codebase. Feature Key: {KEY}.

QUICKFIX DELTA (.sdlc/specs/{slug}/quickfix-{timestamp}.md):
[Inline the delta document]

PROJECT RULES (.sdlc/rules.md):
[Inline rules — refuse to violate any]

INSTRUCTIONS:
1. Apply only the changes in the delta. Do not refactor unrelated code.
2. Update the source files affected. Add `@sdlc {KEY}:REQ-{N}` (and/or `{KEY}:NFR-{N}`) inline tags on any function whose contract changed (comma-separated, one line).
3. Tests per the Test Delta:
   - ADDED → new tests with key-namespaced `COVERS:` headers.
   - MODIFIED → update bodies; keep names unless renamed; update COVERS if covered IDs changed.
   - REMOVED → delete the named test (and the file if it becomes empty).
4. Run the FULL test suite (not just new tests). Report non-regression failures.
5. Do NOT modify .sdlc/specs/{slug}/spec.md or .sdlc/tests/{slug}/test-plan.md — the orchestrator promotes after review.
6. Report: files touched, tests added/modified/removed by name, suite pass/fail per test, any rule overrides invoked.
```

### Phase 5: Inline Review

The quickfix path skips `/sdlc-review` (too small for a separate pass). Audit inline:
1. `git diff` shows only files mentioned in the report.
2. Run the test suite once more, locally.
3. Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` if present — confirm the new/changed tags are key-namespaced and reference real IDs.
4. Confirm `.sdlc/rules.md` is not violated.
5. If any check fails, re-delegate with the specific failure (retry cap = 2).

### Phase 6: Promote (default — opt-out)

**You (the orchestrator), not the delegated agent, do this.** Promotion is the **default**: keeping the spec current is the whole point of closing drift. Tell the user you're promoting unless they object: *"Promoting this delta into `spec.md` and `test-plan.md` so the canonical spec stays current. Say 'keep standalone' if you'd rather leave it as a delta-only record."*

Unless the user opts out:
1. **Update `.sdlc/specs/<slug>/spec.md`**:
   - ADDED → append with assigned REQ-* IDs (continue numbering; never recycle).
   - MODIFIED → rewrite the existing `REQ-NNN` line; add a trailing date comment if non-trivial.
   - REMOVED → keep the ID line as `REQ-NNN: REMOVED ({YYYY-MM-DD}) — {reason}`.
2. **Update `.sdlc/tests/<slug>/test-plan.md`** similarly for UT-*/IT-*/E2E-*/PBT-* IDs.
3. **Keep the dated quickfix file** — it remains the chronological record of what changed and when, even after promotion.

If the user opts out, the dated quickfix file is the durable record; multiple quickfixes accumulate as a chronological log. (Remember the next-ID rule scans these.)

## Phase Transition

This skill terminates the change in-place. Once the delta is applied, the suite passes, the inline review is clean, and the delta is promoted (or explicitly kept standalone), this skill is done. **Do not invoke any other skill yourself.** Tell the user:

> Quickfix applied for `<slug>`: delta at `.sdlc/specs/<slug>/quickfix-<ts>.md`, code and tests updated, suite passing, {promoted into spec.md / kept standalone}.
> - If the quickfix uncovered a deeper design issue, start a fresh session and run `/sdlc-spec <slug>` to regenerate the canonical spec.
> - Otherwise the change is complete and ready for PR.

After delivering this message, end your turn.

## Error Recovery

If interrupted mid-phase:
- List `.sdlc/specs/<slug>/quickfix-*.md` to find the in-progress delta.
- If the delta exists but no code changed, re-delegate from Phase 4.
- If code partially changed, prefer fixing forward over reverting — the delta is the source of truth.
- If code is done but promotion didn't happen, resume at Phase 6.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `quickfix-{timestamp}.md` | `{root}/.sdlc/specs/<slug>/` | Dated delta record (ADDED/MODIFIED/REMOVED) |
| Source diff | `{root}/src/` | Implementation of the delta with key-namespaced traceability tags |
| Test diff | `{root}/tests/` | Test changes per the Test Delta |
