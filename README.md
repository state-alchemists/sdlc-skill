# SDLC AI Plugin

**Skills, not CLI commands.** Seven chat skills (`/sdlc-init`, `/sdlc-plan`, ...) that guide an LLM through Spec-Driven Development, plus a deterministic validator and a rule-based eval runner.

**Primary target: zrb.** Also runs under Claude Code and the ~30 other tools that load `SKILL.md` files — skills are runtime-neutral, so the LLM picks the right mechanism either way (see [Runtime Compatibility](#runtime-compatibility)).

Everything the skills generate comes from **templates installed into your project** at `.sdlc/templates/`. Edit those files and every later run follows your shape — no forking the plugin.

---

## Installation

```bash
bin/install.sh --tools all                    # install to all known AI coding tools
bin/install.sh --tools codex,opencode,gemini  # specific tools (comma-separated)
bin/install.sh                                # auto-detect — only tools already on this machine
bin/install.sh --dir .claude/skills           # a project-scoped directory, checked into the repo
bin/install.sh --uninstall --tools all        # remove sdlc-* skills from all targets
bin/install.sh --dry-run --tools cursor       # preview without changing anything
```

Portable bash (works on macOS's bash 3.2) and replaces any prior copy of each skill. It also removes this repo's skills from directories an earlier version installed to (`~/.opencode/skills`, `~/.github/skills`, `~/.cursor/skills`), so an upgrade leaves one copy rather than two — pass `--keep-legacy` to leave them alone. It only ever removes the skills this repo ships plus the ones it used to ship (`sdlc-requirements`, `sdlc-architect`, `sdlc-document`, `sdlc-migrate`) — your own skill in the same directory is left alone and reported as kept, whether it is called `my-skill` or `sdlc-deploy`.

### Upgrading from an earlier version

The installer works on the `sdlc-*` namespace in each target directory, so an upgrade removes skills that were merged away (`sdlc-requirements`, `sdlc-architect`, `sdlc-document`, `sdlc-migrate`) as well as refreshing the ones that remain. Non-`sdlc-*` skills are never touched.

```bash
git pull
bin/install.sh                 # same command as a fresh install
```

### Upgrading to the strict validator — read this before you upgrade CI

This release makes the traceability gate enforce what it always claimed. Three rules are new, and each of them **will fail builds that used to pass**:

| New rule | Typical failure | Fix |
|---|---|---|
| A tag must be inside a real comment | `trace-code` on a requirement whose tag was in a string literal or a `.txt` file | move the tag into a comment in the implementing file |
| `IMPLEMENTS:` only counts from a source file | `tag-role` + `trace-code` where a test file carried the header | move it to the source file |
| `COVERS:` only counts from a test file | `tag-role` + `trace-test` where a source file carried the header | write the test, or move the tag to it |

Every one of those errors names the file, the rule, and the fix, and says which `.sdlc/config.json` key relaxes it. If your project's test files are somewhere the built-in conventions do not recognise, declare it in `.sdlc/config.json` (`layout.test_directory_names`, `layout.test_stem_patterns`, `layout.test_overrides`) rather than re-tagging.

A project with no test files will now fail, which is the point: it used to pass.

**The ramp, if you cannot fix it all at once.** `--relax-tag-roles` (or `"gate": {"enforce_tag_roles": false}` in `.sdlc/config.json`) restores the old leniency for the role rule only: a tag counts wherever it sits, and a misplaced one is a WARNING that still names the file to move it to. The comment rule stays on, so a string literal never counts again. Every run then reports `gate-relaxed` as a WARNING — visible in the report, and non-zero under `--strict` — so the ramp cannot quietly become the setting.

```bash
python3 .sdlc/tools/sdlc-validate.py --relax-tag-roles   # green build, full worklist
```

Then, **per project** that was set up by an older version — always `/sdlc-init` first, then `/sdlc-adopt`:

```
/sdlc-init     # refreshes the validator, installs .sdlc/templates/, keeps your documents
/sdlc-adopt    # folds .sdlc/tests/<slug>/test-plan.md into each spec.md, re-keys tags
```

`/sdlc-init` never overwrites a template you have edited, always refreshes `.sdlc/tools/sdlc-validate.py` (an old copy carries fixed bugs), and shows a diff before replacing `.sdlc/CONVENTIONS.md`.

**The order is always `/sdlc-init` → `/sdlc-adopt`**, on every kind of project. `/sdlc-adopt` fills a structure rather than creating one, so it needs the templates and validator that `/sdlc-init` installs. On a project still using the legacy layout, `/sdlc-init` installs that scaffolding and stops there — it writes no steering documents, because those would form a parallel tree beside your existing ones — and routes you to `/sdlc-adopt`. Re-run `/sdlc-init` afterwards to fill the gaps.

Manual install is the same pattern for any tool — copy the skill directories into `<dotdir>/skills/`:

```bash
mkdir -p ~/.zrb/skills && cp -R skills/sdlc-* ~/.zrb/skills/       # zrb
mkdir -p ~/.claude/skills && cp -R skills/sdlc-* ~/.claude/skills/ # Claude Code
```

Copy the directories whole — `skills/sdlc-init/assets/` carries the templates, conventions, and validator that `/sdlc-init` installs into your project.

---

## Quick Start

```
# Once per project
/sdlc-init                 # 1. scaffolding (templates, conventions, validator) + steering docs + rules
/sdlc-plan                 # 2. problem brief + entity dictionary + ADRs + architecture

# Once per feature
/sdlc-spec <feature>       # 3. spec.md — EARS requirements, design, and test plan in one file
/sdlc-implement <feature>  # 4. code + tests with KEY:REQ-* traceability tags
/sdlc-review <feature>     # 5. validator + fresh-context spec-compliance review

# As needed
/sdlc-quickfix <feature>   # delta path for bug fixes and small changes (promotes into the spec)
/sdlc-adopt                # brownfield: migrate legacy layout, reverse-engineer specs from code
```

`<feature>` is slugified into the directory name (`User Auth` → `.sdlc/specs/user-auth/`).

---

## The Skills

### 1. `sdlc-init` — Scaffolding + Steering Docs + Constitution

Installs `.sdlc/templates/`, `.sdlc/CONVENTIONS.md`, and `.sdlc/tools/sdlc-validate.py` (never overwriting a file you have edited), then writes:

| Artifact | Content |
|----------|---------|
| `.sdlc/docs/product.md` | Problem, users, success criteria, scope, stakeholders |
| `.sdlc/docs/tech.md` | Languages, frameworks, DB, infra, principles, property-testing tooling |
| `.sdlc/docs/test-strategy.md` | Testing levels, naming convention, CI gates, environments |
| `AGENTS.md` | AI assistant guide (repo root) |
| `.sdlc/rules.md` | `RULE-*` invariants + Override Log |

Greenfield projects get interviewed; brownfield projects get a draft derived from manifests, README, CI config, and source layout, then confirmed.

### 2. `sdlc-plan` — Requirements + Architecture

`problem-brief.md` (`US-*`/`AC-*`/`NFR-*` — the upstream source every spec cites), `entity-dictionary.md`, `adr/ADR-*.md` (immutable; supersede, never overwrite), and `architecture.md`. All merge on re-run rather than overwrite.

### 3. `sdlc-spec` — Feature Spec

**One file per feature**: `.sdlc/specs/<slug>/spec.md` — canonical EARS requirements, a declared `**Feature Key:**`, API surface, error handling, correctness properties, entities, and the test plan.

| Pattern | Template |
|---------|----------|
| Ubiquitous | The `<system>` SHALL `<response>`. |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |

EARS keywords are uppercase — that is what makes them keywords, and the validator only treats uppercase occurrences as such.

### 4. `sdlc-implement` — Code Generation

Single delegation to a coding agent that reads spec artifacts **on demand from disk** (progressive disclosure); only `.sdlc/rules.md` is inlined verbatim. Emits key-namespaced traceability tags, then verifies tests, lint, and the validator with a hard retry cap.

### 5. `sdlc-review` — Spec Compliance Review

Two layers: the **validator** covers traceability, EARS, and ID hygiene deterministically; a **fresh-context sub-agent** covers correctness, entity fidelity, ADR and rule compliance. Verdict mapping is deterministic — any validator ERROR, FAIL, or unrecorded rule violation means REQUEST CHANGES. Reports at `.sdlc/reviews/<slug>/report-<ts>.md`.

### 6. `sdlc-quickfix` — Delta Path

`ADDED/MODIFIED/REMOVED` delta against an existing spec, implemented in one shot with an inline review, then **promoted into `spec.md`** so the spec never drifts behind the code. Promotion is the recommendation, not a default that happens on silence — editing an existing spec is Tier-1 and it asks. Use this skill instead of fragmenting a one-line fix into a new spec directory.

### 7. `sdlc-adopt` — Brownfield Adoption

Two modes, and it decides which your project needs:
- **Layout migration** — relocate legacy artifacts under `.sdlc/` with `git mv`, fold separate `test-plan.md` files into their specs, re-key unkeyed traceability tags. Idempotent.
- **Document from code** — reverse-engineer a spec for code that has none, or that has drifted, with a drift report (`UNCHANGED` / `MODIFIED` / `ADDED` / `REMOVED-from-code`).

---

## Templates

`/sdlc-init` installs one template per document into `.sdlc/templates/`. Skills read them at generation time, so editing a template changes what every later run produces — and an edited template is never overwritten by a re-run.

| Template | Produces |
|----------|----------|
| `product.md`, `tech.md`, `test-strategy.md`, `agents.md`, `rules.md` | `/sdlc-init` output |
| `problem-brief.md`, `entity-dictionary.md`, `adr.md`, `architecture.md` | `/sdlc-plan` output |
| `spec.md` | `/sdlc-spec` and `/sdlc-adopt` output |
| `quickfix.md`, `review-report.md`, `drift-report.md` | `/sdlc-quickfix`, `/sdlc-review`, `/sdlc-adopt` output |

---

## Real-World Scenarios

Each phase runs in its own fresh chat session — exit and start a new one between phases so context doesn't accumulate.

### A: Greenfield

```
/sdlc-init
/sdlc-plan
/sdlc-spec user-authentication       # spec.md, Feature Key AUTH
/sdlc-implement user-authentication  # src/ + tests/ with AUTH:REQ-* tags
/sdlc-review user-authentication     # APPROVE / REQUEST CHANGES / COMMENT
```

The next feature starts at `/sdlc-spec todo-crud` — steering docs, requirements, and architecture already exist.

### B: Adding a Feature

Only `/sdlc-spec` → `/sdlc-implement` → `/sdlc-review`. Run several features in parallel sessions: each writes to its own `.sdlc/specs/<slug>/`, and Feature Keys keep `REQ-*` IDs from colliding even in shared source files. For parallel *implementation*, use git worktrees.

### C: Bug Fix

```
/sdlc-quickfix user-authentication
```
Describe the change in one sentence, approve a 1–3 requirement delta; code, tests, and the spec are updated together.

### D: Spec Drift

Specs are snapshots. When code changes outside the pipeline: `/sdlc-adopt` (document mode) reverse-engineers the current behaviour and writes a drift report; decide per finding whether to absorb it into the spec or close the gap in code with `/sdlc-quickfix`; then `/sdlc-review`.

### E: Brownfield With No SDLC Setup

```
/sdlc-init         # brownfield path: scaffolding, then extracts what it can and interviews the rest
/sdlc-adopt        # document mode on src/auth/ — writes a spec from code
/sdlc-plan         # entities extracted from code and the new spec
```

`/sdlc-init` comes first everywhere: `/sdlc-adopt` generates from `.sdlc/templates/`, which `/sdlc-init` installs.

### F: Project From an Earlier Version of These Skills

`/sdlc-init` refreshes the validator and installs the templates without touching your documents — on a legacy layout it stops right there. Then `/sdlc-adopt` consolidates legacy paths under `.sdlc/`, folds `test-plan.md` into `spec.md`, and re-keys tags, preserving git history. Re-run `/sdlc-init` to fill any remaining gaps.

---

## How This Maps to Scrum

The SDLC phases are **artifact stages**, not time-boxed ceremonies.

| SDLC phase | Scrum parallel |
|---|---|
| `sdlc-init` | Sprint Zero — vision, tech stack, Definition of Done (invariants) |
| `sdlc-plan` | Backlog creation + architecture spike |
| `sdlc-spec` | Backlog refinement + test-case design — moving a story to "Ready" |
| `sdlc-implement` | Sprint development work |
| `sdlc-review` | Code review + Definition of Done check |
| `sdlc-quickfix` | Hotfix / unplanned work lane |
| `sdlc-adopt` | Discovery / tech-debt onboarding |

Phases 1–2 run once per project; 3–5 loop per feature. **Where the analogy breaks:** the skills give you *artifacts*, not *cadence* — standups, retros, estimation, and timeboxing are still yours.

---

## Traceability

Each `spec.md` declares a globally-unique `**Feature Key:**` (e.g. `AUTH`), and IDs are written `KEY:REQ-NNN` so they never collide across features.

```python
# SPEC: .sdlc/specs/user-authentication/spec.md
# IMPLEMENTS: AUTH:REQ-001, AUTH:REQ-003, AUTH:NFR-002
```
```python
# COVERS: AUTH:REQ-002, AUTH:NFR-001, AUTH:UT-005, AUTH:IT-001
```
```python
# @sdlc AUTH:REQ-003, AUTH:REQ-004
def validate_login(...): ...
```

NFRs validated **outside code** (WAF rules, SLO dashboards, infra) are listed under "NFRs Validated Outside Code" in the spec; the validator exempts them rather than expecting a fake `IMPLEMENTS:` line. That heading is the only thing that exempts an NFR — what the "Validated By" cell *says* exempts nothing, and neither does naming CI, because CI is where validation runs, not what performs it.

A requirement's `(AC-NNN)` citation is checked against `problem-brief.md` when one exists, so an AC renumbered upstream surfaces as an error instead of rotting. Unkeyed legacy tags (`@sdlc REQ-003`) warn **and** leave their requirement untraced — they do not satisfy coverage until re-keyed.

```bash
python3 .sdlc/tools/sdlc-validate.py                 # whole project
python3 .sdlc/tools/sdlc-validate.py --feature user-authentication
python3 .sdlc/tools/sdlc-validate.py --strict --json # CI gate, machine-readable
python3 .sdlc/tools/sdlc-validate.py --exclude 'docs/*.md'
```

`ERROR` (missing `IMPLEMENTS`/`COVERS`, a tag in the wrong kind of file, dangling tags, duplicate or recycled IDs, key collisions, unknown `AC-*` citations, a test-plan row pointing at a retired requirement, an unusable Feature Key, an unknown `--feature` slug, an unusable `.sdlc/config.json`), `WARNING` (unkeyed legacy tags, EARS problems, test-plan gaps in either direction, a file skipped while scanning), `INFO` (legacy layout, outside-code NFRs). Exit `0` clean, `1` warnings with `--strict`, `2` errors.

### What counts as a tag

A tag counts only when all three hold. This is what makes the gate real rather than a string search:

1. **It sits in a real comment** — not a string literal, not prose, not a `.txt` file. A header tag must also *open* its comment, so `# This file does NOT IMPLEMENTS: X` is a remark about the format, not a claim.
2. **It is in the right kind of file** — `IMPLEMENTS:` from a source file, `COVERS:` from a test file. One file carrying both satisfies neither.
3. **The file is code** — documentation (`.md`, `.rst`, `.adoc`) is never scanned, so a README can show the format freely.

Source and test are decided by path components and filename stems, never substrings: `tests/`, `test_*.py`, `*_test.go`, `src/test/java/`, `*.spec.ts`, `__tests__/`, `*Tests.cs` and so on. Go, Maven, Jest, RSpec, .NET and monorepo layouts all work as shipped; anything unusual goes in `.sdlc/config.json`. `src/contest/models.py` stays source.

`--feature` narrows the **findings**, not the parse: every spec is still read, so other features' tags resolve instead of reporting as dangling. Fenced code blocks in Markdown are never read as tags, so a README can document the tag format freely; `--exclude GLOB` covers anything outside a fence.

---

## Approval Tiers

Writes are tiered to avoid approval fatigue (defined in `.sdlc/CONVENTIONS.md`):

- **Tier 1 — per-item approval**: rule modifications, ADR supersessions, entity conflicts, spec overwrites, file moves.
- **Tier 2 — one batched approval**: routine first-time generation.
- **Tier 3 — none**: read-only analysis, validator runs, review reports.

---

## Generated Project Structure

```
<project-root>/
├── .sdlc/
│   ├── CONVENTIONS.md                 # Paths, EARS dialect, ID scheme, file roles, approval tiers
│   ├── ANNOTATION.md                  # Comment syntax and header placement per language
│   ├── config.json                    # Source/test layout, comment styles, scan overrides
│   ├── keys/<KEY>                     # Feature Key claims (parallel-session safety)
│   ├── rules.md                       # Project invariants
│   ├── templates/*.md                 # Project-owned templates every skill generates from
│   ├── tools/sdlc-validate.py         # Deterministic validator
│   ├── docs/
│   │   ├── product.md  tech.md  test-strategy.md  architecture.md
│   │   └── adr/ADR-*.md
│   ├── requirements/
│   │   ├── problem-brief.md           # US-*/AC-*/NFR-* ids
│   │   └── entity-dictionary.md
│   ├── specs/<slug>/
│   │   ├── spec.md                    # EARS requirements + design + test plan
│   │   ├── quickfix-<ts>.md           # (optional) deltas
│   │   └── drift-report-<ts>.md       # (optional) drift diff
│   └── reviews/<slug>/report-<ts>.md
├── src/                               # Source code (key-namespaced traceability headers)
├── tests/                             # Test code
└── AGENTS.md                          # AI assistant guide (repo root)
```

---

## Context Management

Each phase runs in a **fresh chat session**: finish a phase, approve its artifacts, exit, start a new chat, run the next phase — it reads artifacts from disk, not chat history. Artifacts (`.sdlc/`, `src/`, `tests/`) are the durable state.

> If your runtime offers conversation persistence (zrb's `/save` and `/load`), use it freely between phases — the skills don't depend on it.

---

## Evals

`evals/` holds golden examples per skill plus a **rule-based runner** that grades deterministic `checks.json` assertions — runnable in CI with no LLM. Fuzzy rubric items stay human-graded.

```bash
python3 evals/run.py --list                  # list cases
python3 evals/run.py                         # lint case structure
python3 evals/run.py --actual /path/to/output # grade against produced output
```

Three cases ship today (`sdlc-init`, `sdlc-spec`, `sdlc-quickfix`); the authoring guide and schema are in [`evals/README.md`](evals/README.md). More cases are the cheapest way to harden the plugin.

---

## Runtime Compatibility

Skills are runtime-neutral: they describe **what** the LLM should do (read a file, delegate to a sub-agent, use a worktree), not **which tool** to use. The delegation blocks in `sdlc-implement`, `sdlc-review`, and `sdlc-quickfix` are prompt templates — they prefer progressive disclosure and fall back to inlining for runtimes without file access. The validator and eval runner are stdlib-only Python 3.8+.

**Skills directories.** Anthropic published Agent Skills as an open spec in December 2025, and `~/.<tool>/skills/<name>/SKILL.md` is the convention it established. These were checked against each tool's own documentation:

| Tool | Personal skills directory |
|------|---------------------------|
| Claude Code | `~/.claude/skills/` |
| zrb | `~/.zrb/skills/` |
| OpenAI Codex CLI | `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| GitHub Copilot | `~/.copilot/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| *(vendor-neutral)* | `~/.agents/skills/` — read by Copilot, OpenCode and others |

The remaining IDs follow the same convention and are inherited from OpenSpec's supported-tools table; they are installed to but not individually confirmed here.

**Cursor is project-scoped only** — it reads `.cursor/skills/` inside a repository and has no `$HOME` location, so it has no tool ID. Install to it with `bin/install.sh --dir .cursor/skills`.

Claude Code ignores the `disable-model-invocation` / `user-invocable` frontmatter (zrb-specific) but otherwise loads the skills as-is.

---

## Contributing

The repository has one copy of everything:

| File | Role |
|------|------|
| `skills/<name>/SKILL.md` | The skill itself — workflow only, no embedded templates |
| `skills/sdlc-init/assets/templates/*.md` | Canonical templates, installed into `.sdlc/templates/` |
| `skills/sdlc-init/assets/CONVENTIONS.md` | Canonical conventions, installed into `.sdlc/` |
| `skills/sdlc-init/assets/ANNOTATION.md` | Per-language comment syntax and header placement |
| `skills/sdlc-init/assets/config.json` | Default project config, installed into `.sdlc/` |
| `skills/sdlc-init/assets/tools/sdlc-validate.py` | Canonical validator, installed into `.sdlc/tools/` |
| `evals/run.py` | Eval runner |
| `tests/test_sdlc_validate.py` | Validator regression tests — one case per bug it has shipped |
| `tests/test_skill_prompts.py` | Static invariants over the prompts — one case per prompt bug it has shipped |

Only `sdlc-init` carries assets, so there are no bundled copies to keep in sync — edit the file and you are done. `/sdlc-adopt` deliberately does not install tooling; it routes the user to `/sdlc-init` instead.

Scripts follow [kettanaito/naming-cheatsheet](https://github.com/kettanaito/naming-cheatsheet): snake_case throughout, no contractions, `get_`/`is_`/`has_` prefixes, plurals for collections, and functions ordered caller-before-callee so a file reads top-down.

Every change is checked by `.github/workflows/ci.yml` — compile, validator regression tests, eval-case lint, installer dry-run — on Python 3.8, the floor the validator promises. Run the same locally:

```bash
python3 tests/test_sdlc_validate.py   # validator regression tests
python3 tests/test_skill_prompts.py   # static invariants over the skill prompts
python3 evals/run.py                  # lint the eval cases
```

A change to the validator's parsing or check logic needs a case in `tests/test_sdlc_validate.py`. Verify a new case can actually fail: reintroduce the bug, confirm the case goes red, then restore.

For [zrb](https://github.com/state-alchemists/zrb), `zrb_init.py` exposes `zrb skill test` (all of the above) and `zrb skill install`.

---

## Key Design Notes & Limitations

**Addressed:**
- **Traceability is validated, not grepped** — the validator parses IDs and tags and fails on gaps; wire it into CI (`/sdlc-init` offers the snippet). Both ends are checked: `REQ-* → code` downstream, and `REQ-* → AC-*` against the problem brief upstream.
- **Canonical EARS** — standard EARS (Mavin et al.), uppercase keywords, with migration hints for the old homemade dialect.
- **IDs don't collide across features** — per-feature IDs namespaced by a globally-unique Feature Key.
- **Templates are project-owned** — edit `.sdlc/templates/`; re-running a skill never clobbers your edits.
- **One file per feature** — requirements, design, and test plan live together in `spec.md`.
- **Migration is first-class** — `/sdlc-adopt` upgrades old-layout projects, history-preserving and idempotent.
- **The validator is tested** — `tests/test_sdlc_validate.py` pins every bug it has shipped, and CI runs it on every push.
- **Drift is reduced** — `quickfix` promotes into the spec on approval, every time, rather than leaving deltas to pile up; `/sdlc-adopt` closes the loop the other way.

**Still true:**
- **No CLI commands** — chat skills plus the bundled Python validator and eval runner. The installer is the only shell entry point.
- **No runtime approval enforcement** — approval relies on the LLM following the tiered instructions; `Write`/`Edit`/`Bash` are not policy-gated.
- **The validator is structural, not semantic** — it checks IDs, tags, and EARS shape, not whether a requirement is *correctly* implemented. That is the review sub-agent's job.
- **The validator never runs your tests** — a `COVERS:` tag on a skipped or empty test satisfies coverage. It checks that a test *exists and claims the requirement*, not that it asserts anything.
- **A tag on commented-out code is indistinguishable from a tag on live code** — delete the tag when you delete the implementation.
- **Tags are unversioned** — reword a requirement and every tag pointing at it still validates. Drift of that kind is caught by `/sdlc-adopt`'s drift report, per feature and on demand, not per link and automatically.
- **Evals grade deterministic checks only** — no LLM-as-judge, and grading still needs a human to produce the `--actual` output. Only the validator tests and case linting run unattended.
- **Specs are snapshots** — re-sync is manual. Shared by every SDD tool.
