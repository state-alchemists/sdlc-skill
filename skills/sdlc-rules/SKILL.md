---
name: sdlc-rules
description: Bootstrap or update .sdlc/rules.md — the immutable constitution layer that every downstream SDLC skill must honor. Captures non-negotiable invariants (security, compliance, coding standards, forbidden patterns).
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-rules

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, interviewing the user, generating artifacts, and obtaining approval before writing. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Generates the **constitution** of the project at `.sdlc/rules.md`. Unlike steering documents (which describe the project) and ADRs (which record decisions), rules describe what **must always be true** and **must never happen**. Every downstream skill — `sdlc-architect`, `sdlc-spec`, `sdlc-test-plan`, `sdlc-implement`, `sdlc-review`, `sdlc-quickfix` — reads this file as a precondition and refuses to violate it.

## Conventions (read once, apply throughout)

- **Approval**: treat as approved only an affirmative reply ("yes" / "ok" / "approved" / "go ahead"). Anything else — silence, hedging, partial edits — is a change request: incorporate and re-present. Never write without an explicit affirmative.
- **Rule IDs are immutable**: once a `RULE-NNN` is written, never renumber it. Continue from the highest existing non-sentinel ID on every re-run.
- **Categories** (pin to this enum — do not invent new ones):
  - `Forbidden Patterns` — things the code must never do.
  - `Required Patterns` — things the code must always do.
  - `Compliance & Security` — regulatory or security invariants (PII, PCI, HIPAA, GDPR, secret handling).
  - `Quality Gates` — coverage, lint, dead-code policies.
  - `Coding Standards` — formatting, naming, idiom conventions.
  - `Process` — reserved for the RULE-999 Override Process sentinel; do not add user rules under this category.

## Workflow

### Phase 1: Input Discovery

Read everything that might already imply rules:
- `docs/product.md`, `docs/tech.md`, `docs/test-strategy.md`
- `docs/architecture.md`, `docs/adr/*.md`
- `.sdlc/rules.md` if it already exists (this run will **update**, not overwrite — preserve existing rule IDs)

### Phase 2: Interview for Missing Invariants

Ask the user one question at a time, only those not already covered by the artifacts above. Each answer becomes one (or more) user rule under the named category — except the last, which configures the fixed RULE-999 sentinel, not a new rule:

| Question | Category (becomes RULE-NNN unless noted) |
|----------|------------------------------------------|
| Are there security or compliance requirements (PII, PCI, HIPAA, GDPR) the code must always honor? | Compliance & Security |
| Are there libraries, patterns, or language features the team has explicitly banned (e.g. `eval`, raw SQL, `any` types)? | Forbidden Patterns |
| Are there patterns the team requires (e.g. structured logging, dependency injection, async/await only)? | Required Patterns |
| What is the team's stance on test coverage, lint failures, and dead code? | Quality Gates |
| Are there formatting or naming conventions a reviewer would always flag? | Coding Standards |
| What is the process for overriding a rule (who approves, where it's recorded)? | **Configures RULE-999** (the Override Process sentinel) — do not create a new RULE-NNN for this. |

### Phase 3: Generate `.sdlc/rules.md`

**Numbering**: user rules use IDs `RULE-001` through `RULE-998`. `RULE-999` is reserved for the Override Process sentinel and is always present. On a re-run, continue from the highest existing **non-sentinel** ID — i.e. ignore RULE-999 when computing "next ID". Never renumber or recycle IDs.

#### Template: .sdlc/rules.md

```markdown
# Project Rules — Constitution

> Immutable invariants. Every SDLC skill reads this file and refuses to violate it.
> Override process: see RULE-999 below. Do not edit rule statements without an Override Record.

## How to Use This File
- Every spec, design, test plan, and implementation must respect every rule below.
- `/sdlc-review` will report a `FAIL` for any code that violates a rule.
- To change a rule, follow the Override Process (RULE-999) and append (do not edit) an entry to the Override Log.

## Rules

### RULE-001 — {{Short Title}}
| Field | Value |
|-------|-------|
| Category | {{Forbidden / Required / Compliance / Quality / Coding Standard}} |
| Statement | {{The rule, phrased as ALWAYS/NEVER}} |
| Rationale | {{Why this exists — past incident, regulation, team standard}} |
| Enforcement | {{How violations are detected — lint rule, review checklist, CI gate}} |
| Added | {{YYYY-MM-DD}} |

### RULE-002 — ...
...

## Override Process — RULE-999
| Field | Value |
|-------|-------|
| Category | Process |
| Statement | A rule may only be overridden for a single change, recorded as an entry in the Override Log below, with the approver named. The rule statement itself is never edited. |
| Rationale | Prevents silent erosion of invariants. |
| Enforcement | Reviewers reject PRs that violate a rule without a matching Override Log entry. |

## Override Log

| Date | Rule | Scope (PR / commit) | Approver | Reason |
|------|------|---------------------|----------|--------|
| ... | RULE-NNN | ... | ... | ... |
```

### Phase 4: Approval

Present the populated rules file to the user before writing. Each new or modified rule requires explicit approval (see Conventions).

If updating an existing `.sdlc/rules.md`: read the current file, build the new version in memory, and present a **unified diff** to the user (e.g. by listing rules under headings: `### Unchanged`, `### Added`, `### Modified — was / now`, `### RULE-999 — updated/unchanged`). Write only after the user approves the diff. Do not overwrite without showing what changes.

## Phase Transition

This skill is **invoked once at project setup** (immediately after `/sdlc-init`) and **whenever a new invariant is identified**. It has no fixed "next phase" — every other SDLC skill reads `.sdlc/rules.md` as a precondition.

Once `.sdlc/rules.md` is written and approved, this skill is done. **Do not invoke the next skill yourself.** Tell the user (paraphrase as needed):

> Project constitution is written at `.sdlc/rules.md`. Every later SDLC skill will read this file. To continue:
> - **Fresh project**: exit and start a fresh chat, then run `/sdlc-requirements`.
> - **Mid-pipeline rule addition**: exit and start a fresh chat, then re-run the phase you were on so the new rule is honored end-to-end.

After delivering this message, end your turn.

## Error Recovery

If the session is interrupted mid-phase, list `.sdlc/` to see whether `rules.md` was written. Diff against any backup the user keeps before re-running, since rule IDs must be stable.

## Read By

| Skill | What it does with rules |
|-------|-------------------------|
| `sdlc-architect` | ADRs must not contradict rules; cite RULE-* under "Compliance" |
| `sdlc-spec` | EARS requirements must encode rule compliance where relevant |
| `sdlc-test-plan` | Add tests that detect rule violations |
| `sdlc-implement` | Generated code must adhere; reject prompts that would violate |
| `sdlc-quickfix` | Same as implement, applied to deltas |
| `sdlc-review` | Reports `FAIL` on any unrecorded rule violation |

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| `rules.md` | `{root}/.sdlc/rules.md` | Immutable project invariants |
