# SDLC AI Plugin

**Skills, not CLI commands.** This plugin provides 9 chat skills (`/sdlc-init`, `/sdlc-requirements`, etc.) that guide an LLM through Spec-Driven Development, plus a bundled deterministic validator and a rule-based eval runner.

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

The installer is portable bash (works on macOS's bash 3.2), supports all major AI coding assistants (zrb, Claude Code, Codex, OpenCode, Cursor, Windsurf, GitHub Copilot, Gemini CLI, Cline, and 20+ more), replaces any prior copy of each skill, and never touches non-`sdlc-*` skills in your target directories. The validator (`sdlc-validate.py`) is bundled inside the `sdlc-init` and `sdlc-migrate` skill directories and travels with them — see [Contributing](#contributing) for how those copies stay in sync with their single source under `scripts/`.

### Manual (if you prefer)

```bash
# zrb
mkdir -p ~/.zrb/skills && cp -R skills/sdlc-* ~/.zrb/skills/
# Claude Code
mkdir -p ~/.claude/skills && cp -R skills/sdlc-* ~/.claude/skills/
# Any other tool — same pattern: <dotdir>/skills/
```

All runtimes scan their skills directory on startup; skills become available as `/sdlc-init`, `/sdlc-requirements`, etc. Claude Code ignores the `disable-model-invocation`/`user-invocable` frontmatter (zrb-specific) but otherwise loads the skills as-is.

---

## Quick Start

In a chat session, activate a skill by name:

```
# Main pipeline (in order)
/sdlc-init                # 1. Steering docs + constitution + conventions + validator
/sdlc-requirements        # 2. PRD + entity dictionary
/sdlc-architect           # 3. ADRs + architecture
/sdlc-spec <feature>      # 4. Spec (canonical EARS, Feature Key) + test plan
/sdlc-implement <feature> # 5. Code + tests with KEY:REQ-* traceability tags
/sdlc-review <feature>    # 6. Validator + spec-compliance review

# Lightweight & maintenance skills (invoke as needed)
/sdlc-quickfix <feature>  # Delta-format path for bug fixes / small changes (promotes to spec by default)
/sdlc-document <scope>    # Reverse-engineer specs from existing code (drift recovery)
/sdlc-migrate             # Upgrade an old-layout project to the current .sdlc/ layout + conventions
```

`<feature>` is slugified into the directory name (`User Auth` → `.sdlc/specs/user-auth/`).

---

## Upgrading an Existing Project — `/sdlc-migrate`

Projects created with an earlier version of these skills keep artifacts at the repo root (`docs/`, `docs/adr/`, `requirements/`, `rules.md`) instead of under `.sdlc/`. The current skills expect the consolidated `.sdlc/` layout. If you run a skill on an old-layout project, it detects the legacy paths, reads them in place (no split-brain), and tells you to migrate.

`/sdlc-migrate` does the upgrade in one session, **preserving git history** (`git mv`):

- Moves steering docs, ADRs, requirements, specs, and reviews under `.sdlc/`.
- Installs `.sdlc/tools/sdlc-validate.py` and `.sdlc/CONVENTIONS.md`.
- Repoints cross-references in `AGENTS.md` and `README.md`.
- Detects content migrations it won't do blindly and routes them: old-format specs (`requirements.md` + `design.md` → `spec.md`) → `/sdlc-document`; deprecated EARS dialect → `/sdlc-document` or `/sdlc-quickfix`; unkeyed traceability tags → mechanical re-key.
- Runs the validator to confirm.

It is idempotent — safe to re-run; a project already on the current layout reports "nothing to migrate."

---

## How This Maps to Scrum

The SDLC phases are **artifact stages**, not time-boxed ceremonies. Rough mapping for teams coming from Scrum:

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
| `sdlc-migrate` | Tooling upgrade / repo housekeeping |

**Mental model:**
- Phases 1–3 run **once per project** (your "sprint zero").
- Phases 4–6 run **once per feature**, looped multiple times per sprint.
- `quickfix`, `document`, and `migrate` are **out-of-band lanes** for hotfixes, drift recovery, and upgrades.

**Where the analogy breaks:** the skills don't replace standups, retros, estimation, or timeboxing. SDD gives you the *artifacts*; Scrum gives you the *cadence*.

---

## Real-World Scenarios

### Scenario A: Greenfield Project

Each phase runs in its own fresh chat session — exit and start a new one between phases so context doesn't accumulate.

```
/sdlc-init                        # steering docs, rules, CONVENTIONS.md, validator
/sdlc-requirements                # problem brief (US/AC/NFR ids) + entity dictionary
/sdlc-architect                   # ADRs + architecture
/sdlc-spec user-authentication    # spec.md (Feature Key AUTH) + test-plan.md
/sdlc-implement user-authentication  # src/ + tests/ with AUTH:REQ-* tags; runs validator
/sdlc-review user-authentication  # validator + fresh-context review → APPROVE / REQUEST CHANGES / COMMENT
```

After auth is done, add the next feature starting from `/sdlc-spec todo-crud` — steering docs, requirements, and architecture already exist.

### Scenario B: Adding a Feature to an Existing Project

Steering docs, requirements, and architecture already exist (under `.sdlc/`). You only need phases 4–6: `/sdlc-spec <feature>` → `/sdlc-implement <feature>` → `/sdlc-review <feature>`.

**Multiple features in parallel**: run `/sdlc-spec payment-processing` and `/sdlc-spec notifications` in separate sessions — each writes to its own `.sdlc/specs/<slug>/`, and Feature Keys keep their `REQ-*` IDs from colliding even in shared source files. For parallel *implementation*, use git worktrees (see `sdlc-implement`).

### Scenario C: Bug Fix (Lightweight Path)

Not every change needs the full pipeline. For a small bug fix in an already-specified feature, use the delta path — **not** a new spec:

```
/sdlc-quickfix user-authentication
# Describe the change in one sentence. Approve the 1–3-requirement delta.
# Code + tests updated, validator run, delta promoted into spec.md by default.
```

This keeps the fix inside the feature's own spec instead of fragmenting it into a separate `fix-login-*` spec directory. Use `/sdlc-spec` only for genuinely new capabilities.

### Scenario D: Spec Drift After Code Changes

Specs are **snapshots, not living documents** — if code changes outside the pipeline, specs lag. To re-sync:

1. `/sdlc-document <feature>` reverse-engineers a current spec from code; if a prior spec exists it also writes a `drift-report-<ts>.md` (UNCHANGED / MODIFIED / ADDED / REMOVED-from-code).
2. Per finding, decide: absorb into the spec (keep `sdlc-document`'s output) or close the gap in code (`/sdlc-quickfix <feature>`).
3. `/sdlc-review <feature>` for a fresh compliance check once spec and code agree.

The `quickfix` promote-by-default behavior keeps everyday drift from accumulating in the first place.

### Scenario E: Brownfield With No SDLC Setup

```
/sdlc-document src/auth/   # zero-baseline run → writes .sdlc/specs/auth/spec.md from code, warns no entity dictionary
/sdlc-init                 # brownfield path: extracts what it can, interviews the rest
/sdlc-requirements         # extracts entities from code + the new spec
# Project is now bootstrapped; future features follow the normal pipeline.
```

### Scenario F: Old-Layout / Old-Format Project

Your project predates the `.sdlc/` consolidation (artifacts at `docs/`, `requirements/`) and/or the spec merge (`requirements.md` + `design.md` per feature). Run `/sdlc-migrate` first to consolidate paths and install tooling, then `/sdlc-document <feature>` to merge any old-format specs into `spec.md`. See [Upgrading an Existing Project](#upgrading-an-existing-project--sdlc-migrate).

---

## The Skills

### 1. `sdlc-init` — Kickoff + Constitution + Conventions

| Artifact | Content |
|----------|---------|
| `.sdlc/docs/product.md` | Problem, users, success criteria, scope, stakeholders |
| `.sdlc/docs/tech.md` | Languages, frameworks, DB, infra, principles, PBT tooling |
| `.sdlc/docs/test-strategy.md` | Testing levels, naming convention, CI gates, environments |
| `AGENTS.md` | AI assistant guide (repo root) |
| `.sdlc/rules.md` | `RULE-*` invariants + Override Log |
| `.sdlc/CONVENTIONS.md` | Paths, canonical EARS dialect, ID/traceability scheme, approval tiers |
| `.sdlc/tools/sdlc-validate.py` | Bundled deterministic validator |

### 2. `sdlc-requirements` — Requirements Elicitation

`problem-brief.md` (US-*/AC-*/NFR-* ids — the upstream source for spec NFRs) and `entity-dictionary.md`. Both are project-wide, single-file, and **merge** on re-run.

### 3. `sdlc-architect` — Architecture Decisions

`adr/ADR-*.md` (immutable; supersede, never overwrite) and `architecture.md`.

### 4. `sdlc-spec` — Feature Spec + Test Plan

`spec.md` (canonical EARS, declared `**Feature Key:**`, API surface, error handling, correctness) and `test-plan.md`. Feature directory is the slugified `<feature>` argument.

**Canonical EARS** (replaces the old homemade dialect):

| Pattern | Template |
|---------|----------|
| Ubiquitous | The `<system>` SHALL `<response>`. |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |

### 5. `sdlc-implement` — Code Generation

Single delegation to a coding agent. The agent reads spec artifacts **on demand from disk** (progressive disclosure); only `.sdlc/rules.md` is inlined verbatim. Emits key-namespaced traceability tags and runs the validator.

### 6. `sdlc-review` — Spec Compliance Review

Two layers: the **validator** handles traceability, EARS, and ID hygiene deterministically; a **fresh-context sub-agent** handles correctness, entity fidelity, ADR and rule compliance. Verdict mapping is deterministic (any validator ERROR / FAIL / unrecorded rule violation → REQUEST CHANGES). Reports at `.sdlc/reviews/<slug>/report-<ts>.md`.

### 7. `sdlc-quickfix` — Delta-Format Lightweight Path

`ADDED/MODIFIED/REMOVED` delta against an existing spec, implemented in one shot with inline review, **promoted into `spec.md` by default** so the canonical spec stays current.

### 8. `sdlc-document` — Reverse-Engineer Specs From Code

Spec-from-code for brownfield onboarding and drift recovery. Detects old-format specs (`requirements.md` + `design.md`) and offers format migration; writes a drift report when prior specs existed.

### 9. `sdlc-migrate` — Layout & Convention Upgrade

Consolidates legacy root-level artifacts under `.sdlc/`, installs the validator and conventions file, re-keys tags, and routes content migrations. History-preserving and idempotent. See [Upgrading an Existing Project](#upgrading-an-existing-project--sdlc-migrate).

---

## Traceability

Source and test files carry **key-namespaced** tags so IDs never collide across features and the spec → code link survives refactors. Each `spec.md` declares a globally-unique `**Feature Key:**` (e.g. `AUTH`); IDs are written `KEY:REQ-NNN`.

**Source file header:**
```python
# GENERATED FROM SPEC: .sdlc/specs/user-authentication/spec.md
# IMPLEMENTS: AUTH:REQ-001, AUTH:REQ-003, AUTH:NFR-002
```
**Test file header:**
```python
# COVERS: AUTH:REQ-002, AUTH:NFR-001, AUTH:UT-005, AUTH:IT-001
```
**Inline tag** on the unit that fulfils requirements:
```python
# @sdlc AUTH:REQ-003, AUTH:REQ-004
def validate_login(...): ...
```

NFRs validated **outside code** (WAF rules, SLO dashboards, infra) are listed under "NFRs Validated Outside Code" in `spec.md` — the validator exempts them rather than expecting a fake `IMPLEMENTS:` line.

The bundled validator enforces all of this deterministically:

```bash
python .sdlc/tools/sdlc-validate.py                 # whole project
python .sdlc/tools/sdlc-validate.py --feature user-authentication
python .sdlc/tools/sdlc-validate.py --strict --json # CI gate, machine-readable
```

It reports `ERROR` (missing IMPLEMENTS/COVERS for a REQ, dangling tags, duplicate/recycled IDs, key collisions), `WARNING` (unkeyed legacy tags, deprecated EARS dialect, test-plan gaps), and `INFO` (legacy layout, outside-code NFRs). Exit codes: `0` clean, `1` warnings (`--strict`), `2` errors. Wire it into CI via the gate row in `test-strategy.md`.

---

## Context Management

Each phase runs in a **fresh chat session** to prevent context accumulation: finish a phase and approve its artifacts → exit → start a new chat → run the next phase (it reads artifacts from disk, not chat history). Artifacts on disk (`.sdlc/`, `src/`, `tests/`) are the durable state.

> If your runtime offers conversation persistence (e.g. zrb's `/save` and `/load`), use it freely between phases — the skills don't depend on it.

---

## Approval Tiers

To avoid approval fatigue, writes are tiered (defined in `.sdlc/CONVENTIONS.md`):

- **Tier 1 — explicit per-item approval**: global / hard-to-reverse writes (rule modifications, ADR supersessions, entity-dictionary conflict resolutions, spec overwrites, file moves).
- **Tier 2 — one batched approval**: routine first-time generation (the four steering docs together; spec + test plan together).
- **Tier 3 — no approval**: read-only analysis, validator runs, review reports.

---

## Generated Project Structure

```
<project-root>/
├── .sdlc/
│   ├── rules.md                       # Project invariants (sdlc-init)
│   ├── CONVENTIONS.md                 # Paths, EARS dialect, ID scheme, approval tiers (sdlc-init)
│   ├── tools/
│   │   └── sdlc-validate.py           # Deterministic validator (sdlc-init / sdlc-migrate)
│   ├── docs/
│   │   ├── product.md  tech.md  test-strategy.md  architecture.md
│   │   └── adr/ADR-*.md
│   ├── requirements/
│   │   ├── problem-brief.md           # US-*/AC-*/NFR-* ids
│   │   └── entity-dictionary.md
│   ├── specs/<slug>/
│   │   ├── spec.md                    # Canonical EARS + design; declares Feature Key
│   │   ├── quickfix-<ts>.md           # (optional) deltas from sdlc-quickfix
│   │   └── drift-report-<ts>.md       # (optional) drift diff from sdlc-document
│   ├── tests/<slug>/test-plan.md
│   └── reviews/<slug>/report-<ts>.md
├── src/                               # Source code (key-namespaced traceability headers)
├── tests/                             # Test code
└── AGENTS.md                          # AI assistant guide (repo root)
```

The only variable is the `<slug>` (or `<scope>` for `sdlc-document`).

---

## Evals

`evals/` holds golden examples per skill plus a **rule-based runner** (`evals/run.py`) that grades deterministic `checks.json` assertions — runnable in CI with no LLM. Fuzzy rubric items stay human-graded; an LLM-as-judge extension is stubbed for later. Three cases ship today (`sdlc-init`, `sdlc-spec`, `sdlc-quickfix`); the authoring guide and `checks.json` schema are in [`evals/README.md`](evals/README.md). More cases are the cheapest way to harden the plugin.

```bash
python evals/run.py --list                  # list cases
python evals/run.py                          # lint case structure
python evals/run.py --actual /path/to/output # grade against produced output
```

---

## Runtime Compatibility

Skills are runtime-neutral: they describe **what** the LLM should do (read a file, delegate to a sub-agent, run a worktree), not **which tool** to use. The delegation blocks in `sdlc-implement`, `sdlc-review`, and `sdlc-quickfix` are **prompt templates** — they prefer progressive disclosure (pass file paths, let the sub-agent read on demand) and fall back to inlining for runtimes without file access. The validator and eval runner are stdlib-only Python 3.8+, so any environment with `python3` can run them.

---

## Contributing

A few files must live *inside* a skill directory (the installer copies skill dirs verbatim and never runs this repo's tooling), yet several skills need the *same* file. To avoid hand-maintained copies drifting, the canonical source lives once under `scripts/` and is synced into the skills that need it:

| Canonical source | Bundled into | How |
|------------------|--------------|-----|
| `scripts/sdlc-validate.py` | `skills/sdlc-init/`, `skills/sdlc-migrate/` | verbatim file copy |
| `scripts/templates/conventions.md` | `sdlc-init` & `sdlc-migrate` `SKILL.md` | spliced into the `<!-- SYNC:BEGIN conventions.md -->` region |

**Edit the source under `scripts/`, never the bundled copies.** Then resync:

```bash
python3 scripts/sync_skills.py          # regenerate bundled copies
python3 scripts/sync_skills.py --check  # CI/pre-push guard: exit 1 if drifted
```

For the [zrb](https://github.com/state-alchemists/zrb) runtime, `zrb_init.py` wires these into tasks — `zrb skill sync`, `zrb skill check`, `zrb skill test` — and chains `sync → check → test` so drifted copies can't ship. Adding another shared file is one entry in the `SCRIPT_COPIES` / `TEMPLATE_INJECTS` manifest in `scripts/sync_skills.py`.

---

## Key Design Notes & Limitations

**Now addressed:**
- **Traceability is validated, not just grepped** — `sdlc-validate.py` parses IDs and tags and fails on gaps; wire it into CI.
- **Canonical EARS** — the homemade `AS`/`ALWAYS`/state-`WHERE` dialect is replaced by standard EARS; the validator flags the old dialect with a migration hint.
- **IDs don't collide across features** — per-feature `REQ-*` are namespaced by a globally-unique Feature Key (`AUTH:REQ-003`).
- **Eval runner exists** — `evals/run.py` grades deterministic checks; ≥3 scenarios shipped.
- **Feature names are slugified** — no spaces or unsafe characters in directory names.
- **Migration is first-class** — `/sdlc-migrate` upgrades old-layout projects, history-preserving and idempotent.
- **Spec drift is reduced** — `quickfix` promotes to the canonical spec by default; `sdlc-document` closes the loop the other way.

**Still true:**
- **No CLI commands** — only chat skills + the bundled Python validator/eval runner. The installer is the only shell entry point for setup.
- **No runtime approval enforcement** — approval relies on the LLM following the tiered-approval instructions; `Write`/`Edit`/`Bash` are not gated by policy.
- **Validator is structural, not semantic** — it checks IDs, tags, and EARS keywords, not whether a requirement is *correctly* implemented (that's the review sub-agent's job, which remains LLM judgement).
- **LLM-as-judge evals are a stub** — today's `run.py` grades deterministic checks only.
- **Specs are snapshots** — re-sync is manual (`sdlc-document`); there is no automatic re-sync on every commit. Shared by every SDD tool.
```
