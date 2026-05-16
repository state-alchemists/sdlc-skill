# SDLC AI Plugin

**Skills, not CLI commands.** This plugin provides 10 chat skills (`/sdlc-init`, `/sdlc-requirements`, etc.) that guide an LLM through Spec-Driven Development.

**Primary target: zrb.** Also runs under Claude Code — skills are runtime-neutral, so the LLM picks the right tool either way (see [Runtime Compatibility](#runtime-compatibility)).

---

## Installation

### One-liner (recommended)

```bash
bin/install.sh --all          # install to both ~/.zrb/skills/ and ~/.claude/skills/
bin/install.sh                # auto-detect — install only to runtimes that exist on this machine
bin/install.sh --uninstall    # remove sdlc-* skills from detected targets
bin/install.sh --dry-run --all # preview without changing anything
```

The installer is portable bash (works on macOS's bash 3.2), replaces any prior copy of each skill atomically, and never touches non-`sdlc-*` skills in your target directories.

### Manual (if you prefer)

**zrb:**
```bash
mkdir -p ~/.zrb/skills && cp -R skills/sdlc-* ~/.zrb/skills/
```

**Claude Code:**
```bash
mkdir -p ~/.claude/skills && cp -R skills/sdlc-* ~/.claude/skills/
```

Both runtimes scan their skills directory on startup; skills become available as `/sdlc-init`, `/sdlc-requirements`, etc. Claude Code ignores the `disable-model-invocation` and `user-invocable` frontmatter (zrb-specific) but otherwise loads the skills as-is.

---

## Quick Start

In a chat session, activate a skill by name:

```
# Main pipeline (in order)
/sdlc-init                # 1. Steering docs
/sdlc-rules               # 2. Project constitution (invariants — read by every later skill)
/sdlc-requirements        # 3. PRD + entity dictionary
/sdlc-architect           # 4. ADRs + architecture
/sdlc-spec <feature>      # 5. EARS specs + design
/sdlc-test-plan <feature> # 6. Test plans
/sdlc-implement <feature> # 7. Code + tests (with @sdlc REQ-* traceability tags)
/sdlc-review <feature>    # 8. Spec-compliance + traceability review

# Lightweight & maintenance skills (invoke as needed)
/sdlc-quickfix <feature>  # Delta-format path for bug fixes / small changes
/sdlc-document <scope>    # Reverse-engineer specs from existing code (drift recovery)
```

---

## Architecture

```
~/.zrb/skills/   or   ~/.claude/skills/   # ← Installed here (scanned automatically)
  sdlc-init/SKILL.md            # Steering docs (templates inlined)
  sdlc-rules/SKILL.md           # Project constitution (invariants)
  sdlc-requirements/SKILL.md    # PRD + entity dictionary
  sdlc-architect/SKILL.md       # ADRs + C4 architecture
  sdlc-spec/SKILL.md            # EARS specs + design
  sdlc-test-plan/SKILL.md       # Test plans
  sdlc-implement/SKILL.md       # Code generation (single-shot delegation)
  sdlc-review/SKILL.md          # Spec compliance review
  sdlc-quickfix/SKILL.md        # Delta-format lightweight path
  sdlc-document/SKILL.md        # Reverse-engineer specs from code

sdlc-skill/                     # ← Source repo
  bin/install.sh                #   Portable installer for zrb / Claude Code
  evals/                        #   Golden examples per skill (regression harness skeleton)
```

## Runtime Compatibility

Skills are runtime-neutral: they describe **what** the LLM should do (list a directory, read files in parallel, delegate to a sub-agent, run in an isolated git worktree), not **which tool** to use. The LLM picks the appropriate tool from whichever runtime it's executing in.

The delegation blocks inside `sdlc-implement`, `sdlc-review`, and `sdlc-quickfix` are **prompt templates** — fill the placeholders with file content and submit via the runtime's sub-agent mechanism.

---

## Real-World Scenarios

### Scenario A: Greenfield Project (New Todo App)

You're starting a new project from scratch. The full pipeline applies.

Each phase runs in its own fresh chat session — exit and start a new one between phases so context doesn't accumulate.

```
# Phase 1: Define the project (fresh chat)
/sdlc-init
# → LLM asks: what's the product? who uses it? scope? stakeholders? tech stack? test strategy?
# → Approve docs/product.md, docs/tech.md, docs/test-strategy.md, AGENTS.md

# Phase 2: Constitution (fresh chat)
/sdlc-rules
# → Bans: raw SQL, eval(), unencrypted credential storage
# → Requires: structured logging, dependency injection for external services
# → Writes .sdlc/rules.md — every later skill reads it

# Phase 3: Requirements (fresh chat)
/sdlc-requirements
# → Problem brief written: "a personal task manager"
# → Entities extracted from stories: User, TodoList, TodoItem

# Phase 4: Architecture (fresh chat)
/sdlc-architect
# → ADRs: SQLite for storage, FastAPI + HTMX, JWT auth (each cites the RULE-* it honors)

# Phase 5: Feature spec (fresh chat)
/sdlc-spec user-authentication
# → EARS: WHEN user submits login form, SHALL validate credentials
# → Design: round-trip (session create/destroy), uniqueness (no duplicate emails)

# Phase 6: Test plan (fresh chat)
/sdlc-test-plan user-authentication
# → Test plan: unit tests for password hashing, integration for login endpoint

# Phase 7: Implementation (fresh chat)
/sdlc-implement user-authentication
# → Generates src/auth.py with IMPLEMENTS: REQ-001, REQ-002... header
# → Generates tests/test_auth.py with COVERS: REQ-001, UT-001... header
# → Pytest runs, all pass

# Phase 8: Review (fresh chat)
/sdlc-review user-authentication
# → Validates: every REQ-* has code, traceability tags, no RULE-* violations
# → Report: 8/8 requirements covered, 3 entity fields match dictionary, 0 rule violations
```

**After auth is done**, add the next feature (`todo-crud`) starting from `/sdlc-spec todo-crud`. The steering docs, requirements, and architecture already exist — each new feature builds on them.

---

### Scenario B: Adding a Feature to an Existing Project

Your project already has code, steering docs, and architecture. You only need phases 4-7.

```
# Steering docs already exist at docs/product.md, docs/tech.md
# Requirements at requirements/*.md
# Architecture at docs/architecture.md, docs/adr/

/sdlc-spec payment-processing
# → Reads existing docs automatically
# → Generates EARS specs for payment flow

# (fresh chat)
/sdlc-test-plan payment-processing

# (fresh chat)
/sdlc-implement payment-processing

# (fresh chat)
/sdlc-review payment-processing
```

**Multiple features in parallel**: run `/sdlc-spec payment-processing` and `/sdlc-spec notification-service` in separate chat sessions. Each writes to `specs/payment-processing/` and `specs/notification-service/` — no file conflicts.

---

### Scenario C: Bug Fix (Lightweight Path)

Not every change needs the full pipeline. For a small bug fix, skip the planning phases:

```
# Steering docs, requirements, architecture already exist
# Just implement and review

/sdlc-spec fix-login-error-handling
# → EARS: WHEN login returns 500, SHALL show friendly error message
# → Design: add error boundary in auth handler

# (fresh chat)
/sdlc-implement fix-login-error-handling
# → Delegates with the EARS spec

# (fresh chat)
/sdlc-review fix-login-error-handling
```

You can skip `/sdlc-test-plan` for trivial changes — the implement skill still runs tests against existing suites.

---

### Scenario D: Evolving Specs After Code Changes

Specs are **snapshots, not living documents**. If you change the code later, old specs don't auto-update. This is a known limitation shared by every SDD tool in 2026.

**When specs drift from code**, the recommended approach is:

1. Run `/sdlc-document {scope}` to reverse-engineer specs from the current code. If prior specs exist, this also writes a `drift-report-{timestamp}.md` showing what's UNCHANGED / MODIFIED / ADDED / REMOVED-from-code.
2. Decide per-finding whether to absorb the change into the spec (keep `sdlc-document`'s output) or close the gap in the code (run `/sdlc-quickfix {feature}`).
3. Run `/sdlc-review {feature}` for a fresh compliance check once specs and code agree.

---

## Skills Reference

### 1. `sdlc-init` — Project Kickoff

Produces four steering documents via interactive interview:

| Document | Content |
|----------|---------|
| `docs/product.md` | Problem, users, success criteria, scope, stakeholders |
| `docs/tech.md` | Languages, frameworks, DB, infra, principles |
| `docs/test-strategy.md` | Testing levels, CI gates, environments |
| `AGENTS.md` | AI assistant guide |

```
/sdlc-init
# Answer the interview questions one at a time. Approve each document before writing.
# Then: exit → fresh chat → /sdlc-requirements
```

### 2. `sdlc-rules` — Project Constitution

| Document | Content |
|----------|---------|
| `.sdlc/rules.md` | `RULE-*` invariants (forbidden patterns, required patterns, compliance, coding standards) + Override Log |

Read by every later skill as a precondition. Invoke once after `sdlc-init`, and again whenever a new invariant is identified.

```
/sdlc-rules
```

### 3. `sdlc-requirements` — Requirements Elicitation

| Document | Content |
|----------|---------|
| `requirements/problem-brief.md` | PRD with user stories, acceptance criteria |
| `requirements/entity-dictionary.md` | Entities, fields, types, constraints |

```
/sdlc-requirements
```

### 4. `sdlc-architect` — Architecture Decisions

| Document | Content |
|----------|---------|
| `docs/adr/ADR-*.md` | Decision records (Status/Context/Decision/Consequences/Compliance) |
| `docs/architecture.md` | C4 Level 1-3, data flow, deployment |

```
/sdlc-architect
```

### 5. `sdlc-spec` — Feature Specifications (EARS)

| Document | Content |
|----------|---------|
| `specs/{feature}/requirements.md` | EARS: WHEN/THEN SHALL, ALWAYS SHALL, UNLESS |
| `specs/{feature}/design.md` | Correctness properties + API surface + errors |

```
/sdlc-spec user-authentication
```

### 6. `sdlc-test-plan` — Test Generation

| Document | Content |
|----------|---------|
| `tests/{feature}/test-plan.md` | Unit, integration, E2E, property-based tests |

```
/sdlc-test-plan user-authentication
```

### 7. `sdlc-implement` — Code Generation

Single-shot delegation to a coding agent with full spec context. Writes all source and test files, then runs the test suite. Every generated source file gets `IMPLEMENTS: REQ-*` headers and inline `@sdlc REQ-*` tags for traceability; every test file gets `COVERS: REQ-*, UT-*` headers.

```
/sdlc-implement user-authentication
```

### 8. `sdlc-review` — Spec Compliance Review

Delegates to a code-review agent, then validates seven checks:
- EARS coverage (every `REQ-*` and `NFR-*` has code + test, or — for NFRs — a documented out-of-code validation mechanism)
- Correctness properties (round-trip, uniqueness, atomicity, validation, idempotency)
- Entity fidelity (fields match dictionary)
- ADR compliance (code follows decisions)
- Rules compliance (no `RULE-*` violation without an Override Log entry)
- Test coverage (test plan tests exist and pass)
- Traceability (every `REQ-*`/`NFR-*` reachable from source headers + test headers + inline tags)

Reports are written feature-scoped at `review/{feature}/report-{timestamp}.md`.

```
/sdlc-review user-authentication
```

### 9. `sdlc-quickfix` — Delta-Format Lightweight Path

For changes too small to justify the full pipeline (bug fixes, copy tweaks, single-property additions). Produces a dated `quickfix-{timestamp}.md` with `ADDED/MODIFIED/REMOVED` requirement and test deltas against existing specs, then implements the delta in one shot with inline review. Skips `sdlc-test-plan` and `sdlc-review`.

| Document | Content |
|----------|---------|
| `specs/{feature}/quickfix-{timestamp}.md` | Delta record (ADDED/MODIFIED/REMOVED requirements + tests) |

```
/sdlc-quickfix user-authentication
# Describe the change in one sentence. Approve the delta. Done.
```

Use this for the "change button from blue to green" class of work that the full pipeline would otherwise turn into a multi-story spec.

### 10. `sdlc-document` — Reverse-Engineer Specs From Code

Closes the drift loop the other way: reads existing source + tests and produces (or regenerates) `requirements.md` and `design.md` to match what the code actually does. Produces a `drift-report-{timestamp}.md` when prior specs existed.

| Document | Content |
|----------|---------|
| `specs/{feature}/requirements.md` | Reverse-engineered EARS |
| `specs/{feature}/design.md` | Reverse-engineered correctness properties |
| `specs/{feature}/drift-report-{timestamp}.md` | UNCHANGED / MODIFIED / ADDED / REMOVED-from-code diff (only if prior specs existed) |

```
/sdlc-document src/auth/
```

Use for brownfield onboarding or after `sdlc-review` flags drift.

---

## Traceability

Source files generated by `sdlc-implement` (and modifications by `sdlc-quickfix`) carry traceability tags so the spec → code link survives refactors.

**Source file header** (lists every REQ-* and NFR-* satisfied by the file):
```python
# GENERATED FROM SPEC: specs/user-authentication/requirements.md
# IMPLEMENTS: REQ-001, REQ-003, REQ-004, NFR-002
```

**Test file header** (lists REQ-*, NFR-*, and test-plan IDs covered):
```python
# COVERS: REQ-002, NFR-001, UT-005, IT-001
```

**Inline tag on the unit that fulfils requirements** (comma-separated for multi-ID):
```python
# @sdlc REQ-003, REQ-004
def validate_login(...):
    ...
```

NFRs that are validated **outside code** (e.g. WAF rules, SLO dashboards, infra modules) are NOT given fake `IMPLEMENTS:` lines — they're listed under the "NFRs Validated Outside Code" section of `specs/{feature}/requirements.md` with the validation mechanism named.

`sdlc-review` enforces these — a missing `IMPLEMENTS:` for a known `REQ-*`/`NFR-*` or an `@sdlc` tag referencing a non-existent ID produces a FAIL in the Traceability check. Inspection commands:

```bash
grep -rnE "IMPLEMENTS: "          src/
grep -rnE "COVERS: "              tests/
grep -rnE "@sdlc (REQ|NFR)-"      src/ tests/
```

---

## Context Management

Each phase runs in a **fresh chat session** to prevent context accumulation:

1. Finish the current phase and approve its artifacts.
2. Exit the chat (Ctrl+C or `/exit`).
3. Start a new chat session.
4. Run the next phase — it reads artifacts from disk, not from prior chat history.

Artifacts on disk (`docs/`, `requirements/`, `specs/`, `tests/`, `src/`) are the durable state. Conversation history is auxiliary.

> If your runtime offers a conversation-persistence command (e.g. zrb's `/save` and `/load`), use it freely between phases — the skills don't depend on it.

---

## Generated Project Structure

After running the full pipeline, the project has this deterministic layout (the only variable is `{feature}`):

```
<project-root>/
├── .sdlc/                             # Constitution (sdlc-rules)
│   └── rules.md                       #   Project invariants — read by every later skill
├── docs/                              # Phase 1: Steering (sdlc-init)
│   ├── product.md                     #   Problem, users, success criteria
│   ├── tech.md                        #   Languages, frameworks, DB, infra
│   ├── test-strategy.md               #   Testing levels, CI gates
│   ├── architecture.md                #   Phase 4: C4 model (sdlc-architect)
│   └── adr/                           #   Architecture Decision Records
│       ├── ADR-001-database-choice.md
│       ├── ADR-002-api-architecture.md
│       └── ...
├── requirements/                      # Phase 3: Requirements (sdlc-requirements)
│   ├── problem-brief.md               #   PRD with US-* stories and AC-* acceptance criteria
│   └── entity-dictionary.md           #   Entities, fields, types, constraints (merged on re-run)
├── specs/                             # Phase 5: Feature specs (sdlc-spec)
│   └── {feature}/                     #   One directory per feature
│       ├── requirements.md            #   EARS REQ-* + NFR-* (each citing its source AC-*)
│       ├── design.md                  #   Correctness properties, API surface, errors
│       ├── quickfix-{ts}.md           #   (Optional) one or more dated deltas from sdlc-quickfix
│       └── drift-report-{ts}.md       #   (Optional) drift diff from sdlc-document
├── tests/                             # Phase 6+7: Tests (sdlc-test-plan + implement)
│   └── {feature}/                     #   Test plan and test code
│       └── test-plan.md               #   Unit, integration, E2E, property-based tests
│   └── (test files from implement, with COVERS: REQ-*/NFR-* headers)
├── review/                            # Phase 8: Review reports (sdlc-review)
│   └── {feature}/                     #   Feature-scoped — multi-feature projects stay sorted
│       └── report-{ts}.md             #   Compliance + traceability verdict
├── src/                               # Phase 7: Source code (sdlc-implement, with IMPLEMENTS: REQ-*/NFR-* headers + @sdlc REQ-* tags)
└── AGENTS.md                          # Phase 1: AI assistant guide (sdlc-init)
```

All paths are hardcoded in the SKILL.md files. The only user choice is the `{feature}` name (or `{scope}` for `sdlc-document`) passed to the feature-level skills.

Each skill reads the artifacts it needs from these deterministic paths. For example, `/sdlc-spec` reads `.sdlc/rules.md`, `docs/product.md`, `requirements/entity-dictionary.md`, etc. before generating specs.

---

## Evals

`evals/` holds golden examples per skill — the foothold for measuring whether prompt changes improve or regress output quality. The runner is not implemented yet; the structure and authoring guide are in [`evals/README.md`](evals/README.md), with one case under `evals/golden/sdlc-init/personal-todo-app/` (input + rubric authored; expected outputs not yet committed). Contributions of additional cases are the cheapest way to harden the plugin.

---

## Key Design Limitations

- **No CLI commands** — `zrb sdlc init` does not exist. Only chat skills (`/sdlc-init`, etc.). The installer is the only shell entry point.
- **No runtime approval enforcement** — `Write`/`Edit`/`Bash` are not gated by `ToolPolicy`. Approval relies on the LLM following instructions in the skill.
- **No validation tools** — no EARS syntax validator, no ADR compliance checker, no entity cross-reference tool. Traceability is enforced by `grep` patterns, not a real parser.
- **No hook integration** — no `SESSION_START`/`SESSION_END` hooks for automated phase validation.
- **No MCP server** — generic MCP-aware agents outside zrb/Claude Code can't consume these skills directly yet.
- **No eval runner** — `evals/` has structure and one case, but no automated grader. Today's evals are read by humans.
- **Specs still drift** — `sdlc-document` closes the loop manually, but there is no automated re-sync after every commit. This is a known limitation shared by every SDD tool in 2026.
