# SDLC AI Plugin

**Skills, not CLI commands.** Seven chat skills (`/sdlc-init`, `/sdlc-plan`, ...) guide an LLM through Spec-Driven Development, plus a deterministic validator and a rule-based eval runner.

**Primary target: zrb.** Also runs under Claude Code and the ~30 other tools that load `SKILL.md` files — skills are runtime-neutral (see [Runtime Compatibility](#runtime-compatibility)).

Everything the skills generate comes from **templates installed into your project** at `.sdlc/templates/`. Edit those files and every later run follows your shape — no forking the plugin.

---

## Install

```bash
bin/install.sh --tools all                    # install to all known AI coding tools
bin/install.sh --tools codex,opencode,gemini  # specific tools (comma-separated)
bin/install.sh                                # auto-detect — only tools already here
bin/install.sh --dir .claude/skills           # project-scoped, checked into the repo
bin/install.sh --uninstall --tools all        # remove sdlc-* skills from all targets
bin/install.sh --dry-run --tools cursor       # preview without changing anything
```

Portable bash (macOS 3.2 included). It replaces prior copies of each skill and sweeps directories an earlier version installed to, so an upgrade leaves one copy per target rather than two (`--keep-legacy` opts out). It only ever removes the skills this repo ships or used to ship (`sdlc-requirements`, `sdlc-architect`, `sdlc-document`, `sdlc-migrate`) — your own skills are left alone.

No matching flag for your tool? Copy the `sdlc-*` directories whole into `<dotdir>/skills/`:

```bash
mkdir -p ~/.claude/skills && cp -R skills/sdlc-* ~/.claude/skills/
```

`skills/sdlc-init/assets/` carries the templates, conventions, and validator the skills install into a project.

**Upgrade:** `git pull && bin/install.sh`. On a project set up by an older version, run `/sdlc-init` (refreshes the validator, keeps your documents) then `/sdlc-adopt` (relocates legacy artifacts and completes setup). Newer validator releases enforce rules older ones only claimed — see the [CHANGELOG](CHANGELOG.md) before upgrading CI.

---

## Quick Start

```
# Once per project
/sdlc-init                 # 1. scaffolding + steering docs + rules
/sdlc-plan                 # 2. problem brief + entity dictionary + ADRs + architecture

# Once per feature
/sdlc-spec <feature>       # 3. spec.md — EARS requirements + design + test plan
/sdlc-implement <feature>  # 4. code + tests with KEY:REQ-* traceability tags
/sdlc-review <feature>     # 5. validator + fresh-context compliance review

# As needed
/sdlc-quickfix <feature>   # delta path for bug fixes (promotes into the spec)
/sdlc-adopt                # brownfield: migrate + reverse-engineer specs
```

`<feature>` is slugified into the directory name (`User Auth` → `.sdlc/specs/user-auth/`).

---

## The Skills

| Skill | What it does |
|-------|--------------|
| `/sdlc-init` | Installs `.sdlc/` scaffolding (templates, `CONVENTIONS.md`, validator), then writes `product.md`, `tech.md`, `test-strategy.md`, `AGENTS.md`, and `rules.md`. Greenfield projects get interviewed; brownfield get a derived draft to confirm. |
| `/sdlc-plan` | Produces `problem-brief.md` (the `US-*`/`AC-*`/`NFR-*` source every spec cites), `entity-dictionary.md`, `adr/ADR-*.md`, and `architecture.md`. Merges on re-run; never overwrites. |
| `/sdlc-spec` | One `spec.md` per feature: canonical EARS requirements, a declared `**Feature Key:**`, API surface, error handling, correctness properties, entities, and the test plan. |
| `/sdlc-implement` | Delegates the whole feature to one coding agent that reads the spec from disk; emits key-namespaced traceability tags; verifies tests, lint, and the validator (retry cap 2). |
| `/sdlc-review` | Two layers: the deterministic validator, then a fresh-context review sub-agent for what a parser can't judge. Verdicts (APPROVE / REQUEST CHANGES / COMMENT) are mapped by rule, not opinion. |
| `/sdlc-quickfix` | An `ADDED/MODIFIED/REMOVED` delta against an existing spec, implemented in one shot with an inline review, then promoted into `spec.md` so the spec never drifts behind the code. |
| `/sdlc-adopt` | Brownfield onboarding: relocate legacy artifacts under `.sdlc/` with git history preserved, reverse-engineer specs from code, annotate source with tags, then complete the setup. |

The fine print — EARS dialect, ID scheme, file roles, approval tiers, single-writer files — lives in `.sdlc/CONVENTIONS.md`. Read that when a skill mentions it; this table is just the map.

---

## Templates

`/sdlc-init` installs one template per document into `.sdlc/templates/`. Skills generate from them at run time, so editing a template changes what every later run produces — and an edited template is never overwritten by a re-run.

| Template | Produces |
|----------|----------|
| `product.md`, `tech.md`, `test-strategy.md`, `agents.md`, `rules.md` | `/sdlc-init` output |
| `problem-brief.md`, `entity-dictionary.md`, `adr.md`, `architecture.md` | `/sdlc-plan` output |
| `spec.md` | `/sdlc-spec` and `/sdlc-adopt` output |
| `quickfix.md`, `review-report.md`, `drift-report.md` | `/sdlc-quickfix`, `/sdlc-review`, `/sdlc-adopt` output |

---

## Real-World Flows

Phases are stateless — artifacts on disk are the durable state, not chat history — so a **fresh session is a hygiene preference, not a rule**, except where independence is the point. Only `/sdlc-review` requires one: run in the session that implemented the feature, its verdict is capped at COMMENT (see `.sdlc/CONVENTIONS.md` § Review independence). `/sdlc-spec` → `/sdlc-implement` can share a session — the implementer reads `spec.md` from disk.

- **Greenfield:** `/sdlc-init` → `/sdlc-plan` → `/sdlc-spec feature` → `/sdlc-implement feature` → `/sdlc-review feature`. The next feature starts at `/sdlc-spec` — steering docs, requirements, and architecture already exist.
- **Adding a feature:** only `/sdlc-spec` → `/sdlc-implement` → `/sdlc-review`. Features can run in parallel: each writes its own `.sdlc/specs/<slug>/`, and Feature Keys keep `REQ-*` IDs from colliding even in shared files. Use git worktrees for parallel *implementation*.
- **Bug fix:** `/sdlc-quickfix feature` — describe the change in one sentence, approve a 1–3 requirement delta; code, tests, and the spec update together.
- **Spec drift:** specs are snapshots. When code changes outside the pipeline, `/sdlc-adopt` (document mode) reverse-engineers current behaviour into a drift report; absorb each finding into the spec or close the gap in code; then `/sdlc-review`.
- **Brownfield with no SDLC setup:** `/sdlc-init` (brownfield path) → `/sdlc-adopt` (document a subsystem from code) → `/sdlc-plan` (entities from code and the new spec). `/sdlc-init` always comes first — `/sdlc-adopt` generates from the templates it installs.
- **Upgrading an older project:** the trigger is where the artifacts are, not how old the project is. Files already under `.sdlc/` need only `/sdlc-init` (fills a missing `rules.md` or steering doc). A legacy layout (`docs/adr/`, root `rules.md`, `specs/`) needs `/sdlc-init` → `/sdlc-adopt`, and `/sdlc-adopt` is the last command of that journey.

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

Phases 1–2 run once per project; 3–5 loop per feature. The skills give you *artifacts*, not a cadence — standups, retros, estimation, and timeboxing stay yours.

---

## Traceability

Every `spec.md` declares a globally-unique `**Feature Key:**` (e.g. `AUTH`), and IDs are written `KEY:REQ-NNN` so they never collide across features.

```python
# SPEC: .sdlc/specs/user-authentication/spec.md
# IMPLEMENTS: AUTH:REQ-001, AUTH:REQ-003, AUTH:NFR-002     # source files
# COVERS: AUTH:REQ-002, AUTH:NFR-001, AUTH:UT-005          # test files
# @sdlc AUTH:REQ-003, AUTH:REQ-004                          # above a function
```

`python3 .sdlc/tools/sdlc-validate.py` parses these back and fails the build when the chain breaks: a requirement with no implementation, a tag pointing at nothing, an ID recycled, or a duplicate key. Both ends are checked — `REQ-* → code/tests` downstream, and each requirement's `(AC-NNN)` citation against `problem-brief.md` upstream, so an AC renumbered in the brief surfaces as an error instead of rotting.

**What counts as a tag** — all three must hold:

1. It sits in a **real comment** — not a string literal, not prose, not a `.txt` file. A header must *open* its comment, so `# This file does NOT IMPLEMENTS: X` is a remark about the format, not a claim.
2. It is in the **right kind of file** — `IMPLEMENTS:` from source, `COVERS:` from a test. One file carrying both satisfies neither.
3. The file is **code** — documentation (`.md`, `.rst`, `.adoc`) is never scanned.

Source and test are decided by path components and filename stems, never substrings (`tests/`, `test_*.py`, `*_test.go`, `src/test/java/`, `*.spec.ts`, `__tests__/`, `*Tests.cs`). Go, Maven, Jest, RSpec, .NET and monorepo layouts work as shipped; anything unusual goes in `.sdlc/config.json`. Exemption headings in the spec cover NFRs validated by infra and functional requirements no executable check can reach — and only those headings exempt, never what a "Validated By" cell says. Legacy unkeyed tags (`@sdlc REQ-003`) warn and do not count until re-keyed.

```bash
python3 .sdlc/tools/sdlc-validate.py                 # whole project
python3 .sdlc/tools/sdlc-validate.py --feature user-authentication
python3 .sdlc/tools/sdlc-validate.py --strict --json # CI gate, machine-readable
python3 .sdlc/tools/sdlc-validate.py --exclude 'docs/*.md'
```

Exit codes: `0` clean, `1` warnings under `--strict`, `2` errors. `--feature` narrows the findings, not the parse, so other features' tags still resolve. The exact rules, checks, and `config.json` overrides are in the validator's own docstring and `.sdlc/CONVENTIONS.md`.

### Changing a requirement

The command depends on **where** the change lands, not on how small it is:

| You are changing | Run | Why |
|---|---|---|
| A `REQ-*` — its text, or adding / removing one | `/sdlc-quickfix <slug>` | 1–3 EARS requirements, one specified feature, no new architecture |
| The feature's shape — new architecture, or more than a few requirements | `/sdlc-spec <slug>` | The change outgrows a delta |
| An `AC-*`/`US-*`/`NFR-*` in `problem-brief.md` | `/sdlc-plan` | The brief is project-level and single-writer |

IDs are immutable — never renumber, never recycle. Changing a requirement keeps its ID and edits its text; removing one retires it **in place**, and the marker must be the first thing in the line:

```
- `REQ-004` (AC-012): REMOVED (2026-03-01) — superseded by REQ-009.
```

A `REQ-*` change is per-feature and safe in any session; an `AC-*` change is project-level and wants a session of its own, because two sessions each appending "the next free `AC-*`" would collide on exactly the IDs the scheme declares immutable.

**The gate checks structure, not meaning.** Reword a requirement and the validator stays green while the code is stale — tags are unversioned, so a tag on `REQ-003` satisfies it whoever the text describes. Meaning changes are a manual three-part edit (spec, code, test-plan prose); the validator only catches the first, which is what `/sdlc-review` and `/sdlc-adopt`'s drift report are for.

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

Phases are stateless: each reads artifacts from disk, so chat history isn't part of the contract. A **fresh session is the healthy default** — smaller context, fewer decisions to re-check — but it is not required between phases; the single required freshness is `/sdlc-review`, which must not run in the session that wrote the implementation. So `/sdlc-spec` and `/sdlc-implement` can run in one session when the context still fits, and you can also finish a phase, exit, and start a fresh chat for the next. If your runtime offers conversation persistence (zrb's `/save` and `/load`), use it freely between phases — a resumed session is still treated as the session that did the work, so a review there is capped at COMMENT.

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

Skills are runtime-neutral: they describe **what** the LLM should do, not **which** tool to use. The delegation blocks in `sdlc-implement`, `sdlc-review`, and `sdlc-quickfix` are prompt templates — they prefer progressive disclosure and fall back to inlining for runtimes without file access. The validator and eval runner are stdlib-only Python 3.8+.

`~/.<tool>/skills/<name>/SKILL.md` is the open Agent Skills convention:

| Tool | Personal skills directory |
|------|---------------------------|
| Claude Code | `~/.claude/skills/` |
| zrb | `~/.zrb/skills/` |
| OpenAI Codex CLI | `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| GitHub Copilot | `~/.copilot/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| *(vendor-neutral)* | `~/.agents/skills/` — read by Copilot, OpenCode and others |

The remaining installer targets follow the same convention, inherited from OpenSpec's supported-tools table; only the rows above were checked against each tool's own documentation. Cursor is project-scoped only (`.cursor/skills/`, no `$HOME` location), so install to it with `--dir .cursor/skills`. Claude Code ignores the `disable-model-invocation` / `user-invocable` frontmatter (zrb-specific) but otherwise loads the skills as-is.

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
| `tests/test_sdlc_validate.py` | Validator regression tests — one case per shipped bug |
| `tests/test_skill_prompts.py` | Static invariants over the prompts — one case per prompt bug |

Only `sdlc-init` carries assets, so there are no bundled copies to keep in sync — edit the file and you are done. Scripts follow [kettanaito/naming-cheatsheet](https://github.com/kettanaito/naming-cheatsheet).

Every change is checked by `.github/workflows/ci.yml` — compile, validator regression tests, eval-case lint, installer dry-run — on Python 3.8. Run the same locally:

```bash
python3 tests/test_sdlc_validate.py   # validator regression tests
python3 tests/test_skill_prompts.py   # static invariants over the skill prompts
python3 evals/run.py                  # lint the eval cases
```

A change to the validator's parsing or check logic needs a case in `tests/test_sdlc_validate.py`; verify the case can actually fail by reintroducing the bug, then restoring it. For [zrb](https://github.com/state-alchemists/zrb), `zrb_init.py` exposes `zrb skill test` (all of the above) and `zrb skill install`.

---

## Key Design Notes & Limitations

**Addressed:**
- **Traceability is validated, not grepped.** The validator parses IDs and tags and fails on gaps, in both directions (`REQ-* → code`, and `REQ-* → AC-*` against the brief).
- **Canonical EARS** with uppercase keywords, plus migration hints for the old dialect.
- **IDs don't collide across features** — key-namespaced, with `.sdlc/keys/` claims for parallel sessions.
- **One file per feature** — requirements, design, and test plan live together in `spec.md`.
- **Migration is first-class** — `/sdlc-adopt` is history-preserving and idempotent.
- **Templates are project-owned** — editable, never clobbered.
- **The validator is tested** — `tests/test_sdlc_validate.py` pins every bug it has shipped.

**Still true:**
- **No CLI commands** — chat skills plus the bundled Python validator and eval runner are the whole surface.
- **No runtime approval enforcement** — approval tiers rely on the model following instructions; writes are not policy-gated.
- **The validator is structural, not semantic** — it checks IDs, tags, and EARS shape, not whether a requirement is correctly implemented.
- **The validator never runs your tests** — a `COVERS:` tag on a skipped test satisfies coverage; a tag on commented-out code is indistinguishable from a tag on live code.
- **Tags are unversioned** — reword a requirement and its tags still validate; re-verifying meaning is `/sdlc-review`'s and `/sdlc-adopt`'s drift report's job, on demand.
- **Specs are snapshots** — re-sync is manual. Shared by every spec-driven tool.
- **Evals grade deterministic checks only** — no LLM-as-judge, and grading still needs a human to produce the output.