---
name: sdlc-implement
description: Generate code and tests from a feature spec. Delegates the whole feature to a coding sub-agent that reads the spec from disk, then verifies tests, lint, and traceability.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-implement

> **Execution model**: you execute the Workflow below — reading files, delegating to a coding agent, verifying the suite, reporting results. Lines that say "run `/sdlc-<other>`" are instructions **for the user**; only the user starts the next skill. Deliver the Phase Transition message, then stop.

Drives implementation from `spec.md` with a **single delegation**. The sub-agent reads spec artifacts on demand from disk (progressive disclosure); only the project rules are inlined, because they are small and must never be missed.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md` — paths, ID scheme, file roles, approval tiers.
- **Layout**: read `.sdlc/config.json` for this project's source and test roots, and `.sdlc/ANNOTATION.md` for comment syntax and header placement. Never assume `src/` + `tests/`.
- **Argument → slug**: slugify the user's free text the same way `sdlc-spec` did, to locate `.sdlc/specs/<slug>/`. If it is missing, ask.
- **Feature Key**: read `**Feature Key:**` from the spec. Every tag the agent emits is key-namespaced (`@sdlc KEY:REQ-003`).
- **Required input**: no `.sdlc/specs/<slug>/spec.md`, or a spec with no `## Test Plan` section? Stop and tell the user to run `/sdlc-spec <slug>`.
- **Approval**: get an affirmative on the delegation **before** running it (Tier-2 — one approval covers the feature). No second approval unless retrying.
- **Retry cap**: at most **2 re-delegations** (3 attempts total), each with the specific failure context. After the third failure, stop and report the blocker. Do not loop.
- **Verification commands**: read test and lint commands from `AGENTS.md`, then `.sdlc/docs/test-strategy.md`. If neither names a runnable command, ask — never guess.
- **Legacy layout**: a separate `.sdlc/tests/<slug>/test-plan.md` still works as an input; tell the user to run `/sdlc-adopt` to fold it into the spec.

## Workflow

### Phase 1: Input Discovery

Read only enough to write a correct delegation and to inline the rules:
- `.sdlc/rules.md` — **inline verbatim** in the delegation (small, load-bearing)
- `.sdlc/specs/<slug>/spec.md` — confirm it exists; read the Feature Key, requirements, and test plan
- `AGENTS.md`, `.sdlc/docs/test-strategy.md` — test and lint commands

The sub-agent reads the architecture, ADRs, and entity dictionary itself. You do not need to inline them.

### Phase 2: Single Delegation

Show the user the task. Once approved, delegate the **entire feature** to one coding agent. The block below is a prompt template — fill the placeholders.

```
Implement the feature "{slug}" (Feature Key: {KEY}) following spec-driven development.

READ THESE FILES FIRST — they are your source of truth (read on demand; do not assume their contents):
- .sdlc/specs/{slug}/spec.md               ← requirements (canonical EARS), design, and the test plan you must satisfy
- .sdlc/docs/tech.md                       ← stack and constraints
- .sdlc/docs/architecture.md and .sdlc/docs/adr/*.md   ← architecture decisions to honor
- .sdlc/requirements/entity-dictionary.md  ← field names, types, constraints
- .sdlc/ANNOTATION.md                      ← comment syntax and WHERE the header goes, per language. Read it before writing the first header.
- .sdlc/config.json                        ← this project's source and test roots
(If your runtime cannot read files, tell the orchestrator and it will inline them.)

PROJECT RULES (.sdlc/rules.md — refuse to violate any; inlined because they are mandatory):
[Inline rules.md verbatim, or write "No rules file present."]

INSTRUCTIONS:
1. Put source and test files where this project already puts them. The layout is declared in
   .sdlc/config.json and visible in the repo itself; where tests live beside their sources
   (Go's *_test.go, Jest's *.test.ts) follow that. Do NOT create a new top-level src/ or tests/
   directory — if you think one is needed, stop and say so in your report.
2. Follow the spec's "## Test Plan" section — every test in it must exist and pass.
3. Run the test suite after implementation (commands from AGENTS.md / .sdlc/docs/test-strategy.md).
4. Do NOT modify .sdlc/specs/{slug}/spec.md, or anything else under .sdlc/. The spec is the
   contract you are being measured against; editing it is how a failing implementation passes.
   If a requirement looks unimplementable, say so in your report and leave it failing.
5. Report pass/fail per test.

TRACEABILITY (REQUIRED — every ID is namespaced by the Feature Key "{KEY}"):
- READ .sdlc/ANNOTATION.md FIRST. It gives the comment syntax per file type and exactly where the
  header goes. The header is NOT always the first line: it goes after a shebang, after an encoding
  or magic comment, after a licence block, after the module docstring, after `<?php`, after an XML
  prolog, and inside the <script> block of a Vue/Svelte component. Getting this wrong does not
  produce an untidy file — it produces a file that no longer runs.
- Every SOURCE file you generate, in that file's own comment syntax:
    SPEC: .sdlc/specs/{slug}/spec.md
    IMPLEMENTS: {KEY}:REQ-001, {KEY}:REQ-003, {KEY}:NFR-002
- Every TEST file you generate:
    COVERS: {KEY}:REQ-002, {KEY}:NFR-001, {KEY}:UT-005, {KEY}:IT-001
- Inline-tag each public function/class/handler with the IDs it directly fulfils:
    @sdlc {KEY}:REQ-003, {KEY}:REQ-004
  Tag only the unit that directly fulfils the requirement — do not sprinkle tags on helpers.
- A tag only counts inside a real comment, and only from the right kind of file: IMPLEMENTS: from
  a source file, COVERS: from a test file. One file carrying both satisfies neither.
- A file that cannot carry a comment (.json, .csv, a lockfile) gets NO header and NO invented
  comment key. Tag the code that loads it instead.
- Never put a header on a generated or vendored file; see .sdlc/ANNOTATION.md.
- Every REQ-* and NFR-* must appear in at least one source header and one test header. For an NFR
  listed under "NFRs Validated Outside Code", do NOT emit a fake IMPLEMENTS line — note it in the
  report instead.
```

Hand the filled prompt to a general-purpose coding agent via whatever delegation mechanism your runtime exposes; the agent plans its own task breakdown.

**Fallback for runtimes without file access**: inline the spec and relevant architecture as well. Progressive disclosure is preferred — it scales to large projects — but inlining is the correct degradation.

### Phase 3: Verification

1. Run the test suite.
2. Run the linter.
3. Run `python3 .sdlc/tools/sdlc-validate.py --feature <slug>`. Treat ERROR findings (missing `IMPLEMENTS`/`COVERS`, dangling tags) as failures to fix. `--feature` narrows the findings to this feature; other features' tags still resolve, so anything reported here is really yours. An unkeyed tag is a WARNING *and* leaves its requirement untraced — re-key it rather than adding a second tag.
4. Confirm the spec was not edited: `git diff --name-only -- .sdlc/` must be empty. A validator error cleared by rewriting the spec is not a fix. If the agent touched anything under `.sdlc/`, revert it and re-delegate with that called out.
5. On any failure, re-delegate with the specific context — **retry cap 2**. Every retry fixes **code**, never the spec. After the third failure, stop and report what failed, what was tried, and what looks unimplementable from the spec.
6. Report: tests pass/fail per ID, lint result, validator summary, files written, retries consumed.

## Worktree Isolation

For parallel feature work, run the delegation inside an isolated git worktree on a `feature/<slug>` branch. Use whatever worktree mechanism your runtime provides; otherwise the user manages it and merges via normal git flow.

## Phase Transition

> Implementation complete for `<slug>`. The files listed below carry key-namespaced `IMPLEMENTS:`/`COVERS:` headers and `@sdlc {KEY}:REQ-*` tags. Suite passes ({N} tests); validator: {summary}.
> To continue: exit this chat, start a fresh session, and run `/sdlc-review <slug>`.

After delivering this message, end your turn.

## Error Recovery

Interrupted: run `git status --short` to see what was written. Nothing written → re-delegate. Partial files → fix forward or re-delegate with corrections.

## Artefact Trail

| Artifact | Location | Purpose |
|----------|----------|---------|
| Source code | the project's source roots | Implementation, key-namespaced traceability headers |
| Tests | the project's test roots, or beside their sources | Tests per the spec's Test Plan |
