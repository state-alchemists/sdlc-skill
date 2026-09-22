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

- **Conventions**: read `.sdlc/CONVENTIONS.md` — paths, ID scheme, file roles, approval tiers.
- **Layout**: read `.sdlc/config.json` for this project's source and test roots, and `.sdlc/ANNOTATION.md` before writing or editing any traceability header.
- **Template**: fill `.sdlc/templates/quickfix.md`.
- **Argument → slug**: slugify to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Required input**: no existing `spec.md` for the feature? There is nothing to delta against — tell the user to run `/sdlc-spec <feature>` (new feature) or `/sdlc-adopt` (existing code, no spec).
- **ID rules**: continue numbering from the highest existing ID; never renumber or recycle. A removed requirement keeps its ID and its text **begins** `REMOVED ({date}) — {reason}`, directly after the `(AC-NNN)` citation if it has one — anything else between the ID and `REMOVED` leaves it active.
- **Retry cap**: 2 re-delegations.

## Workflow

### Phase 1: Input Discovery

Read `.sdlc/rules.md`, `.sdlc/specs/<slug>/spec.md` (the Feature Key, the requirements to delta against, and the `## Test Plan` section), `.sdlc/requirements/entity-dictionary.md` if an entity is touched, and the source files the change will touch (`git grep` the affected symbol).

**Next free ID**: `spec.md` holds it, because a promoted delta writes its IDs there. Also read any `.sdlc/specs/<slug>/quickfix-*.md` whose header says `**Promoted**: no` — those IDs exist nowhere else. Files under `.sdlc/specs/<slug>/archive/` are promoted history; skip them.

### Phase 2: Scope Confirmation

State in one or two sentences exactly what is changing and what is not. Ask for confirmation. If the scope exceeds 1–3 EARS additions or modifications, recommend the full pipeline instead.

### Phase 3: Write the Delta

Fill `.sdlc/templates/quickfix.md` into `.sdlc/specs/<slug>/quickfix-<TIMESTAMP>.md`, where `<TIMESTAMP>` is the output of `date -u +%Y-%m-%dT%H-%M-%SZ` — run it, do not invent it (see `.sdlc/CONVENTIONS.md` § Dates and timestamps). Requirements use canonical EARS with uppercase keywords. The Test Delta lists the `UT-*`/`IT-*` rows that will be promoted into the spec's `## Test Plan`.

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
2. Update the affected source files. Add `@sdlc {KEY}:REQ-{N}` inline tags on any function whose contract changed (comma-separated, one line). Follow .sdlc/ANNOTATION.md for comment syntax and header placement — a header above a shebang or an encoding line breaks the file.
3. Tests per the Test Delta:
   - ADDED → new tests with key-namespaced COVERS: headers.
   - MODIFIED → update bodies; keep names unless renamed; update COVERS if the covered IDs changed.
   - REMOVED → delete the named test (and the file if it becomes empty).
4. For a REMOVED requirement, also strip its traceability from the source: drop its ID from every `IMPLEMENTS:` header and delete its `@sdlc` inline tags. A tag pointing at a retired ID is a dangling-tag ERROR.
5. Run the FULL test suite, not just the new tests. Report non-regression failures.
6. Do NOT modify .sdlc/specs/{slug}/spec.md — the orchestrator promotes after review.
7. Report: files touched, tests added/modified/removed by name, suite pass/fail per test, any rule overrides invoked.
```

### Phase 5: Inline Review

The quickfix path skips `/sdlc-review` — too small for a separate pass. Audit inline:
1. `git diff` shows only the files named in the report.
2. Run the test suite yourself.
3. Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` — confirm new tags are key-namespaced and resolve.
4. Confirm no rule is violated.
5. On failure, re-delegate with the specific failure (cap 2).

### Phase 6: Promote

**You do this, not the delegated agent.** Promotion is the recommended default — keeping the spec current is the point — but `spec.md` is an existing spec, and editing one is **Tier-1**: ask, and wait for an affirmative. Silence is not consent (see `.sdlc/CONVENTIONS.md`). Say: *"I recommend promoting this delta into `spec.md` so the spec stays current — approve? Or say 'keep standalone' to leave it as a delta-only record."*

On approval, update `.sdlc/specs/<slug>/spec.md`:
- **ADDED** → append with the assigned `REQ-*` IDs; add the matching rows to the `## Test Plan` section.
- **MODIFIED** → rewrite the existing `REQ-NNN` line; update its test-plan rows.
- **REMOVED** → keep the ID line, its text beginning `REMOVED (<output of `date +%Y-%m-%d`>) — {reason}`; remove its test-plan rows.

**Keep the dated quickfix file** either way — it is the chronological record of what changed and when. Set its `**Promoted**:` header to match what happened. A promoted delta's IDs now live in `spec.md`, so it may be moved to `.sdlc/specs/<slug>/archive/` to keep the feature directory readable; a standalone one stays put, because it is the only record of its IDs.

## Phase Transition

> Quickfix applied for `<slug>`: delta at `.sdlc/specs/<slug>/quickfix-<ts>.md`, code and tests updated, suite passing, {promoted into spec.md / kept standalone}.

Then deliver the action block (see CONVENTIONS.md § Session handoff). A quickfix is usually complete in itself, so the common block has one item:

```
Next:
  [ ] open the PR for <slug>            the change is complete
```

Offer an alternative only when the work justified it: if the fix uncovered a deeper design issue, `/sdlc-spec <slug>` to regenerate the spec; if a test was added or changed, `/sdlc-review <slug>` to verify it against the spec. Do not list both unconditionally — name the one the work actually calls for.

After delivering this message, end your turn.

## Error Recovery

Interrupted: list `.sdlc/specs/<slug>/quickfix-*.md` to find the in-progress delta. Delta exists but no code changed → re-delegate from Phase 4. Code partially changed → fix forward; the delta is the source of truth. Code done, promotion missing → resume at Phase 6.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `quickfix-{ts}.md` | `.sdlc/specs/<slug>/` | Dated delta record (ADDED/MODIFIED/REMOVED) |
| Source + test diff | the project's source and test roots | The change, with key-namespaced tags |
| `spec.md` | `.sdlc/specs/<slug>/` | Updated in place when the delta is promoted |
