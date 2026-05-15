---
name: sdlc-implement
description: Generate code and tests from specification artifacts. Uses single-shot delegation to a coding sub-agent with full spec context.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-implement

> **Execution model**: You (the LLM) execute the **Workflow** sections below — reading files, delegating to a coding agent, verifying the test suite, and reporting results to the user. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. Only the user can start a fresh chat session and trigger another skill. When this skill ends, deliver the Phase Transition message and stop — do not invoke or simulate the next skill.

Drives implementation from spec artifacts using a single delegation to a coding sub-agent with full spec context.

## Conventions (read once, apply throughout)

- **Argument**: the user invoked `/sdlc-implement <free-text>`. Use it verbatim as `{feature}`. If missing, ask.
- **Approval**: get an affirmative reply ("yes" / "ok" / "approved" / "go ahead") on the delegation prompt **before** running it. Anything else is a change request. After the agent returns, present results to the user — no second approval is needed unless retrying.
- **Required input missing**: if any of `specs/{feature}/requirements.md`, `specs/{feature}/design.md`, or `tests/{feature}/test-plan.md` is missing, stop and tell the user which earlier skill to run first. Do not invent.
- **Retry cap**: if the delegated agent returns with failing tests, re-delegate at most **twice**, each time including the specific failure context. After the third total attempt fails, stop and report the blocker to the user. Do not loop indefinitely.
- **Verification command fallback**: read test/lint commands from `AGENTS.md`, then `docs/test-strategy.md`. If neither names a runnable command, ask the user — never guess at `pytest`, `npm test`, etc.

## Workflow

### Phase 1: Input Discovery

Read all preceding artifacts:
- `.sdlc/rules.md` (if present) — invariants the generated code must never violate; include this verbatim in the delegation prompt
- `docs/product.md`, `docs/tech.md`, `docs/test-strategy.md` — steering
- `docs/architecture.md`, `docs/adr/*.md` — architecture
- `requirements/entity-dictionary.md`, `requirements/problem-brief.md` — requirements
- `specs/{feature}/requirements.md` — EARS specs
- `specs/{feature}/design.md` — design
- `tests/{feature}/test-plan.md` — test plan

### Phase 2: Single-Shot Delegation

Show the user which task you're starting. Once approved, delegate the **entire feature** to a single coding agent.

Build the prompt by inlining the artifacts you just read. The block below is a **prompt template** (not a tool call) — replace each `[Read and inline ...]` placeholder with the real file content.

```
Implement the following feature following spec-driven development.

PROJECT RULES (.sdlc/rules.md — refuse to violate any):
[Inline rules verbatim if the file exists, or write "No rules file present."]

PROJECT CONTEXT (from docs/product.md, docs/tech.md):
[Read and inline real content from these files]

SPECS (specs/{feature}/):
- requirements.md: [Read and inline EARS requirements]
- design.md: [Read and inline correctness properties]

TEST PLAN (tests/{feature}/test-plan.md):
[Read and inline test plan]

INSTRUCTIONS:
1. Create all source files under src/
2. Create all test files under tests/
3. Follow the test plan — every test must pass
4. Run the test suite after implementation (use commands from AGENTS.md / docs/test-strategy.md)
5. Report pass/fail per test

TRACEABILITY (REQUIRED):
- At the top of every generated source file, emit a header comment listing the REQ-* AND NFR-* IDs it implements:
    // GENERATED FROM SPEC: specs/{feature}/requirements.md
    // IMPLEMENTS: REQ-001, REQ-003, REQ-004, NFR-002
  Use the comment syntax of the target language (`//` for JS/Go/Rust, `#` for Python/Ruby, `--` for SQL, etc.).
- At the top of every generated test file, list the REQ-*, NFR-*, and test-plan IDs it covers:
    # COVERS: REQ-002, NFR-001, UT-005, IT-001
- Inline tag each public function/class/handler with the IDs it serves, comma-separated on one line:
    # @sdlc REQ-003, REQ-004
    def validate_login(...):
  Tag only the unit that directly fulfils the requirement — don't sprinkle tags on every helper.
- Every REQ-* and NFR-* in requirements.md must appear in at least one source-file header and one test-file header. If an NFR-* is validated outside code (per the "NFRs Validated Outside Code" section of requirements.md), say so explicitly in the report — do NOT emit a fake `IMPLEMENTS: NFR-*` line for it.
```

Hand the filled-in prompt to a general-purpose coding agent using whatever sub-agent delegation mechanism your runtime exposes. The exact tool name varies by runtime — use the one available to you. The agent plans its own task breakdown from the EARS requirements and design doc — no separate task file needed.

### Phase 3: Verification

After delegation returns:
1. Run the test suite using the command from `AGENTS.md` → `docs/test-strategy.md` → (if neither names one) ask the user.
2. Run the linter from the same source.
3. If failures: identify the issue and re-delegate with the specific failure context. **Retry cap = 2 re-delegations (3 attempts total).** After the third failure, stop and report the blocker — describe what failed, what was tried, and what looks unimplementable from the spec. Do not loop further.
4. Report results to the user: tests pass/fail per ID, linter pass/fail, files written, retry count consumed.

## Worktree Isolation

For parallel feature work, run the delegation inside an isolated git worktree on a feature branch (e.g. `feature/{feature-name}`) so multiple features can be implemented concurrently without conflicting in the working tree. Use whatever worktree-isolation mechanism your runtime provides for sub-agent invocations; if none is available, the user is responsible for managing the worktree manually.

The user merges via normal git flow when the feature is complete.

## Error Recovery

If the session is interrupted:
- List `src/` and `tests/` to see what was written
- If no files exist, re-delegate
- If partial files exist, fix manually or re-delegate with corrections

## Phase Transition

Once the source and test files are written and the test suite passes (with the report delivered to the user), this skill is done. **Do not invoke `/sdlc-review` yourself** — only the user can start a fresh chat and trigger it. Tell the user (paraphrase as needed):

> Implementation is complete for `{feature}`. Source files in `src/` and tests in `tests/` carry `IMPLEMENTS:`/`COVERS:` headers and `@sdlc REQ-*` tags. The test suite passes ({N} tests). To continue, exit this chat and start a fresh session, then run `/sdlc-review {feature}` for a fresh-context compliance review.

After delivering this message, end your turn.

## Artefact Trail

| Artifact | Location | Purpose |
|----------|----------|---------|
| Source code | `{root}/src/` | Implementation per specification |
| Tests | `{root}/tests/` | Tests per test plan |