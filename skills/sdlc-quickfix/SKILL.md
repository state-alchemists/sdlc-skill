---
name: sdlc-quickfix
description: Lightweight delta-format path for small changes (bug fixes, tweaks, single-property changes). Produces an ADDED/MODIFIED/REMOVED delta against existing specs, implements it, and runs a focused review — all without invoking the full spec→test-plan→implement→review pipeline.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-quickfix

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, writing the delta, delegating to a coding agent, and performing the inline review. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

For changes that don't justify the full pipeline — bug fixes, copy tweaks, error-message changes, single-property additions. Uses an `ADDED/MODIFIED/REMOVED` delta format against existing specs, avoiding the common failure mode of inflating a one-line fix into a multi-story spec.

**Use this skill when:**
- The change touches one feature already specified.
- The change can be described in 1–3 EARS requirements.
- A full re-spec would be more paperwork than the change itself.

**Do NOT use this skill when:**
- Introducing a new feature → use `/sdlc-spec`.
- Changing architectural decisions → use `/sdlc-architect` and a new ADR.
- Touching multiple features → split or run the full pipeline.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-quickfix <free-text>`. Use it verbatim as `{feature}`. If missing, ask.
- **Approval**: get an explicit affirmative on the delta in Phase 3, and again on the inline-review verdict in Phase 5. Silence or vague replies are change requests.
- **Required input missing**: if `.sdlc/specs/{feature}/spec.md` does not exist, this is not a quickfix — stop and recommend `/sdlc-spec {feature}` to plan the feature first.
- **Timestamp**: get the current time via the runtime's shell (e.g. `date -u +%Y-%m-%dT%H-%M-%S`). Never invent a timestamp.
- **Retry cap**: if the delegated agent fails the inline review (Phase 5), re-delegate at most **twice**. After the third total attempt, stop and report the blocker.
- **Modification ownership**:
  - **Phase 4 (delegated agent)**: must NOT touch `.sdlc/specs/{feature}/spec.md` or `.sdlc/tests/{feature}/test-plan.md`. The agent only writes code and test files.
  - **Phase 6 (you, the orchestrating LLM)**: if and only if the user explicitly opts in to promotion, **you** edit the canonical spec/test-plan files yourself, after the agent has returned and the inline review is clean.

## Workflow

### Phase 1: Input Discovery

Read:
- `.sdlc/rules.md` (if exists) — non-negotiable invariants
- `.sdlc/specs/{feature}/spec.md` — existing spec to delta against (requirements + design in one file)
- `.sdlc/tests/{feature}/test-plan.md` — existing test plan to delta against
- `.sdlc/requirements/entity-dictionary.md` — if the change touches a domain entity
- Source files in `src/` that the change will touch (use `git grep` for the affected symbol)

### Phase 2: Scope Confirmation

State to the user, in one or two sentences, exactly what is changing and what is not. Ask for confirmation before proceeding. If the scope feels larger than 1–3 EARS additions or modifications, recommend the full pipeline instead.

### Phase 3: Write the Delta

#### Template: .sdlc/specs/{feature}/quickfix-{YYYY-MM-DDTHH-MM-SS}.md

```markdown
# Quickfix: {{ONE-LINE DESCRIPTION}}

**Date**: {{YYYY-MM-DD}}
**Feature**: {{feature}}
**Trigger**: {{Bug ticket / user request / observation}}

## Behaviour Change Summary
{{One short paragraph: what the system did before, what it will do after, why.}}

## Requirements Delta

### ADDED
- `REQ-{{next-N}}`: {{EARS statement}}

### MODIFIED
- `REQ-{{existing-N}}` — was: "{{old text}}"
- `REQ-{{existing-N}}` — now: "{{new text}}"

### REMOVED
- `REQ-{{existing-N}}` — reason: {{why}}

## Design Impact
| Property | Before | After |
|----------|--------|-------|
| Round-Trip | {{state}} | {{state}} |
| Uniqueness | {{state}} | {{state}} |
| Atomicity | {{state}} | {{state}} |
| Validation | {{state}} | {{state}} |
| Idempotency | {{state}} | {{state}} |

Mark `N/A — unchanged` for properties the quickfix does not touch.

## Test Delta

### ADDED
- `UT-{{next-N}}`: test_{{function}}_{{condition}} — covers REQ-{{N}}

### MODIFIED
- `UT-{{existing-N}}` — updated expectation: {{describe}}

### REMOVED
- `UT-{{existing-N}}` — reason: {{why}}

## Rules Compliance
- {{Each RULE-* that could plausibly be touched, with a one-line note on why the change still complies. If no rules apply, write "No applicable rules."}}

## Non-Regression Hints
{{Which existing tests must continue to pass. Which adjacent behaviours could break and should be verified manually.}}
```

### Phase 4: Single-Shot Implementation

Present the delta to the user. On approval, delegate the implementation. The delegation prompt is a **template** — replace placeholders with the file content you just generated.

```
Implement the following quickfix delta against an existing codebase.

QUICKFIX DELTA (.sdlc/specs/{feature}/quickfix-{timestamp}.md):
[Inline the delta document]

PROJECT RULES (.sdlc/rules.md):
[Inline rules — refuse to violate any]

INSTRUCTIONS:
1. Apply only the changes described in the delta. Do not refactor or modernize unrelated code.
2. Update the source files affected. Add `@sdlc REQ-{N}` (and/or `NFR-{N}`) inline tags on any function whose contract changed. Use comma-separated IDs on one line for multi-ID tags.
3. Add/update tests per the Test Delta:
   - **ADDED** tests → write new tests with `COVERS:` headers referencing the new/modified REQ-* / NFR-* IDs.
   - **MODIFIED** tests → update the existing test bodies; keep their names unless the delta renames them; update `COVERS:` headers if the covered IDs changed.
   - **REMOVED** tests → delete the named test function (and the test file if it becomes empty).
4. Run the full test suite (not just the new tests). Report any non-regression failures.
5. Do NOT modify `.sdlc/specs/{feature}/spec.md` or `.sdlc/tests/{feature}/test-plan.md`. The quickfix file IS the change record. The orchestrating skill (not you) may promote later, if the user asks.
6. Report: files touched, tests added/modified/removed (by name), test suite pass/fail per test, any rule overrides invoked.
```

Hand this prompt to a coding sub-agent via whatever delegation mechanism your runtime exposes.

### Phase 5: Inline Review

The quickfix path skips `/sdlc-review` because it is too small to warrant a separate review pass. Do the audit inline:

1. Verify the agent's report matches the file system: `git diff` shows only files mentioned in the report.
2. Run the test suite once more, locally.
3. Spot-check that `IMPLEMENTS:`/`COVERS:`/`@sdlc REQ-*` tags reference IDs that exist in the delta.
4. Confirm `.sdlc/rules.md` is not violated.
5. If any check fails, re-delegate with the specific failure — do not switch to the full `/sdlc-implement` flow inside this skill (that's a different mental model; the user can invoke it separately if they want to escalate).

### Phase 6: Promote (Optional, opt-in only)

**You (the orchestrating LLM), not the delegated agent, do this step.** Ask the user explicitly: "Promote this delta into `.sdlc/specs/{feature}/spec.md` and `.sdlc/tests/{feature}/test-plan.md`, or leave the quickfix as a standalone change record?"

If the user opts in:
1. **Update `.sdlc/specs/{feature}/spec.md`**:
   - ADDED requirements → append with their assigned REQ-* IDs (continue numbering, do not recycle).
   - MODIFIED requirements → rewrite the existing REQ-NNN line; mention the change date in a trailing comment if non-trivial.
   - REMOVED requirements → keep the ID line but mark as `REQ-NNN: REMOVED ({YYYY-MM-DD}) — {reason}`. Do not reuse the number.
2. **Update `.sdlc/tests/{feature}/test-plan.md`** similarly for UT-*, IT-*, E2E-*, PBT-* IDs.
3. **Keep the dated quickfix file** — do not delete it. It remains the chronological record of what changed and when, even after promotion.

If the user declines: the dated quickfix file IS the durable record. Multiple quickfixes accumulate as a chronological log under `.sdlc/specs/{feature}/quickfix-*.md`.

## Phase Transition

This skill terminates the change in-place — there is no next phase. Once the delta is applied, the test suite passes, and the inline review is clean, this skill is done. **Do not invoke any other skill yourself.** Tell the user (paraphrase as needed):

> Quickfix applied for `{feature}`: delta recorded at `.sdlc/specs/{feature}/quickfix-{timestamp}.md`, code and tests updated, test suite passing.
> - If the quickfix uncovered a deeper design issue, exit this chat and start a fresh session, then run `/sdlc-spec {feature}` to regenerate the canonical spec.
> - Otherwise the change is complete and ready for PR.

After delivering this message, end your turn.

## Error Recovery

If interrupted mid-phase:
- List `.sdlc/specs/{feature}/quickfix-*.md` to find the in-progress delta.
- If the delta exists but no code was changed, re-delegate from Phase 4.
- If code was partially changed, prefer fixing forward over reverting — the delta document is the source of truth.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `quickfix-{timestamp}.md` | `{root}/.sdlc/specs/{feature}/` | Dated delta record (ADDED/MODIFIED/REMOVED) |
| Source diff | `{root}/src/` | Implementation of the delta with traceability tags |
| Test diff | `{root}/tests/` | Test changes per the Test Delta |
