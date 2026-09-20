---
name: sdlc-quickfix
description: Lightweight delta path for small changes (bug fixes, tweaks, single-property changes). Writes an ADDED/MODIFIED/REMOVED delta against an existing spec, implements it, reviews inline, and promotes the delta into the spec by default.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-quickfix

> **Execution model**: you execute the Workflow below — reading files, writing the delta, delegating to a coding agent, reviewing inline, promoting. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

For changes that do not justify the full pipeline. Uses an `ADDED/MODIFIED/REMOVED` delta against an existing spec, avoiding the failure mode of inflating a one-line fix into a multi-story spec. The delta is **promoted into the spec by default**, so the spec never drifts behind the code.

**Use this skill when** the change touches one already-specified feature, fits in 1–3 EARS requirements, and needs no new architecture. Otherwise use `/sdlc-spec`.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md`.
- **Template**: fill `.sdlc/templates/quickfix.md`.
- **Argument → slug**: slugify to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Required input**: no existing `spec.md` for the feature? There is nothing to delta against — tell the user to run `/sdlc-spec <feature>` (new feature) or `/sdlc-adopt` (existing code, no spec).
- **ID rules**: continue numbering from the highest existing ID; never renumber or recycle. A removed requirement keeps its ID and its text **begins** `REMOVED ({date}) — {reason}`.
- **Retry cap**: 2 re-delegations.

## Workflow

### Phase 1: Input Discovery

Read `.sdlc/rules.md`, `.sdlc/specs/<slug>/spec.md` (the Feature Key, the requirements to delta against, and the `## Test Plan` section), any existing `.sdlc/specs/<slug>/quickfix-*.md` (to compute the next free IDs), `.sdlc/requirements/entity-dictionary.md` if an entity is touched, and the source files the change will touch (`git grep` the affected symbol).

### Phase 2: Scope Confirmation

State in one or two sentences exactly what is changing and what is not. Ask for confirmation. If the scope exceeds 1–3 EARS additions or modifications, recommend the full pipeline instead.

### Phase 3: Write the Delta

Fill `.sdlc/templates/quickfix.md` into `.sdlc/specs/<slug>/quickfix-{YYYY-MM-DDTHH-MM-SS}.md`. Requirements use canonical EARS with uppercase keywords. The Test Delta lists the `UT-*`/`IT-*` rows that will be promoted into the spec's `## Test Plan`.

### Phase 4: Single Delegation

Present the delta (**Tier-1** approval). On approval, delegate — the block below is a prompt template.

```
Implement the following quickfix delta against an existing codebase. Feature Key: {KEY}.

QUICKFIX DELTA (.sdlc/specs/{slug}/quickfix-{timestamp}.md):
[Inline the delta document]

PROJECT RULES (.sdlc/rules.md):
[Inline rules — refuse to violate any]

INSTRUCTIONS:
1. Apply only the changes in the delta. Do not refactor unrelated code.
2. Update the affected source files. Add `@sdlc {KEY}:REQ-{N}` inline tags on any function whose contract changed (comma-separated, one line).
3. Tests per the Test Delta:
   - ADDED → new tests with key-namespaced COVERS: headers.
   - MODIFIED → update bodies; keep names unless renamed; update COVERS if the covered IDs changed.
   - REMOVED → delete the named test (and the file if it becomes empty).
4. Run the FULL test suite, not just the new tests. Report non-regression failures.
5. Do NOT modify .sdlc/specs/{slug}/spec.md — the orchestrator promotes after review.
6. Report: files touched, tests added/modified/removed by name, suite pass/fail per test, any rule overrides invoked.
```

### Phase 5: Inline Review

The quickfix path skips `/sdlc-review` — too small for a separate pass. Audit inline:
1. `git diff` shows only the files named in the report.
2. Run the test suite yourself.
3. Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` — confirm new tags are key-namespaced and resolve.
4. Confirm no rule is violated.
5. On failure, re-delegate with the specific failure (cap 2).

### Phase 6: Promote

**You do this, not the delegated agent.** Promotion is the default — keeping the spec current is the point. Say: *"Promoting this delta into `spec.md` so the spec stays current. Say 'keep standalone' if you'd rather leave it as a delta-only record."*

Unless the user opts out, update `.sdlc/specs/<slug>/spec.md`:
- **ADDED** → append with the assigned `REQ-*` IDs; add the matching rows to the `## Test Plan` section.
- **MODIFIED** → rewrite the existing `REQ-NNN` line; update its test-plan rows.
- **REMOVED** → keep the ID line, its text beginning `REMOVED ({YYYY-MM-DD}) — {reason}`; remove its test-plan rows.

**Keep the dated quickfix file** either way — it is the chronological record of what changed and when, and the next-ID scan reads it.

## Phase Transition

> Quickfix applied for `<slug>`: delta at `.sdlc/specs/<slug>/quickfix-<ts>.md`, code and tests updated, suite passing, {promoted into spec.md / kept standalone}.
> - If the quickfix uncovered a deeper design issue, start a fresh session and run `/sdlc-spec <slug>` to regenerate the spec.
> - Otherwise the change is complete and ready for PR.

After delivering this message, end your turn.

## Error Recovery

Interrupted: list `.sdlc/specs/<slug>/quickfix-*.md` to find the in-progress delta. Delta exists but no code changed → re-delegate from Phase 4. Code partially changed → fix forward; the delta is the source of truth. Code done, promotion missing → resume at Phase 6.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `quickfix-{ts}.md` | `.sdlc/specs/<slug>/` | Dated delta record (ADDED/MODIFIED/REMOVED) |
| Source + test diff | `src/`, `tests/` | The change, with key-namespaced tags |
| `spec.md` | `.sdlc/specs/<slug>/` | Updated in place when the delta is promoted |
