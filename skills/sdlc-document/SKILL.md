---
name: sdlc-document
description: Reverse-engineer EARS requirements and design from existing code. Use when specs have drifted from implementation, or when adopting SDLC on a brownfield codebase that has no specs at all.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-document

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading source files, reverse-engineering specs, diffing against any prior specs, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Closes the drift loop in the opposite direction from the other skills: instead of code-from-spec, this produces **spec-from-code**. Use it for brownfield adoption and for drift recovery when implementation has diverged from existing specs.

**Use this skill when:**
- The code for a feature exists but has no spec (brownfield onboarding).
- A `/sdlc-review` flagged drift between code and existing specs, and you want to regenerate the spec to match reality before deciding which side is wrong.
- An external contractor delivered code without specs and you need to retrofit them.

**Do NOT use this skill when:**
- You want to *plan* a new feature → use `/sdlc-spec`.
- You want to fix a small bug → use `/sdlc-quickfix`.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-document <free-text>`. Use it verbatim as `{scope}` — it may be a feature name, a directory path, a file glob, or a git ref range. If missing, ask (see Phase 1).
- **`{feature}` resolution**: derive the feature name from the scope as follows: if scope is a feature name, use it directly; if it's a path/glob, ask the user "Under which feature directory should I write the specs?"
- **Approval**: write only after an explicit affirmative. For overwriting an existing spec, the affirmative must follow a presented diff (see Phase 6) — never overwrite blindly.
- **Required input present**: at least one source or test file must exist under the chosen scope. If the scope is empty, stop and ask the user to refine it.
- **Timestamp**: get the current time via the runtime's shell. Never invent.
- **Determinism caveat**: LLM output isn't deterministic. Re-runs may produce subtly different specs even from identical inputs. Manual user edits between runs are at risk — Phase 6 addresses this with a diff gate.

## Workflow

### Phase 1: Scope Selection

Ask the user one question: **what is the scope?** Acceptable answers:
- A single feature name (will document everything under `src/` matching that feature's modules)
- A directory path (e.g. `src/auth/`)
- A file glob (e.g. `src/payments/**/*.py`)
- A git commit range (everything changed between two refs)

Reject vague scopes ("the whole project") — break them into multiple `/sdlc-document` runs.

### Phase 2: Input Discovery

Read, in order:
1. All source files in the chosen scope. Use `git ls-files <scope>` to enumerate.
2. All test files for the same scope (they encode intended behaviour).
3. `.sdlc/rules.md` if present (so reverse-engineered specs don't reintroduce forbidden patterns).
4. `requirements/entity-dictionary.md` — to align reverse-engineered domain nouns with existing entities.
5. Any **existing** `specs/{feature}/requirements.md` and `design.md` — you'll diff against these, not overwrite blindly.

### Phase 3: Extract Behaviour

Walk the source and tests, and for each public function/class/handler/endpoint, identify:
- **Trigger**: what causes it to run (HTTP request, queue message, CLI invocation, scheduled job)?
- **Inputs**: parameters, request body, environment.
- **Outputs**: return value, side effects (DB writes, external calls, emitted events).
- **Failure modes**: what does it do when inputs are invalid or dependencies fail?
- **Invariants**: what does the test suite assert as always true?

Translate each behaviour into an EARS statement. Prefer the strongest applicable keyword:

| Observation | EARS form |
|-------------|-----------|
| Hard-coded constraint enforced in code path | `ALWAYS SHALL` |
| Behaviour triggered by an HTTP/event/CLI action | `WHEN ... THEN SHALL` |
| Behaviour depends on a feature flag or session state | `WHERE ... THEN SHALL` |
| Behaviour gated by a runtime condition | `AS ... THEN SHALL` |
| Default behaviour with one explicit exception | `UNLESS ... THEN SHALL` |

Number new requirements continuing from any existing `REQ-*` IDs. **Never recycle IDs** — if a requirement disappears in the new version, mark it as REMOVED in the diff, do not reuse its number.

### Phase 4: Infer Design Properties

For each correctness property from `sdlc-spec`, inspect the code and write a one-sentence finding:

| Property | What to look for in code |
|----------|--------------------------|
| Round-Trip | Serialization symmetry (encode/decode, save/load) |
| Uniqueness | Unique constraints in DB/migrations, dedup logic, idempotency keys |
| Atomicity | Transactions, locks, all-or-nothing branches |
| Validation | Input checks before processing (schema validation, guard clauses) |
| Idempotency | Safe-to-retry behaviour, deterministic re-execution |

If the code does not address a property, state it explicitly: `Not enforced — recommend adding {test/check}`. Do not invent compliance.

### Phase 5: Diff Against Existing Specs

If `specs/{feature}/requirements.md` and `design.md` already exist:
- Show the user a three-column diff: **Old REQ-* / New REQ-* / Status (UNCHANGED / MODIFIED / ADDED / REMOVED-from-code)**.
- Status `REMOVED-from-code` means the spec still claims this requirement but the code no longer implements it — flag for user decision (re-implement, or drop from spec).
- Status `ADDED` means the code behaves this way but the spec never claimed it — flag for user decision (formalize, or remove the undocumented behaviour).

If no existing specs, skip this phase.

### Phase 6: Write the Documented Spec

**If no existing specs**: write the new files directly after presenting them to the user for approval.

**If existing specs are present**: do NOT overwrite blindly. The user may have hand-edited the prior spec since the last `/sdlc-document` run, and reverse-engineering won't catch intent that lives in those edits.

1. Present a **unified diff** between the existing spec and the reverse-engineered version. Group changes as: `### Unchanged`, `### Modified — was / now`, `### Added`, `### Removed-from-code`.
2. Ask the user: "Overwrite, **merge** (keep your prior edits where they diverge from the reverse-engineered version), or **abort**?"
3. Act on the answer:
   - **Overwrite** — replace the files with the reverse-engineered version.
   - **Merge** — for each REQ-* you would change, ask "the prior text was X, the new text is Y — keep X, take Y, or combine?" Apply per-item decisions, then write.
   - **Abort** — leave the existing specs untouched. Still write the drift report so the gaps are recorded.

Files to write (depending on the decision above):
- `specs/{feature}/requirements.md` — reverse-engineered or merged, with the footer below.
- `specs/{feature}/design.md` — same treatment.
- `specs/{feature}/drift-report-{timestamp}.md` — the diff from Phase 5 (always write this when prior specs existed).

Footer to append to overwritten / merged files:
```
---
*Documented from code at {YYYY-MM-DDTHH-MM-SS}. Scope: {scope}. Source commit: {short sha}.*
```

## Phase Transition

Once the reverse-engineered `requirements.md`, `design.md`, and (if applicable) `drift-report-{timestamp}.md` are written and approved, this skill is done. **Do not invoke any other skill yourself** — only the user can start a fresh chat and trigger one. Tell the user (paraphrase as needed):

> Documented `{feature}` from code. Specs are now at `specs/{feature}/requirements.md` and `specs/{feature}/design.md`{, drift report at `specs/{feature}/drift-report-{timestamp}.md` if applicable}. Suggested next steps — pick whichever fits:
> - **Accept the documented spec as authoritative**: exit and start a fresh chat, then run `/sdlc-test-plan {feature}` to generate a test plan against the now-current spec. Missing tests will reveal real coverage gaps.
> - **Code drifted in ways you want to undo**: exit and start a fresh chat, then run `/sdlc-quickfix {feature}` to close the gap in the code rather than absorbing it into the spec.
> - **Both**: do the quickfix first, then the test plan.

After delivering this message, end your turn.

## Error Recovery

If interrupted mid-phase:
- List `specs/{feature}/` to see whether the documented files and drift report were written.
- If only the drift report exists, the user may have chosen to NOT overwrite the spec yet — confirm with the user before re-running.
- Re-running on the same scope is safe; it will regenerate the same artifacts (subject to LLM determinism caveats).

## Caveats

- This skill is **best-effort**, not exhaustive. It captures what the code does, not what the team intended. A user review pass is mandatory.
- Tests are the highest-signal source of intended behaviour. Code without tests will produce thinner specs.
- The output is a **snapshot at this point in time**. The drift problem isn't solved — it's just being closed manually. Re-run periodically (or after major refactors).

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `requirements.md` | `{root}/specs/{feature}/` | Reverse-engineered EARS requirements |
| `design.md` | `{root}/specs/{feature}/` | Reverse-engineered correctness properties |
| `drift-report-{timestamp}.md` | `{root}/specs/{feature}/` | Diff vs. prior specs (only if any existed) |
