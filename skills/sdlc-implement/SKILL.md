---
name: sdlc-implement
description: Generate code and tests from specification artifacts. Uses single delegation to a coding sub-agent with spec context loaded on demand.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-implement

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, delegating to a coding agent, verifying the test suite, and reporting results to the user. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Drives implementation from spec artifacts using a single delegation to a coding sub-agent. The sub-agent reads spec artifacts **on demand from disk** (progressive disclosure) rather than receiving every artifact inlined — only the project rules are inlined verbatim, because they are small and must never be missed.

## Conventions (read once, apply throughout)

- **Argument → slug**: the user invoked `/sdlc-implement <free-text>`. Slugify it the same way `sdlc-spec` did to locate `.sdlc/specs/<slug>/`. If missing, ask.
- **Feature Key**: read the `**Feature Key:**` from `.sdlc/specs/<slug>/spec.md`. All traceability tags the agent emits are key-namespaced (`@sdlc KEY:REQ-003`). See `.sdlc/CONVENTIONS.md`.
- **Artifact paths (migration-aware)**: read from `.sdlc/` (canonical); fall back to legacy roots if missing. Found legacy-only? Read in place and tell the user to run `/sdlc-migrate` (the validator and keyed-tag checks assume the current layout).
- **Approval**: get an affirmative ("yes" / "ok" / "approved" / "go ahead") on the delegation **before** running it (Tier-2 — one approval covers the whole feature). After the agent returns, present results — no second approval unless retrying.
- **Required input missing**: if `.sdlc/specs/<slug>/spec.md` or `.sdlc/tests/<slug>/test-plan.md` is missing, stop and tell the user to run `/sdlc-spec <slug>` first.
- **Retry cap**: if the agent returns failing tests, re-delegate at most **twice** (3 attempts total), each time including the specific failure context. After the third failure, stop and report the blocker. Do not loop.
- **Verification command fallback**: read test/lint commands from `AGENTS.md`, then `.sdlc/docs/test-strategy.md`. If neither names a runnable command, ask the user — never guess.

## Workflow

### Phase 1: Input Discovery

Read enough to write a correct delegation prompt and to inline the rules:
- `.sdlc/rules.md` (if present) — **inline verbatim** in the delegation (small, load-bearing)
- `.sdlc/specs/<slug>/spec.md` — confirm it exists and read the Feature Key + requirements
- `.sdlc/tests/<slug>/test-plan.md` — confirm it exists
- `AGENTS.md`, `.sdlc/docs/test-strategy.md` — test/lint commands

You do not need to inline the full spec, architecture, or entity dictionary — the sub-agent reads those from disk. You only read enough to validate preconditions and fill the rules block.

### Phase 2: Single Delegation (progressive disclosure)

Show the user the task you're starting. Once approved, delegate the **entire feature** to a single coding agent. The block below is a **prompt template** (not a tool call) — fill the placeholders.

```
Implement the feature "{slug}" (Feature Key: {KEY}) following spec-driven development.

READ THESE FILES FIRST — they are your source of truth (read on demand; do not assume their contents):
- .sdlc/specs/{slug}/spec.md         ← requirements (canonical EARS), API surface, error handling, correctness, entities
- .sdlc/tests/{slug}/test-plan.md    ← the tests you must make pass
- .sdlc/docs/tech.md                 ← stack and constraints
- .sdlc/docs/architecture.md and .sdlc/docs/adr/*.md  ← architecture decisions to honor
- .sdlc/requirements/entity-dictionary.md  ← field names, types, constraints
(If your runtime cannot read files, tell the orchestrator and it will inline them.)

PROJECT RULES (.sdlc/rules.md — refuse to violate any; inlined because they are mandatory):
[Inline rules.md verbatim, or write "No rules file present."]

INSTRUCTIONS:
1. Create all source files under src/ and all test files under tests/.
2. Follow the test plan — every test must pass.
3. Run the test suite after implementation (commands from AGENTS.md / .sdlc/docs/test-strategy.md).
4. Report pass/fail per test.

TRACEABILITY (REQUIRED — all IDs are namespaced by the Feature Key "{KEY}"):
- Top of every generated SOURCE file — header listing the REQ-* AND NFR-* IDs it implements, key-prefixed:
    // GENERATED FROM SPEC: .sdlc/specs/{slug}/spec.md
    // IMPLEMENTS: {KEY}:REQ-001, {KEY}:REQ-003, {KEY}:NFR-002
  Use the target language's comment syntax (// for JS/Go/Rust, # for Python/Ruby, -- for SQL, etc.).
- Top of every generated TEST file — IDs it covers, key-prefixed:
    # COVERS: {KEY}:REQ-002, {KEY}:NFR-001, {KEY}:UT-005, {KEY}:IT-001
- Inline tag each public function/class/handler with the IDs it directly fulfils, comma-separated on one line:
    # @sdlc {KEY}:REQ-003, {KEY}:REQ-004
  Tag only the unit that directly fulfils the requirement — don't sprinkle tags on helpers.
- Every REQ-* and NFR-* in spec.md must appear in at least one source header and one test header. For an NFR listed under "NFRs Validated Outside Code", do NOT emit a fake IMPLEMENTS line — note it in the report instead.
```

Hand the filled-in prompt to a general-purpose coding agent via whatever sub-agent delegation mechanism your runtime exposes. The agent plans its own task breakdown from the spec.

**Fallback for runtimes without file access**: if the sub-agent cannot read files, inline the spec, test plan, and relevant architecture into the prompt as well — the progressive-disclosure form is preferred (it scales to large projects) but inlining is the correct degradation.

### Phase 3: Verification

After delegation returns:
1. Run the test suite (command from `AGENTS.md` → `.sdlc/docs/test-strategy.md` → ask the user).
2. Run the linter from the same source.
3. **Run the traceability validator** if present: `python3 .sdlc/tools/sdlc-validate.py --feature <slug>`. Treat ERROR findings (missing IMPLEMENTS/COVERS for a REQ, dangling or unkeyed tags) as failures to fix.
4. If failures (tests, lint, or validator ERRORs): identify the issue and re-delegate with the specific context. **Retry cap = 2 re-delegations (3 attempts total).** After the third failure, stop and report the blocker — what failed, what was tried, what looks unimplementable from the spec.
5. Report to the user: tests pass/fail per ID, linter pass/fail, validator summary, files written, retry count consumed.

## Worktree Isolation

For parallel feature work, run the delegation inside an isolated git worktree on a feature branch (e.g. `feature/<slug>`) so multiple features can be implemented concurrently without conflicting. Use whatever worktree mechanism your runtime provides; if none, the user manages the worktree manually. The user merges via normal git flow when complete.

## Error Recovery

If the session is interrupted:
- List `src/` and `tests/` to see what was written
- If no files exist, re-delegate
- If partial files exist, fix manually or re-delegate with corrections

## Phase Transition

Once source and test files are written and the suite passes (report delivered), this skill is done. **Do not invoke `/sdlc-review` yourself.** Tell the user (paraphrase as needed):

> Implementation is complete for `<slug>`. Source in `src/` and tests in `tests/` carry key-namespaced `IMPLEMENTS:`/`COVERS:` headers and `@sdlc {KEY}:REQ-*` tags. The test suite passes ({N} tests); validator: {summary}. To continue, exit this chat and start a fresh session, then run `/sdlc-review <slug>`.

After delivering this message, end your turn.

## Artefact Trail

| Artifact | Location | Purpose |
|----------|----------|---------|
| Source code | `{root}/src/` | Implementation per specification, key-namespaced traceability headers |
| Tests | `{root}/tests/` | Tests per test plan |
