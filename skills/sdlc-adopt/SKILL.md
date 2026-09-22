---
name: sdlc-adopt
description: Bring an existing project fully onto the SDLC layout so it reads as though it had been built with these skills from the first commit. Relocates legacy artifacts under .sdlc/ preserving git history, reverse-engineers specs from code that has none, and annotates source and tests with traceability tags and ADR references. Presents one change plan with risk levels and waits for approval before writing anything.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-adopt

> **Execution model**: you execute the Workflow below — surveying, planning, getting one explicit approval, then migrating, documenting and annotating. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

Takes a project that was not built with these skills and leaves it looking like it was: artifacts under `.sdlc/`, every feature carrying a spec, every source and test file carrying the traceability tags the validator enforces, and the decisions that govern the code cited from the code.

It runs in three modes. Phase 1 decides which the project needs; they are independent and any combination may run.

| Mode | Changes | Nature |
|------|---------|--------|
| **A — Layout** | Where files live | Mechanical, history-preserving, reversible |
| **B — Specs** | Adds `.sdlc/specs/<slug>/spec.md` from code | Judgement-heavy, best-effort, additive |
| **C — Annotation** | Edits source and test files in place | Mechanical per edit, but **touches working code** |

Order is fixed: **A → B → C.** B writes to paths A creates; C cites IDs B defines.

## The rule that matters most

**Nothing is written until the user approves the Change Plan in Phase 2.** Survey and plan are read-only. This skill moves files, rewrites cross-references and edits source code — a user who has not seen the full list cannot consent to it.

## Before you start

- **Scaffolding first.** This skill fills a structure; it does not create one. If `.sdlc/templates/` or `.sdlc/tools/sdlc-validate.py` is missing, stop after Phase 1 and tell the user to run `/sdlc-init` — then re-run this skill. Do not improvise templates. On a legacy-layout project `/sdlc-init` installs the scaffolding and stops there, writing no steering documents, precisely so this skill has what it needs; it is always safe to run first.
- **Completing setup, not just filling structure.** Adoption is not finished when the files have moved — it is finished when the project has the steering documents and constitution every later skill reads. Mode A's tail covers this. The distinction that decides who finishes the job: a project with **no scaffolding at all** needs `/sdlc-init` first (it creates the structure); a project with **scaffolding but incomplete setup** is this skill's job, and routing that user back to `/sdlc-init` would strand them.
- **Annotation reference**: read `.sdlc/ANNOTATION.md` before Mode C — comment syntax and header placement per language, and the policy for files that cannot carry a comment.
- **Conventions win**: read `.sdlc/CONVENTIONS.md` first, before classifying anything. Where it sets its own canonical layout — e.g. test plans kept as a standalone file rather than folded into `spec.md` — that overrides every default below, including the fold in Mode A step 4.
- **Preserve history**: `git mv` in a git repo; `mkdir -p` + `mv` outside one. Never copy-and-leave-the-original.
- **Never rewrite meaning in Mode A**: it relocates files and mechanically re-keys tags. Restating requirements is Mode B's job.
- **Never invent compliance**: where code does not do something, say so. An adopted spec that overstates the code is worse than no spec.
- **Idempotent**: safe to re-run. A project already adopted reports "nothing to do" and stops.
- **Uncommitted work**: if `git status` is dirty, say so in Phase 2 and recommend committing first. Mode C edits source files; mixing that with unrelated work makes the diff unreadable.

---

## Phase 1: Survey and Classify

Read-only. List, only where they exist: the repo root, `docs/`, `docs/adr/`, `requirements/`, `specs/`, `tests/`, `reviews/`, `src/`, and `.sdlc/`.

### 1a. Is this an SDLC project at all?

**Classify by content, never by directory name.** A `docs/` directory is not evidence of anything — most projects have one.

<!-- legacy-detection:start -->
A project is on the **legacy SDLC layout** when either of these holds:

1. **A conclusive marker exists** — `docs/adr/ADR-*.md`; a root `rules.md` containing `RULE-`; `specs/<slug>/spec.md` (or `requirements.md` + `design.md`); `requirements/problem-brief.md` or `requirements/entity-dictionary.md`; or `docs/product.md`, `docs/tech.md` or `docs/test-strategy.md` — names this project writes and almost nothing else does.
2. **A weak marker exists and its own text cross-references the scheme** — `docs/architecture.md` containing `.sdlc/`, `ADR-<n>`, `RULE-<n>`, `US-<n>`, `AC-<n>`, `NFR-<n>` or `Feature Key`.

**`docs/architecture.md` on its own is not evidence.** MkDocs, Docusaurus and Diátaxis all emit that filename by default; far more projects have one than have ever run `/sdlc-init`. Treating it as a marker made `/sdlc-init` refuse to write steering documents on projects that had never used these skills.

Matching is case-sensitive: `ARCHITECTURE.md` is the project's own document, `architecture.md` is the one `/sdlc-init` writes. A near-miss is a miss — and the near-miss that bites is the lowercase collision, not the uppercase one.
<!-- legacy-detection:end -->

Any `@sdlc`, `IMPLEMENTS:` or `COVERS:` tag anywhere is also conclusive — it is prior SDLC use by definition. And `docs/adr/0007-some-title.md` is not `docs/adr/ADR-0007-some-title.md`: do not "helpfully" treat a project's own `ARCHITECTURE.md` or `DESIGN.md` as a mis-capitalised SDLC artifact.

If none match, the project **has never used these skills**. Mode A has nothing to migrate — say so plainly and do not propose moving anything. A project's own `docs/` belongs to that project. Moving it produces a `.sdlc/` that advertises an adoption that did not happen, which is worse than leaving it alone. Go to Mode B and C only.

### 1b. Classify what needs doing

| Finding | Needs |
|---------|-------|
| Legacy artifacts confirmed by 1a | Mode A |
| `.sdlc/tests/<slug>/test-plan.md` beside a `spec.md`, and `CONVENTIONS.md` doesn't keep them separate | Mode A (fold) |
| `requirements.md` + `design.md`, no `spec.md` | Mode A (move) then Mode B (merge) |
| Unkeyed tags (`@sdlc REQ-003`, `IMPLEMENTS: REQ-`) | Mode A (re-key) |
| Deprecated EARS (`ALWAYS SHALL`, uppercase `AS … THEN`, uppercase `UNLESS`, `WHERE … THEN`) | Mode B, or `/sdlc-quickfix` |
| Source files with no spec covering them | Mode B, then C |
| Infra or SQL repo — `.tf`, k8s YAML, migrations — with no loader to tag | Mode B, then C on the manifests themselves |
| Spec exists, but its code carries no `IMPLEMENTS:`/`COVERS:` | Mode C |
| ADRs exist, but no code cites them | Mode C (optional — ask) |
| `.sdlc/rules.md` absent, or `.sdlc/docs/{product,tech,test-strategy}.md` or root `AGENTS.md` absent | Mode A tail (Complete Setup) |
| Everything already under `.sdlc/`, test plans complete (folded into `spec.md`, or standalone where `CONVENTIONS.md` says so), tags keyed and complete, steering documents and `rules.md` present | Nothing — report and stop |

### 1c. Measure the starting point

Count, and keep these for the Phase 4 comparison: source files in scope, source files carrying `IMPLEMENTS:`, test files carrying `COVERS:`, features with a `spec.md`, and ADRs cited from code. This is what makes "did it work?" answerable later.

---

## Phase 2: The Change Plan — the approval gate

Present **one** plan covering every mode that will run. Nothing is written before the user says yes.

### 2a. What changes

A table with one row per file or group, and an **Effect** column stating what breaks or improves. Never just list paths — a path list is not informed consent.

*(example — the paths below are illustrative; yours come from the project's own layout)*

```
MODE A — Layout                                          Risk
  docs/product.md        → .sdlc/docs/product.md         low    git mv, history preserved
  docs/adr/ADR-*.md (7)  → .sdlc/docs/adr/               low    git mv, history preserved
  rules.md               → .sdlc/rules.md                low    git mv
  README.md              4 links repointed               low    links resolve after move
  AGENTS.md              directory map + validator row   MEDIUM if AGENTS.md documents paths as owned, it now disagrees with itself until updated
  <build/CI config>      N path references               HIGH   a missed reference breaks the build, not the docs

MODE B — Specs
  .sdlc/specs/auth/spec.md    NEW, ~14 REQ from code     low    additive; no existing file touched

MODE C — Annotation
  src/auth/*.py (6 files)     + IMPLEMENTS: headers      MEDIUM edits working source; comments only, no logic
  tests/auth/*.py (4 files)   + COVERS: headers          MEDIUM edits working tests; comments only, no logic
  src/auth/session.py:88      + @sdlc AUTH:REQ-003       MEDIUM inline tag above the function
```

### 2b. Risk register — state these explicitly

Call out every item below that applies. Do not bury them in the table.

- **Anything outside docs that references a moved path** — CI config, Dockerfiles, `pyproject.toml`, `Makefile`, packaging manifests, doc generators, IDE config. Grep for every moved path across the whole repo, not just `*.md`, and list what you found. A moved file that a build step still points at breaks the build.
- **Path-checking tooling in the project itself** — a docs linter or link checker with hardcoded roots will fail after a move and must be updated in the same change.
- **Mode C edits working code.** Comments and headers only, never logic. Say that, and say how many files.
- **Generated or vendored files** — anything under `node_modules/`, `vendor/`, `dist/`, `build/`, `.venv/`, or marked "do not edit". Mode C skips these. List what was skipped.
- **A dirty working tree** — recommend committing first.
- **Irreversibility** — in a git repo with a clean tree, everything here is reversible with `git checkout .` and removing new files. Say so; it is the single most reassuring true fact available. Outside a git repo, say plainly that it is not reversible and offer to stop.

### 2c. What will NOT change

List explicitly: no logic edits, no dependency changes, no test behaviour changes, no renamed public symbols, no deletions except legacy files folded into a spec (name them).

### 2d. Ask

> Approve this plan? I can also run **Mode A only**, **Modes A+B only**, or stop. Nothing has been written yet.

Accept a partial approval and run only the approved modes. If the user declines, write nothing and report the survey as the deliverable.

---

## Mode A — Layout Migration

1. Create destinations (`mkdir -p`, or let `git mv` do it).
2. `git mv <src> <dst>` per file, or per directory where the whole directory relocates.
3. Remove now-empty legacy directories.
4. **Fold test plans, unless `CONVENTIONS.md` keeps them separate** — then skip this step; the validator may cross-reference `UT-*`/`IT-*`/`E2E-*` IDs against that standalone file, and folding breaks it. Otherwise: append each `test-plan.md` to its feature's `spec.md` under `## Test Plan`, demoting its headings one level (`## Unit Tests` → `### Unit Tests`). Keep every ID verbatim — `COVERS:` headers reference them. Then `git rm` the old file.
5. **Repoint every reference**, including the non-markdown ones from the risk register. Re-grep after the move to prove none remain.
6. **Re-key tags**. For each feature read its Feature Key from `spec.md`; if absent, add one as a Tier-1 spec edit presented first. Default to the uppercased slug, but only when that is a valid key (`[A-Z][A-Z0-9_-]*`) — a slug starting with a digit (`2fa` → `2FA`) is not one, and a tag built from it cannot be parsed, so choose a real key (`TWOFA`) and say why. Then across every tracked file (`git grep -l`), skipping anything vendored or generated: `@sdlc REQ-NNN` → `@sdlc <KEY>:REQ-NNN`, and the same for `IMPLEMENTS:` and `COVERS:`.

Every scripted edit asserts its anchor before writing — a blind `str.replace` that matches nothing fails silently and reports success. Before starting Mode B or C, re-run `.sdlc/tools/sdlc-validate.py`: Mode A restructures the files the validator cross-references, so a regression is cheap to catch here and expensive to catch at Phase 4, after later modes have built on top of it.

---

## Mode A tail — Complete Setup

Run this at the end of Mode A, **before** Mode B or C, and only when step 7 below finds a gap.

Relocation puts the artifacts where the skills expect them; it does not finish the setup. `.sdlc/rules.md`, `.sdlc/docs/{product,tech,test-strategy}.md` and root `AGENTS.md` are what every later skill reads, and on a legacy project `/sdlc-init` could not write them — it would have put them beside the user's own documents, a parallel tree. With the documents now relocated, that objection is gone and the work is ordinary.

7. **Detect the gap.** For each of `.sdlc/rules.md`, `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md` and `AGENTS.md`: present or absent. A relocated document is present and needs no more than a gap-fill.

   If all five are present, say so and skip to Mode B. Most projects that ran a pre-`.sdlc/` version of these skills will have `docs/product.md` and friends but **no `rules.md`** — constitution was a later addition, so this is the common case.

8. **Ask once, at the end of Mode A — not in the Phase 2 plan.** The layout is now real, so the user can see what is missing:

   > Layout is done. Missing: {list}. Derive these now from the relocated documents and your manifests, or stop here and I will hand you the command?

   This is a **separate approval**, deliberately. Phase 2 was approved against a tree that did not exist yet; asking there to generate five documents from an interview would be consent to work the user cannot yet picture. Accept a decline: report what is missing and end the turn. Never treat Mode A's approval as covering this.

9. **Derive, then confirm — do not interview from scratch.** Read `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`, the manifests, `README.md` and `.sdlc/CONVENTIONS.md`, then draft each missing document from what is already written. Present the draft and ask the user to correct it. Where a document genuinely has no source — product intent usually — ask, but ask **after** drafting, one question at a time, and only what the artifacts do not answer.

   Templates come from `.sdlc/templates/`, which Phase 2 of `/sdlc-init` installed. A template the project has edited wins over the bundled one; on a legacy project that never ran the new `/sdlc-init`, the templates are freshly installed and unedited.

10. **`rules.md` last, and from the documents.** Rules describe what must **always** be true and **never** happen, and the steering documents you just wrote usually imply them. Number `RULE-001`–`RULE-998` with `RULE-999` as the always-present Override Process sentinel. Never renumber an existing rule; continue from the highest non-sentinel ID.

11. **Approval tiers.** Creating a document that does not exist is **Tier-2**, batched — present all of them together. **Modifying** an existing document, or an existing rule, is **Tier-1**: show a per-rule diff grouped `### Unchanged` / `### Added` / `### Modified — was / now` / `### RULE-999`, and write only the approved items. A relocated `product.md` is an existing document — gap-filling it is Tier-1.

**Never invent project intent to fill a template.** A `product.md` that states goals the user never confirmed is worse than an absent one: every later skill treats it as settled. Where the artifacts are silent, ask; where the user does not know, say the section is open rather than writing a plausible answer.

Do not re-derive what Mode B will cover. Steering documents describe the project; Mode B documents what the code does, feature by feature. They are not substitutes, and Mode A's tail does not write specs.

---

## Mode B — Document from Code

Produces **spec-from-code**: what the code does, not what the team intended. A user review pass is mandatory.

### B1: Scope

Ask: **what is the scope?** Accept a feature name, a directory, a glob, or a commit range. Reject "the whole project" — break it into runs, one coherent subsystem at a time. Prefer a subsystem that has tests; they carry the intent.

### B2: Inputs

Read every source file in scope (`git ls-files <scope>`), every test file for the same scope, `.sdlc/rules.md`, `.sdlc/CONVENTIONS.md`, `.sdlc/requirements/entity-dictionary.md`, and any existing spec.

**Old-format specs** (`requirements.md` and/or `design.md`, no `spec.md`) — ask:

> Found old-format specs. I can **(a) use them as the baseline** for the diff; **(b) ignore them** and start fresh from code; or **(c) abort**.

On (a), after writing `spec.md`, ask whether to delete the old files. On (b), warn once that they were left untouched.

### B3: Extract behaviour

For each public function, class, handler or endpoint: the **trigger**, **inputs**, **outputs and side effects**, **failure modes**, and **invariants** (what tests assert as always true). Translate into canonical EARS:

| Observation | EARS form |
|-------------|-----------|
| Constraint enforced on every path | The `<system>` SHALL `<response>`. |
| Triggered by an action or event | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| Holds while in a state | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Behind a flag or optional feature | WHERE `<feature included>`, the `<system>` SHALL `<response>`. |
| Error, guard, invalid input | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |

Continue numbering from existing IDs. Never recycle — a requirement that vanished from code is marked in the drift report and its number retired.

**Citations**: requirements documented from code have no `AC-*` to cite until a problem brief exists, so write them without a citation rather than inventing one. The validator checks citations only against a brief that exists, so an uncited requirement is clean; a fabricated `AC-042` is an ERROR.

**Record the source of each requirement** (`file:line`). Mode C needs it to place tags, and a reviewer needs it to check your reading.

### B4: Infer design properties

One sentence per property, from the code. Where the code does not address one, write `Not enforced — recommend adding {check}`.

| Property | What to look for |
|----------|------------------|
| Round-Trip | Serialization symmetry (encode/decode, save/load) |
| Uniqueness | Unique constraints, dedup logic, idempotency keys |
| Atomicity | Transactions, locks, all-or-nothing branches |
| Validation | Input checks before processing, guard clauses |
| Idempotency | Safe-to-retry behaviour, deterministic re-execution |

### B5: Diff and write

With a prior spec or baseline, produce the drift report from `.sdlc/templates/drift-report.md`: old ID / new ID / `UNCHANGED` / `MODIFIED` / `ADDED` / `REMOVED-from-code`. `ADDED` and `REMOVED-from-code` each need a user decision.

- **No existing spec** → fill `.sdlc/templates/spec.md`, present it (**Tier-2**). Derive `## Test Plan` from the tests that already exist, so the spec matches reality.
- **Existing spec** (**Tier-1**) → present a unified diff grouped `### Unchanged` / `### Modified — was / now` / `### Added` / `### Removed-from-code`, then ask: overwrite, **merge** per item, or abort. On abort still write the drift report.

Append to any spec written here:

```
---
*Documented from code at {YYYY-MM-DDTHH-MM-SS}. Scope: {scope}. Source commit: {short sha}.*
```

---

## Mode C — Annotate the Code

What makes a project read as SDLC-native: the link from code back to the requirement and the decision it serves. Runs only on features that have a `spec.md`.

**Comments and headers only. Never logic, never formatting, never imports.** If a file needs restructuring to be taggable, do not restructure it — note it and move on.

### C1: Place traceability tags

Using the `file:line` map from B3, emit exactly the three forms the validator parses:

```python
# SPEC: .sdlc/specs/{slug}/spec.md
# IMPLEMENTS: {KEY}:REQ-001, {KEY}:REQ-003, {KEY}:NFR-002
```
```python
# COVERS: {KEY}:REQ-002, {KEY}:UT-005, {KEY}:IT-001
```
```python
# @sdlc {KEY}:REQ-003
def validate_login(...): ...
```

Follow `.sdlc/ANNOTATION.md` for comment syntax and header placement. It is the shared rule, and it covers the cases these three Python examples do not — PHP, CSS, XML, single-file components, formats with no comment syntax, and generated files.

**Never annotate a file you do not own.** Before touching any file, apply the exclusion test in `.sdlc/ANNOTATION.md`: the vendored and generated globs in `.sdlc/config.json`, the standard vendor directories, a `DO NOT EDIT` / `@generated` / `Code generated by` marker in the first five lines, or `linguist-generated` in `.gitattributes`. A header on a generated file is wiped by the next regeneration and the validator then reports the requirement as untraced. Tag the generator's input or the hand-written wrapper instead. **Count and list every file you skipped, and repeat that list in the Phase 4 report** — a silent skip looks identical to a missed file.

Every `REQ-*` and `NFR-*` must land in at least one source header and one test header, or the validator errors. Two ways out, and they are different claims:

- An NFR under **"NFRs Validated Outside Code"** needs no tag — the validator exempts it, and a fake `IMPLEMENTS:` line is a lie it cannot catch.
- A functional requirement no executable check can reach — production paging, a manual review, a business process — goes under **"Requirements With No In-Code Verification"** in the spec, which exempts `REQ-*`. Do not reach for this because a tag is inconvenient: a policy file that gates the merge is a test, so most IaC requirements can carry `COVERS:` instead. If no test exists and none can, say which of the two it is and let the user decide.

**In an infrastructure or SQL repository, the manifest is the implementation.** There is no loader to tag, so the `.tf` / `.yaml` / `.sql` file carries `IMPLEMENTS:` — see `.sdlc/ANNOTATION.md`. Place the header where that file's leader allows: `#` at the top for `.tf`, `.tfvars`, `.hcl` and k8s YAML, `--` after any tool directive (`-- +goose Up`) for `.sql`. A `.sql` migration may hold several statements behind one header; that claims the file's requirement, not each statement.

### C2: Cite the decisions

Where an ADR governs a specific piece of code, add a reference at that place:

```python
# @sdlc-adr ADR-0007 — hooks must fail open; every registration carries `|| exit 0`
```

Rules, because this one invites noise:

- Only where a reader could **re-break** the decision. A file that merely operates under an ADR does not need a line.
- One line, naming the constraint, not summarising the ADR.
- **The validator does not check these.** They are documentation, not enforcement. Say so when reporting; do not present them as verified.
- If the project already cites decisions in its own style, match it. Do not convert an existing convention to this one.

### C3: Verify nothing broke

Run the project's test suite. Mode C only adds comments, so a failure means something went wrong — a header inside a docstring, a broken continuation line, an encoding declaration displaced. Fix it or revert that file. **Report the suite result; never claim the edits are safe without running it.**

---

## Phase 4: Verify

1. `python3 .sdlc/tools/sdlc-validate.py` — present the summary.
2. Re-run the project's own tests and doc checks, and report their output.
3. Re-count the Phase 1c numbers and show the comparison.

**A clean validator run does not mean adoption succeeded.** On a project with no specs it reports `0 errors, 0 warnings` and exits 0 — it is silent about everything that is absent. The honest measure is the before/after table:

```
                            before   after
  features with a spec         0        1
  source files tagged          0        6      (of 9 in scope)
  test files tagged            0        4      (of 4 in scope)
  ADRs cited from code         0        3      (of 12)
  validator                  0/0/1    0/0/0
```

State what is still unadopted and name it. Adoption is complete when every feature in scope has a spec, every source and test file in scope carries its tags, the validator is clean, the project's own tests pass, and the steering documents and `.sdlc/rules.md` are present — not when the validator stops complaining. The last clause is what makes `/sdlc-adopt` terminal: a project can pass every other check and still have no constitution for the next skill to read.

---

## Phase Transition

> Adopted `<project>`. {Mode A: N artifacts relocated under `.sdlc/`, M references repointed, K test plans folded.} {Mode B: spec at `.sdlc/specs/<slug>/spec.md` with N requirements; drift report at `drift-report-<ts>.md`.} {Mode C: N source and M test files tagged, K ADR references added; test suite {result}.} Validator: {N errors, M warnings}.
>
> {The before/after table.}
>
> Still unadopted: {list, or "nothing in scope"}.

Then deliver the action block (see CONVENTIONS.md § Session handoff), turning whichever of these apply into checked-off items. Include only those the survey actually found — an adopted project with a problem brief, complete scope and current EARS has nothing to list, and should say so rather than emit an empty block.

```
Remaining work, in a fresh session:

  [ ] /sdlc-plan                    {only if no problem brief exists — a documented
                                     spec has no AC-* to cite until it does}
  [ ] /sdlc-adopt <next-subsystem>  {only if scope was partial; name the subsystem}
  [ ] /sdlc-quickfix <slug>         {only if deprecated EARS remains, or code drifted
                                     in ways to undo rather than absorb — say which}
```

**Do not list `/sdlc-init` here.** A project that reached this skill has scaffolding, so its setup gaps were Mode A's tail and are either done or were declined at step 8 — either way `/sdlc-init` is not the next command. If step 8 was declined, name what is still missing and say `/sdlc-init` is **not** the way to finish it (it would write beside, not over, the relocated documents); Mode A's tail can be run later instead.

The `/sdlc-init` case that remains is the one this skill refused: **no scaffolding at all**, which is handled in the Phase 1 refusal, before Mode A ever runs.

Add `/sdlc-spec <slug>` for any feature the survey found with source but no spec, since that is then a real next step. When two or more features lack specs, say they may be specified in parallel.

After delivering this message, end your turn.

## Caveats

- Mode B is best-effort. Tests are the highest-signal source of intent; code without tests yields thinner specs.
- Its output is a **snapshot**. Drift is closed manually — re-run after major refactors.
- Mode C makes the link visible; it does not verify the code fulfils the requirement. That is `/sdlc-review`.
- In an infra or SQL project, Mode C has no loader to fall back on: the manifest is the implementation and is annotated directly. Where a requirement's only check is a policy scan nobody fails on, that is **not** a test — say so and use the exemption heading rather than tagging it as covered.

## Error Recovery

- **Mid-move**: re-run. Phase 1 re-inventories and Phase 2 plans only what is pending. `git status` shows staged moves; prefer completing forward over reverting.
- **Mid-document**: list `.sdlc/specs/<slug>/`. If only the drift report exists, the user may have declined the overwrite — confirm before re-running.
- **Mid-annotation**: `git diff --stat` shows which files were touched. Mode C is per-file idempotent; re-running skips files already carrying their tags.
- **Tests failed after Mode C**: revert only the annotated files (`git checkout -- <files>`), report which, and do not proceed to Phase 4 claiming success.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| (moved artifacts) | `.sdlc/…` | Relocated steering docs, ADRs, requirements, specs, reviews |
| `spec.md` | `.sdlc/specs/<slug>/` | Test plan folded in where Mode A's fold applies, or reverse-engineered (Mode B) |
| `drift-report-{ts}.md` | `.sdlc/specs/<slug>/` | Diff against the prior spec, when one existed |
| (annotated sources) | the project's source and test roots | `SPEC:` / `IMPLEMENTS:` / `COVERS:` / `@sdlc` / `@sdlc-adr` |
