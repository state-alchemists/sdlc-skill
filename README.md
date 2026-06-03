# SDLC AI Plugin

**Skills, not CLI commands.** This plugin provides 8 chat skills (`/sdlc-init`, `/sdlc-requirements`, etc.) that guide an LLM through Spec-Driven Development.

**Primary target: zrb.** Also runs under Claude Code — skills are runtime-neutral, so the LLM picks the right tool either way (see [Runtime Compatibility](#runtime-compatibility)).

---

## Installation

### One-liner (recommended)

```bash
bin/install.sh --tools all                    # install to all 30+ known AI coding tools
bin/install.sh --tools codex,opencode,cursor  # install to specific tools (comma-separated)
bin/install.sh                                # auto-detect — install only to tools already on this machine
bin/install.sh --uninstall --tools all        # remove sdlc-* skills from all targets
bin/install.sh --dry-run --tools cursor       # preview without changing anything
```

The installer is portable bash (works on macOS's bash 3.2), supports all major AI coding assistants (zrb, Claude Code, Codex, OpenCode, Cursor, Windsurf, GitHub Copilot, Gemini CLI, Cline, and 20+ more), replaces any prior copy of each skill atomically, and never touches non-`sdlc-*` skills in your target directories.

### Manual (if you prefer)

The installer does this under the hood. To install manually:

```bash
# zrb
mkdir -p ~/.zrb/skills && cp -R skills/sdlc-* ~/.zrb/skills/

# Codex
mkdir -p ~/.codex/skills && cp -R skills/sdlc-* ~/.codex/skills/

# OpenCode
mkdir -p ~/.opencode/skills && cp -R skills/sdlc-* ~/.opencode/skills/

# Cursor
mkdir -p ~/.cursor/skills && cp -R skills/sdlc-* ~/.cursor/skills/

# Any other tool — same pattern: <dotdir>/skills/
```

All runtimes scan their skills directory on startup; skills become available as `/sdlc-init`, `/sdlc-requirements`, etc. Claude Code ignores the `disable-model-invocation` and `user-invocable` frontmatter (zrb-specific) but otherwise loads the skills as-is.

---

## Quick Start

In a chat session, activate a skill by name:

```
# Main pipeline (in order)
/sdlc-init                # 1. Steering docs + project constitution
/sdlc-requirements        # 2. PRD + entity dictionary
/sdlc-architect           # 3. ADRs + architecture
/sdlc-spec <feature>      # 4. Spec + design + test plan (one session)
/sdlc-implement <feature> # 5. Code + tests (with @sdlc REQ-* traceability tags)
/sdlc-review <feature>    # 6. Spec-compliance + traceability review

# Lightweight & maintenance skills (invoke as needed)
/sdlc-quickfix <feature>  # Delta-format path for bug fixes / small changes
/sdlc-document <scope>    # Reverse-engineer specs from existing code (drift recovery)
```

---

## How This Maps to Scrum

The SDLC phases are **artifact stages**, not time-boxed ceremonies. For teams coming from Scrum, the rough mapping:

| SDLC phase | Scrum parallel |
|---|---|
| `sdlc-init` | Sprint Zero — vision, tech stack, Definition of Done (invariants) |
| `sdlc-requirements` | Product backlog creation — epics and user stories |
| `sdlc-architect` | Architecture spike / technical design |
| `sdlc-spec <feature>` | Backlog refinement + test-case design — moving a story to "Ready" |
| `sdlc-implement <feature>` | Sprint development work |
| `sdlc-review <feature>` | Code review + Definition of Done check |
| `sdlc-quickfix` | Hotfix / unplanned work lane |
| `sdlc-document` | Spike / discovery / tech-debt onboarding |

**Mental model:**

- Phases 1–3 run **once per project** (your "sprint zero").
- Phases 4–6 run **once per feature**, looped multiple times per sprint.
- Phases 7–8 are **out-of-band lanes** for hotfixes and drift recovery.

**What merged and why:**

- `sdlc-rules` was merged into `sdlc-init` — rules are a natural follow-on in the same project-setup conversation. The LLM can flow from "what's your stack?" to "what do you forbid?" without a session boundary.
- `sdlc-test-plan` was merged into `sdlc-spec` — the test plan is a structural derivative of the spec. It introduces no new domain knowledge; separating it meant re-reading the same files in a fresh session for a mechanical mapping.

**Where the analogy breaks:** the skills don't replace standups, retros, estimation, or timeboxing — those are human ceremonies that still belong to your team. SDD gives you the *artifacts*; Scrum gives you the *cadence*.

---

## Architecture

Skills are installed into the tool's skills directory. The installer copies the `skills/` directory from this repo into each target's dot-directory:

```
~/.zrb/skills/              or  ~/.claude/skills/          or  ~/.codex/skills/       # ← whichever you picked
  sdlc-init/SKILL.md            # Steering docs + project constitution
  sdlc-requirements/SKILL.md    # PRD + entity dictionary
  sdlc-architect/SKILL.md       # ADRs + C4 architecture
  sdlc-spec/SKILL.md            # EARS spec + design + test plan (one session)
  sdlc-implement/SKILL.md       # Code generation (single-shot delegation)
  sdlc-review/SKILL.md          # Spec compliance review
  sdlc-quickfix/SKILL.md        # Delta-format lightweight path
  sdlc-document/SKILL.md        # Reverse-engineer specs from code

sdlc-skill/                     # ← Source repo
  bin/install.sh                #   Portable bash installer (detects 30+ tools)
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
# Phase 1: Project setup (fresh chat)
/sdlc-init
# → LLM asks: what's the product? who uses it? scope? tech stack? test strategy?
# → Approve .sdlc/docs/product.md, .sdlc/docs/tech.md, .sdlc/docs/test-strategy.md, AGENTS.md
# → LLM then asks: banned patterns? security requirements? coverage thresholds?
# → Approve .sdlc/rules.md — every later skill reads it

# Phase 2: Requirements (fresh chat)
/sdlc-requirements
# → Problem brief written: "a personal task manager"
# → Entities extracted from stories: User, TodoList, TodoItem

# Phase 3: Architecture (fresh chat)
/sdlc-architect
# → ADRs: SQLite for storage, FastAPI + HTMX, JWT auth (each cites the RULE-* it honors)

# Phase 4: Feature spec + test plan (fresh chat)
/sdlc-spec user-authentication
# → Spec: flat EARS requirements, API surface, error handling, correctness properties
# → Test plan: maps each REQ-* to unit/integration/E2E tests
# → Approve both, then exit

# Phase 5: Implementation (fresh chat)
/sdlc-implement user-authentication
# → Generates src/auth.py with IMPLEMENTS: REQ-001, REQ-002... header
# → Generates tests/test_auth.py with COVERS: REQ-001, UT-001... header
# → Pytest runs, all pass

# Phase 6: Review (fresh chat)
/sdlc-review user-authentication
# → Validates: every REQ-* has code, traceability tags, no RULE-* violations
# → Report: 8/8 requirements covered, 3 entity fields match dictionary, 0 rule violations
```

**After auth is done**, add the next feature (`todo-crud`) starting from `/sdlc-spec todo-crud`. The steering docs, requirements, and architecture already exist — each new feature builds on them.

---

### Scenario B: Adding a Feature to an Existing Project

Your project already has code, steering docs, and architecture. You only need phases 4-6.

```
# Steering docs already exist at .sdlc/docs/product.md, .sdlc/docs/tech.md
# Requirements at .sdlc/requirements/*.md
# Architecture at .sdlc/docs/architecture.md, .sdlc/docs/adr/

/sdlc-spec payment-processing
# → Reads existing docs automatically
# → Generates spec.md (requirements + design) and test-plan.md

# (fresh chat)
/sdlc-implement payment-processing

# (fresh chat)
/sdlc-review payment-processing
```

**Multiple features in parallel**: run `/sdlc-spec payment-processing` and `/sdlc-spec notification-service` in separate chat sessions. Each writes to `.sdlc/specs/payment-processing/` and `.sdlc/specs/notification-service/` — no file conflicts.

---

### Scenario C: Bug Fix (Lightweight Path)

Not every change needs the full pipeline. For a small bug fix, skip the planning phases:

```
# Steering docs, requirements, architecture already exist
# Just implement and review

/sdlc-spec fix-login-error-handling
# → EARS: WHEN login returns 500, SHALL show friendly error message

# (fresh chat)
/sdlc-implement fix-login-error-handling
# → Delegates with the EARS spec

# (fresh chat)
/sdlc-review fix-login-error-handling
```

You can skip the test plan for trivial changes — the implement skill still runs tests against existing suites.

---

### Scenario D: Evolving Specs After Code Changes

Specs are **snapshots, not living documents**. If you change the code later, old specs don't auto-update. This is a known limitation shared by every SDD tool in 2026.

**When specs drift from code**, the recommended approach is:

1. Run `/sdlc-document {scope}` to reverse-engineer specs from the current code. If prior specs exist, this also writes a `drift-report-{timestamp}.md` showing what's UNCHANGED / MODIFIED / ADDED / REMOVED-from-code.
2. Decide per-finding whether to absorb the change into the spec (keep `sdlc-document`'s output) or close the gap in the code (run `/sdlc-quickfix {feature}`).
3. Run `/sdlc-review {feature}` for a fresh compliance check once specs and code agree.

### Scenario E: Reverse-Engineering Code With No Prior SDLC Setup

You have an existing codebase with no `.sdlc/` directory, no `AGENTS.md`, and no specs. You want to start using SDLC on it without starting from scratch.

```
# State: src/auth/ exists, tests/auth/ exists, no .sdlc/ directory, no AGENTS.md

/sdlc-document src/auth/
# → LLM notes: no .sdlc/ directory, no prior SDLC setup — zero-baseline run
# → Reads source and test files, extracts behaviour
# → Generates .sdlc/specs/auth/spec.md from code
# → Warns: "No entity dictionary found — entities inferred from code alone.
#   Consider running /sdlc-init and /sdlc-requirements to add project-wide scaffolding."
#
# Spec written. Now bring the project into the SDLC fold:

# (fresh chat)
/sdlc-init
# → Brownfield path: extracts what it can from the codebase, interviews for the rest
# → Writes .sdlc/docs/*, AGENTS.md, .sdlc/rules.md

# (fresh chat)
/sdlc-requirements
# → Extracts entities from the codebase and the new spec
# → Writes .sdlc/requirements/problem-brief.md and .sdlc/requirements/entity-dictionary.md

# Project is now fully bootstrapped. Future features follow the normal pipeline.
```

### Scenario F: Reverse-Engineering When Old-Format Specs Exist

Your project was last touched before the spec-document merge (i.e., before `requirements.md` and `design.md` were merged into `spec.md`). You have old-format specs at `.sdlc/specs/auth/requirements.md` and `.sdlc/specs/auth/design.md` but no `spec.md`.

```
# State: .sdlc/specs/auth/requirements.md + design.md exist (old format), no spec.md

/sdlc-document src/auth/
# → LLM detects old format: "Found old-format specs: requirements.md and design.md
#   (pre-merge format). Would you like me to use them as the baseline,
#   ignore them and start fresh, or abort?"
#
# You: Use them as baseline
#
# → LLM reads both old files, combines into a unified mental model
# → Reverse-engineers from code, diffs against combined baseline
# → Writes .sdlc/specs/auth/spec.md (new format)
# → Drift report notes: "Baseline: old-format specs (requirements.md + design.md)"
# → Asks: "Remove the old requirements.md and design.md files now?"
#
# You: Yes
#
# → Old files removed. Spec is migrated to the current format.
```



### 1. `sdlc-init` — Project Kickoff + Constitution

Produces four steering documents plus project invariants:

| Document | Content |
|----------|---------|
| `.sdlc/docs/product.md` | Problem, users, success criteria, scope, stakeholders |
| `.sdlc/docs/tech.md` | Languages, frameworks, DB, infra, principles |
| `.sdlc/docs/test-strategy.md` | Testing levels, CI gates, environments |
| `AGENTS.md` | AI assistant guide |
| `.sdlc/rules.md` | `RULE-*` invariants (forbidden patterns, required patterns, compliance, coding standards) + Override Log |

Read by every later skill as a precondition. Formerly two separate skills (`sdlc-init` + `sdlc-rules`), now one session.

```
/sdlc-init
# Answer the interview questions. Approve steering docs, then answer the rules interview.
# Then: exit → fresh chat → /sdlc-requirements
```

### 2. `sdlc-requirements` — Requirements Elicitation

| Document | Content |
|----------|---------|
| `.sdlc/requirements/problem-brief.md` | PRD with user stories, acceptance criteria |
| `.sdlc/requirements/entity-dictionary.md` | Entities, fields, types, constraints |

```
/sdlc-requirements
```

### 3. `sdlc-architect` — Architecture Decisions

| Document | Content |
|----------|---------|
| `.sdlc/docs/adr/ADR-*.md` | Decision records (Status/Context/Decision/Consequences/Compliance) |
| `.sdlc/docs/architecture.md` | C4 Level 1-3, data flow, deployment |

```
/sdlc-architect
```

### 4. `sdlc-spec` — Feature Spec + Design + Test Plan

Produces a single merged spec and a structured test plan in one session. Formerly three separate skills (`sdlc-spec` + `sdlc-test-plan`), now one — the test plan is a structural derivative of the spec.

| Document | Content |
|----------|---------|
| `.sdlc/specs/{feature}/spec.md` | EARS requirements (flat list, no category headers), API surface, error handling, correctness properties |
| `.sdlc/tests/{feature}/test-plan.md` | Unit, integration, E2E, property-based tests |

```
/sdlc-spec user-authentication
```

**Choosing the `<feature>` slice.** Features come from the `US-*` user stories in `.sdlc/requirements/problem-brief.md` — there's no automated breakdown, you pick the slice. The string is used verbatim as the directory name under `.sdlc/specs/` (no normalization, no slugification).

Sizing heuristic:

- **Too small** → trivial deltas churn the pipeline; use `/sdlc-quickfix` instead.
- **Too big** → EARS sprawls and `sdlc-implement`'s single-shot delegation struggles.
- **Sweet spot** → one user-visible capability, ~3–10 `REQ-*` entries, implementable in one coding session.

Example. Given a problem brief with these stories:

```
US-001: As a user, I want to sign up with email and password
US-002: As a user, I want to log in and stay signed in
US-003: As a user, I want to create todo lists
US-004: As a user, I want to add items to a list
US-005: As a user, I want to mark items complete
US-006: As a user, I want to share a list with another user
```

A reasonable carve, in dependency order:

```
/sdlc-spec user-authentication    # US-001, US-002
/sdlc-spec todo-crud              # US-003, US-004, US-005
/sdlc-spec list-sharing           # US-006 (depends on auth + crud)
```

If a brief feels too vague to carve, that's a signal to revisit `/sdlc-requirements` and tighten the stories first.

### 5. `sdlc-implement` — Code Generation

Single-shot delegation to a coding agent with full spec context. Writes all source and test files, then runs the test suite. Every generated source file gets `IMPLEMENTS: REQ-*` headers and inline `@sdlc REQ-*` tags for traceability; every test file gets `COVERS: REQ-*, UT-*` headers.

```
/sdlc-implement user-authentication
```

### 6. `sdlc-review` — Spec Compliance Review

Delegates to a code-review agent, then validates seven checks:
- EARS coverage (every `REQ-*` and `NFR-*` has code + test, or — for NFRs — a documented out-of-code validation mechanism)
- Correctness properties (round-trip, uniqueness, atomicity, validation, idempotency — only those listed in the spec)
- Entity fidelity (fields match dictionary)
- ADR compliance (code follows decisions)
- Rules compliance (no `RULE-*` violation without an Override Log entry)
- Test coverage (test plan tests exist and pass)
- Traceability (every `REQ-*`/`NFR-*` reachable from source headers + test headers + inline tags)

Reports are written feature-scoped at `.sdlc/reviews/{feature}/report-{timestamp}.md`.

```
/sdlc-review user-authentication
```

### 7. `sdlc-quickfix` — Delta-Format Lightweight Path

For changes too small to justify the full pipeline (bug fixes, copy tweaks, single-property additions). Produces a dated `quickfix-{timestamp}.md` with `ADDED/MODIFIED/REMOVED` requirement and test deltas against existing specs, then implements the delta in one shot with inline review.

| Document | Content |
|----------|---------|
| `.sdlc/specs/{feature}/quickfix-{timestamp}.md` | Delta record (ADDED/MODIFIED/REMOVED requirements + tests) |

```
/sdlc-quickfix user-authentication
# Describe the change in one sentence. Approve the delta. Done.
```

Use this for the "change button from blue to green" class of work that the full pipeline would otherwise turn into a multi-story spec.

### 8. `sdlc-document` — Reverse-Engineer Specs From Code

Closes the drift loop the other way: reads existing source + tests and produces (or regenerates) `spec.md` to match what the code actually does. Works with or without prior SDLC setup — handles codebases that have no `.sdlc/` directory and detects old-format specs (`requirements.md` + `design.md`) for migration. Produces a `drift-report-{timestamp}.md` when prior specs existed.

| Document | Content |
|----------|---------|
| `.sdlc/specs/{feature}/spec.md` | Reverse-engineered spec (EARS requirements + design) |
| `.sdlc/specs/{feature}/drift-report-{timestamp}.md` | UNCHANGED / MODIFIED / ADDED / REMOVED-from-code diff (only if prior specs existed) |

```
/sdlc-document src/auth/
```

Use for brownfield onboarding or after `sdlc-review` flags drift.

---

## Traceability

Source files generated by `sdlc-implement` (and modifications by `sdlc-quickfix`) carry traceability tags so the spec → code link survives refactors.

**Source file header** (lists every REQ-* and NFR-* satisfied by the file):
```python
# GENERATED FROM SPEC: .sdlc/specs/user-authentication/spec.md
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

NFRs that are validated **outside code** (e.g. WAF rules, SLO dashboards, infra modules) are NOT given fake `IMPLEMENTS:` lines — they're listed under the "NFRs Validated Outside Code" section of `.sdlc/specs/{feature}/spec.md` with the validation mechanism named.

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

Artifacts on disk (`.sdlc/`, `src/`, `tests/`) are the durable state. Conversation history is auxiliary.

> If your runtime offers a conversation-persistence command (e.g. zrb's `/save` and `/load`), use it freely between phases — the skills don't depend on it.

---

## Generated Project Structure

After running the full pipeline, the project has this deterministic layout (the only variable is `{feature}`):

```
<project-root>/
├── .sdlc/                             # ALL SDLC artifacts live here
│   ├── rules.md                       #   Project invariants (sdlc-init)
│   ├── docs/                          #   Steering documents
│   │   ├── product.md                 #     Problem, users, success criteria
│   │   ├── tech.md                    #     Languages, frameworks, DB, infra
│   │   ├── test-strategy.md           #     Testing levels, CI gates
│   │   ├── architecture.md            #     C4 model (sdlc-architect)
│   │   └── adr/                       #     Architecture Decision Records
│   │       ├── ADR-001-database-choice.md
│   │       └── ...
│   ├── requirements/                  #   Requirements (sdlc-requirements)
│   │   ├── problem-brief.md           #     PRD with US-* stories and AC-* criteria
│   │   └── entity-dictionary.md       #     Entities, fields, types, constraints
│   ├── specs/                         #   Feature specs (sdlc-spec)
│   │   └── {feature}/                 #     One directory per feature
│   │       ├── spec.md                #       EARS requirements + design in one file
│   │       ├── quickfix-{ts}.md       #       (Optional) deltas from sdlc-quickfix
│   │       └── drift-report-{ts}.md   #       (Optional) drift diff from sdlc-document
│   ├── tests/                         #   Test plans (sdlc-spec)
│   │   └── {feature}/                 #     Test plan per feature
│   │       └── test-plan.md           #       Unit, integration, E2E, PBT tests
│   └── reviews/                       #   Review reports (sdlc-review)
│       └── {feature}/                 #     Feature-scoped
│           └── report-{ts}.md         #       Compliance + traceability verdict
├── src/                               # Source code (sdlc-implement)
├── tests/                             # Test code (sdlc-implement — real test files)
└── AGENTS.md                          # AI assistant guide (sdlc-init, at root)
```

All paths are hardcoded in the SKILL.md files. The only user choice is the `{feature}` name (or `{scope}` for `sdlc-document`) passed to the feature-level skills.

Each skill reads the artifacts it needs from these deterministic paths. For example, `/sdlc-spec` reads `.sdlc/rules.md`, `.sdlc/docs/product.md`, `.sdlc/requirements/entity-dictionary.md`, etc. before generating specs.

---

## Evals

`evals/` holds golden examples per skill — the foothold for measuring whether prompt changes improve or regress output quality. The runner is not implemented yet; the structure and authoring guide are in [`evals/README.md`](evals/README.md), with one case under `evals/golden/sdlc-init/personal-todo-app/` (input + rubric authored; expected outputs not yet committed). Contributions of additional cases are the cheapest way to harden the plugin.

---

## Key Design Limitations

- **No CLI commands** — `zrb sdlc init` does not exist. Only chat skills (`/sdlc-init`, etc.). The installer (`bin/install.sh --tools all`) is the only shell entry point.
- **No runtime approval enforcement** — `Write`/`Edit`/`Bash` are not gated by `ToolPolicy`. Approval relies on the LLM following instructions in the skill.
- **No validation tools** — no EARS syntax validator, no ADR compliance checker, no entity cross-reference tool. Traceability is enforced by `grep` patterns, not a real parser.
- **No hook integration** — no `SESSION_START`/`SESSION_END` hooks for automated phase validation.
- **No MCP server** — generic MCP-aware agents outside zrb/Claude Code can't consume these skills directly yet.
- **No eval runner** — `evals/` has structure and one case, but no automated grader. Today's evals are read by humans.
- **Specs still drift** — `sdlc-document` closes the loop manually, but there is no automated re-sync after every commit. This is a known limitation shared by every SDD tool in 2026.
