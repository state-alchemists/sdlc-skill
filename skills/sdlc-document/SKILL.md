---
name: sdlc-document
description: Reverse-engineer specs from existing code. Use when specs have drifted from implementation, or when adopting SDLC on a brownfield codebase that has no specs at all.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-document

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading source files, reverse-engineering specs, diffing against any prior specs, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. When this skill ends, deliver the Phase Transition message and stop.

Closes the drift loop in the opposite direction from the other skills: instead of code-from-spec, this produces **spec-from-code**. Use it for brownfield adoption and for drift recovery when implementation has diverged from existing specs.

**Use this skill when:**
- The code for a feature exists but has **no spec at all** — including codebases with no `.sdlc/` directory (brownfield onboarding from zero).
- The code has **old-format specs** (`requirements.md` + `design.md` from before the spec-merge) — the skill detects these and offers migration.
- A `/sdlc-review` flagged drift between code and current-format `spec.md`, and you want to regenerate the spec to match reality before deciding which side is wrong.
- An external contractor delivered code without specs and you need to retrofit them.

**Do NOT use this skill when:**
- You want to *plan* a new feature → use `/sdlc-spec`.
- You want to fix a small bug → use `/sdlc-quickfix`.

> **Two kinds of migration, don't confuse them.** *Layout* migration (artifacts at legacy roots `docs/`, `requirements/`, `specs/` instead of `.sdlc/`) is handled by `/sdlc-migrate` — if you detect a legacy layout, recommend that first. *Format* migration (a feature's `requirements.md` + `design.md` → merged `spec.md`) is handled here, in Phase 2a.

## Conventions (read once, apply throughout)

- **Argument → scope**: the user invoked `/sdlc-document <free-text>`. It may be a feature name, a directory path, a file glob, or a git ref range. If missing, ask (Phase 1).
- **`<slug>` resolution**: derive the feature slug from the scope: if scope is a feature name, slugify it; if it's a path/glob, ask "Under which feature slug should I write the specs?"
- **Feature Key**: the reverse-engineered `spec.md` declares `**Feature Key:** <KEY>` (uppercase, globally unique; default = uppercased slug). Reverse-engineered traceability tags you suggest are key-namespaced. See `.sdlc/CONVENTIONS.md`.
- **Artifact paths (migration-aware)**: read from `.sdlc/` (canonical); fall back to legacy roots. If you detect a legacy *layout*, recommend `/sdlc-migrate` before proceeding (so the new `spec.md` lands in the right place and isn't split-brain).
- **Approval**: writing a fresh spec is Tier-2 (present, single affirmative). **Overwriting an existing spec is Tier-1** — the affirmative must follow a presented diff (Phase 6). Never overwrite blindly.
- **Required input present**: at least one source or test file must exist under the chosen scope. If empty, stop and ask the user to refine it.
- **Timestamp**: get the current time via the runtime's shell. Never invent.
- **Canonical EARS**: reverse-engineer requirements in canonical EARS (ubiquitous / WHEN / WHILE / WHERE / IF…THEN). Do not emit the deprecated dialect.
- **Determinism caveat**: LLM output isn't deterministic. Re-runs may produce subtly different specs. Manual edits between runs are at risk — Phase 6 addresses this with a diff gate.

## Workflow

### Phase 1: Scope Selection

Ask one question: **what is the scope?** Acceptable answers: a feature name, a directory path (`src/auth/`), a file glob (`src/payments/**/*.py`), or a git commit range. Reject vague scopes ("the whole project") — break them into multiple runs.

### Phase 2: Input Discovery

Read, in order:
1. All source files in scope (`git ls-files <scope>` to enumerate).
2. All test files for the same scope (they encode intended behaviour).
3. `.sdlc/rules.md` (canonical or legacy `rules.md`) if present — if neither `.sdlc/` nor `AGENTS.md` exists, treat as a **zero-baseline** run (skip rules; note the greenfield-on-brownfield situation).
4. `.sdlc/CONVENTIONS.md` if present.
5. `.sdlc/requirements/entity-dictionary.md` if present — else entities are inferred from source/tests alone.
6. Existing specs at `.sdlc/specs/<slug>/` (or legacy `specs/<slug>/`):
   - `spec.md` exists → current format. Use in Phase 5.
   - `requirements.md` and/or `design.md` exist but no `spec.md` → **old format**. Go to Phase 2a.
   - neither → no prior specs. Skip Phase 5; write fresh in Phase 6.

### Phase 2a: Old-Format Detection and Migration

If `requirements.md` and/or `design.md` exist but `spec.md` does not, the feature predates the spec-merge. Tell the user:

> Found old-format specs (`requirements.md` / `design.md`). I can: **(a) use them as the baseline** — read both, treat the combined content as the existing spec for the diff, write the new `spec.md`; **(b) ignore them** — start fresh from code; or **(c) abort**.

Act on the answer:
- **Use as baseline**: read both, combine into a unified mental model, use as the "existing spec" for Phase 5/6 diffs. After writing `spec.md`, ask: "Remove the old `requirements.md` and `design.md` now, or keep for reference?" The drift report notes: `Baseline: old-format specs (requirements.md + design.md)`.
- **Ignore**: proceed as if no prior specs; warn once: "Old-format specs were left untouched — remove or archive when ready."
- **Abort**: stop. Write nothing.

### Phase 3: Extract Behaviour

For each public function/class/handler/endpoint in scope, identify: **Trigger** (HTTP/queue/CLI/cron), **Inputs**, **Outputs / side effects**, **Failure modes**, **Invariants** (what tests assert as always true). Translate each into canonical EARS — prefer the strongest applicable form:

| Observation | EARS form |
|-------------|-----------|
| Hard-coded constraint enforced on every path | Ubiquitous: The `<system>` SHALL `<response>`. |
| Behaviour triggered by an HTTP/event/CLI action | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| Behaviour that holds while in a particular state | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Behaviour tied to an optional/configured feature or flag | WHERE `<feature included>`, the `<system>` SHALL `<response>`. |
| Error / guard / invalid-input handling | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |

Number new requirements continuing from any existing `REQ-*` IDs. **Never recycle IDs** — a disappeared requirement is marked REMOVED in the diff, its number not reused.

### Phase 4: Infer Design Properties

For each correctness property, inspect the code and write a one-sentence finding:

| Property | What to look for |
|----------|------------------|
| Round-Trip | Serialization symmetry (encode/decode, save/load) |
| Uniqueness | Unique constraints in DB/migrations, dedup logic, idempotency keys |
| Atomicity | Transactions, locks, all-or-nothing branches |
| Validation | Input checks before processing (schema validation, guard clauses) |
| Idempotency | Safe-to-retry behaviour, deterministic re-execution |

If the code does not address a property, state it: `Not enforced — recommend adding {test/check}`. Do not invent compliance.

### Phase 5: Diff Against Existing Specs

If `spec.md` (or the old-format baseline from 2a) exists, show a three-column diff: **Old REQ-* / New REQ-* / Status (UNCHANGED / MODIFIED / ADDED / REMOVED-from-code)**.
- `REMOVED-from-code` — spec claims it but code no longer implements it → flag for user decision (re-implement, or drop from spec).
- `ADDED` — code behaves this way but the spec never claimed it → flag (formalize, or remove the undocumented behaviour).

If no existing specs, skip this phase.

### Phase 6: Write the Documented Spec

**If no existing specs**: write the new `spec.md` (with `**Feature Key:**` header) after presenting it (Tier-2).

**If existing specs are present** (Tier-1 — never overwrite blindly; the user may have hand-edited):
1. Present a **unified diff** between the existing spec and the reverse-engineered version, grouped as `### Unchanged`, `### Modified — was / now`, `### Added`, `### Removed-from-code`.
2. Ask: "Overwrite, **merge** (keep your prior edits where they diverge), or **abort**?"
3. Act:
   - **Overwrite** — replace with the reverse-engineered version.
   - **Merge** — for each REQ-* you'd change, ask "prior text X, new text Y — keep X, take Y, or combine?" Apply per-item, then write.
   - **Abort** — leave specs untouched. Still write the drift report so gaps are recorded.

Files to write:
- `.sdlc/specs/<slug>/spec.md` — reverse-engineered or merged, with the footer below.
- `.sdlc/specs/<slug>/drift-report-<timestamp>.md` — the Phase 5 diff (always, when prior specs existed).

Footer to append to overwritten/merged files:
```
---
*Documented from code at {YYYY-MM-DDTHH-MM-SS}. Scope: {scope}. Source commit: {short sha}.*
```

After writing, run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` if present, and report what it flags (likely unkeyed tags in existing code, EARS items needing follow-up).

## Phase Transition

Once the reverse-engineered `spec.md` and (if applicable) `drift-report-<timestamp>.md` are written and approved, this skill is done. **Do not invoke any other skill yourself.** Tell the user (paraphrase, fill in what applies):

> Documented `<slug>` from code. Spec at `.sdlc/specs/<slug>/spec.md`{, drift report at `.sdlc/specs/<slug>/drift-report-<ts>.md`}. Next steps — pick what fits:
> - **Accept the documented spec as authoritative**: this skill writes `spec.md` but not the `test-plan.md` that `/sdlc-implement` needs. To add it, start a fresh chat and run `/sdlc-spec <slug>` — it generates the test plan and reconciles `spec.md` against the problem brief (preserving REQ-* IDs). That reconciliation needs the brief; if you came in from a zero-baseline run, run `/sdlc-init` and `/sdlc-requirements` first.
> - **Code drifted in ways you want to undo**: start a fresh chat and run `/sdlc-quickfix <slug>` to close the gap in the code rather than absorbing it into the spec.

After delivering this message, end your turn.

## Error Recovery

If interrupted mid-phase:
- List `.sdlc/specs/<slug>/` to see whether the documented files and drift report were written.
- If only the drift report exists, the user may have chosen NOT to overwrite the spec — confirm before re-running.
- Re-running on the same scope is safe; it regenerates the same artifacts (subject to determinism caveats).

## Caveats

- This skill is **best-effort**, not exhaustive. It captures what the code does, not what the team intended. A user review pass is mandatory.
- Tests are the highest-signal source of intended behaviour. Code without tests yields thinner specs.
- The output is a **snapshot**. The drift problem isn't solved — it's closed manually. Re-run periodically (or after major refactors).

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `spec.md` | `{root}/.sdlc/specs/<slug>/` | Reverse-engineered spec (canonical EARS + design), declares Feature Key |
| `drift-report-{timestamp}.md` | `{root}/.sdlc/specs/<slug>/` | Diff vs. prior specs (only if any existed) |
