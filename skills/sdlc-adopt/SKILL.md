---
name: sdlc-adopt
description: Bring an existing project onto the current SDLC layout. Migrates legacy artifact paths (docs/, requirements/, rules.md, separate test plans) under .sdlc/ preserving git history, and reverse-engineers specs from code that has none. Use for brownfield adoption, drift recovery, or after upgrading the skills.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-adopt

> **Execution model**: you execute the Workflow below — surveying the project, planning moves, getting approval, migrating, and reverse-engineering specs. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

The one skill for a project that is not yet on the current layout. It does two jobs, and Phase 1 decides which the project needs:

- **Mode A — Layout migration**: relocate legacy artifacts under `.sdlc/`, fold separate test plans into `spec.md`, re-key traceability tags. Mechanical; preserves git history.
- **Mode B — Document from code**: reverse-engineer a spec for code that has none (brownfield onboarding) or that has drifted from its spec. Judgement-heavy; best-effort.

A project may need both — run Mode A first, so Mode B writes to the right paths.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md` if present.
- **Templates**: Mode B fills `.sdlc/templates/spec.md` and `drift-report.md`. If `.sdlc/templates/` does not exist, the project predates templates — finish Mode A, then tell the user to run `/sdlc-init`, which installs the scaffolding without touching existing documents.
- **Moves are Tier-1**: present the complete move plan and get one affirmative before touching the filesystem.
- **Preserve history**: `git mv` in a git repo; `mkdir -p` + `mv` outside one. Never copy-and-leave-the-original — that creates the split-brain this skill exists to prevent.
- **Never rewrite meaning in Mode A**: it relocates files and mechanically re-keys tags. Content that needs judgement (merging old-format specs, restating deprecated EARS) is routed to Mode B or `/sdlc-quickfix`.
- **Idempotent**: safe to re-run. A project already on the current layout reports "nothing to migrate".

## Workflow

### Phase 1: Survey

List (only what exists) the repo root, `docs/`, `docs/adr/`, `requirements/`, `specs/`, `tests/`, `reviews/`, and `.sdlc/`. Build an inventory, then classify:

| Finding | Needs |
|---------|-------|
| Artifacts at legacy roots (`docs/`, `requirements/`, `rules.md`) | Mode A |
| A feature with `.sdlc/tests/<slug>/test-plan.md` beside its `spec.md` | Mode A (fold) |
| A feature with `requirements.md` + `design.md` and no `spec.md` | Mode A (move) then Mode B (merge) |
| Unkeyed tags (`@sdlc REQ-003`, `IMPLEMENTS: REQ-`) | Mode A (re-key) |
| Deprecated EARS (`ALWAYS SHALL`, uppercase `AS … THEN`, uppercase `UNLESS`) | Mode B, or `/sdlc-quickfix` |
| Code with no spec at all | Mode B |
| Everything under `.sdlc/`, specs hold their own `## Test Plan` | Nothing — report and stop |

State which modes you are about to run and why, then proceed.

---

## Mode A — Layout Migration

### A1: Build the Move Plan

An explicit source → destination table for every file. Slugify existing feature directory names. Move `requirements.md` + `design.md` under `.sdlc/specs/<slug>/` keeping their names — merging them into `spec.md` is Mode B's job.

```
docs/product.md              → .sdlc/docs/product.md
docs/tech.md                 → .sdlc/docs/tech.md
docs/test-strategy.md        → .sdlc/docs/test-strategy.md
docs/architecture.md         → .sdlc/docs/architecture.md
docs/adr/ADR-*.md            → .sdlc/docs/adr/ADR-*.md
requirements/*.md            → .sdlc/requirements/*.md
rules.md                     → .sdlc/rules.md
specs/<slug>/spec.md         → .sdlc/specs/<slug>/spec.md
reviews/<slug>/*             → .sdlc/reviews/<slug>/*
.sdlc/tests/<slug>/test-plan.md  → folded into .sdlc/specs/<slug>/spec.md (## Test Plan), file deleted
+ update AGENTS.md and README.md cross-references
```

Present the full plan. **This is the Tier-1 gate — write nothing until the user says yes.**

### A2: Execute Moves

1. Create destinations (`mkdir -p`, or let `git mv` do it).
2. `git mv <src> <dst>` per file, or per directory where the whole directory relocates. Outside git, `mv`.
3. Remove now-empty legacy directories.
4. **Fold test plans**: for each `test-plan.md`, append its content to the feature's `spec.md` under a `## Test Plan` heading, demoting its own headings one level (`## Unit Tests` → `### Unit Tests`). Keep every ID verbatim — `UT-*`/`IT-*`/`E2E-*`/`PBT-*` are referenced by `COVERS:` headers in tests. Then `git rm` the old file.
5. **Update cross-references**: `AGENTS.md` (directory map, plus the validator row), `README.md` (documentation links), and `GENERATED FROM SPEC:` header lines in source that point at old spec paths.

### A3: Re-key Traceability Tags

Mechanical and safe, so do it here rather than routing it. For each feature, read its `spec.md` for the declared Feature Key (if there is none, add one — default the uppercased slug — as a **Tier-1** spec edit, presented first). Then rewrite across `src/` and `tests/`:

- `@sdlc REQ-NNN` → `@sdlc <KEY>:REQ-NNN`
- `IMPLEMENTS: REQ-…` → `IMPLEMENTS: <KEY>:REQ-…`
- `COVERS: …` likewise

### A4: Verify

Run `python3 .sdlc/tools/sdlc-validate.py` and present the summary. If the validator or `.sdlc/templates/` is absent, tell the user to run `/sdlc-init` — it installs them without overwriting anything that already exists.

Path migration is complete when no SDLC artifact remains at a legacy root, no `test-plan.md` remains beside a spec, and cross-references resolve. Remaining EARS or content warnings are Mode B's work.

---

## Mode B — Document from Code

Produces **spec-from-code**, the opposite direction from every other skill. Best-effort: it captures what the code does, not what the team intended, so a user review pass is mandatory.

### B1: Scope Selection

Ask one question: **what is the scope?** Accept a feature name, a directory (`src/auth/`), a glob (`src/payments/**/*.py`), or a commit range. Reject "the whole project" — break it into runs.

### B2: Input Discovery

Read, in order: every source file in scope (`git ls-files <scope>`), every test file for the same scope (tests encode intended behaviour), `.sdlc/rules.md`, `.sdlc/CONVENTIONS.md`, `.sdlc/requirements/entity-dictionary.md`, and any existing spec at `.sdlc/specs/<slug>/`.

If neither `.sdlc/` nor `AGENTS.md` exists, this is a **zero-baseline** run: skip the rules, note the situation, and continue.

**Old-format specs** (`requirements.md` and/or `design.md`, no `spec.md`) — ask:

> Found old-format specs. I can **(a) use them as the baseline** — read both and treat them as the existing spec for the diff; **(b) ignore them** and start fresh from code; or **(c) abort**.

On (a), after writing `spec.md`, ask whether to delete the old files or keep them for reference. On (b), warn once that they were left untouched.

### B3: Extract Behaviour

For each public function, class, handler, or endpoint in scope, identify the **trigger** (HTTP/queue/CLI/cron), **inputs**, **outputs and side effects**, **failure modes**, and **invariants** (what tests assert as always true). Translate each into canonical EARS, preferring the strongest applicable form:

| Observation | EARS form |
|-------------|-----------|
| Constraint enforced on every path | The `<system>` SHALL `<response>`. |
| Behaviour triggered by an action or event | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| Behaviour holding while in a state | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Behaviour behind a flag or optional feature | WHERE `<feature included>`, the `<system>` SHALL `<response>`. |
| Error, guard, invalid-input handling | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |

Continue numbering from existing `REQ-*` IDs. Never recycle — a requirement that vanished from code is marked in the drift report, its number not reused.

### B4: Infer Design Properties

Inspect the code for each property and write a one-sentence finding. Where the code does not address one, say so: `Not enforced — recommend adding {check}`. Do not invent compliance.

| Property | What to look for |
|----------|------------------|
| Round-Trip | Serialization symmetry (encode/decode, save/load) |
| Uniqueness | Unique constraints, dedup logic, idempotency keys |
| Atomicity | Transactions, locks, all-or-nothing branches |
| Validation | Input checks before processing, guard clauses |
| Idempotency | Safe-to-retry behaviour, deterministic re-execution |

### B5: Diff and Write

If a spec (or old-format baseline) exists, produce the drift report from `.sdlc/templates/drift-report.md`: old ID / new ID / status (`UNCHANGED` / `MODIFIED` / `ADDED` / `REMOVED-from-code`). `REMOVED-from-code` and `ADDED` both need a user decision — re-implement or drop; formalize or delete.

Writing the spec:
- **No existing spec** → fill `.sdlc/templates/spec.md` and present it (**Tier-2**). Derive the `## Test Plan` section from the tests that already exist, so the spec matches reality.
- **Existing spec** (**Tier-1** — the user may have hand-edited it) → present a unified diff grouped as `### Unchanged`, `### Modified — was / now`, `### Added`, `### Removed-from-code`, then ask: overwrite, **merge** (per-item: keep prior text, take new text, or combine), or abort. On abort, still write the drift report so the gaps are recorded.

Append to any spec written here:

```
---
*Documented from code at {YYYY-MM-DDTHH-MM-SS}. Scope: {scope}. Source commit: {short sha}.*
```

Then run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>` and report what it flags.

---

## Phase Transition

Report what ran, then route what is left:

> Adopted `<project/slug>`. {Mode A: artifacts consolidated under `.sdlc/`, N test plans folded into their specs, M tags re-keyed.} {Mode B: spec at `.sdlc/specs/<slug>/spec.md`, drift report at `.sdlc/specs/<slug>/drift-report-<ts>.md`.} Validator: {N errors, M warnings}.
> Remaining work, each in a fresh session:
> - {If scaffolding is missing:} Run `/sdlc-init` to install templates, conventions, and the validator.
> - {If steering docs or a problem brief are missing:} Run `/sdlc-init`, then `/sdlc-plan` — a documented spec has no `AC-*` to cite until the brief exists.
> - {If deprecated EARS remains:} Run `/sdlc-adopt` in Mode B on that feature, or `/sdlc-quickfix <slug>` to restate specific requirements.
> - {If code drifted in ways you want to undo rather than absorb:} Run `/sdlc-quickfix <slug>` to close the gap in the code instead of the spec.

After delivering this message, end your turn.

## Caveats

- Mode B is best-effort. Tests are the highest-signal source of intent; code without tests yields thinner specs.
- Its output is a **snapshot**. Drift is not solved, it is closed manually — re-run after major refactors.

## Error Recovery

- **Mid-move**: re-run the skill. Phase 1 re-inventories and A1 only plans what is still pending. In git, `git status` shows staged moves; prefer completing forward over reverting.
- **Mid-document**: list `.sdlc/specs/<slug>/`. If only the drift report exists, the user may have declined the overwrite — confirm before re-running.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| (moved artifacts) | `.sdlc/…` | Relocated steering docs, ADRs, requirements, specs, reviews |
| `spec.md` | `.sdlc/specs/<slug>/` | Test plan folded in (Mode A) or reverse-engineered (Mode B) |
| `drift-report-{ts}.md` | `.sdlc/specs/<slug>/` | Diff against the prior spec, when one existed |
