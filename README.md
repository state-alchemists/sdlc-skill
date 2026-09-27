# SDLC AI Plugin

Seven chat skills (`/sdlc-init`, `/sdlc-plan`, …) that guide an LLM through spec-driven development, plus a deterministic validator that fails the build when code and requirements stop tracing to each other.

- **Primary target: zrb.** Also runs under Claude Code and the ~30 other tools that load `SKILL.md` files — the skills are runtime-neutral.
- **Templates live in your project** at `.sdlc/templates/`. Edit them and every later run follows your shape — no forking.
- **Skills, not CLI commands.** The only shell entry points are the installer, the validator and the eval runner.

## Install

```bash
bin/install.sh                                # auto-detect — only tools already on this machine
bin/install.sh --tools all                    # every known AI coding tool
bin/install.sh --tools codex,opencode,gemini  # specific tools
bin/install.sh --dir .claude/skills           # project-scoped, checked into the repo
bin/install.sh --dry-run --tools claude       # preview without changing anything
bin/install.sh --uninstall --tools all        # remove this repo's sdlc-* skills
```

Portable bash (macOS 3.2 included). It replaces prior copies, removes skills this repo used to ship (`sdlc-requirements`, `sdlc-architect`, `sdlc-document`, `sdlc-migrate`), and sweeps directories earlier versions installed to (`--keep-legacy` opts out). Your own skills, including your own `sdlc-*` ones, are never touched. No flag for your tool? `cp -R skills/sdlc-* <dotdir>/skills/`.

**Upgrade:** `git pull && bin/install.sh`, then in each project run `/sdlc-init` (refreshes the validator, keeps your documents) and, if it reports a legacy layout, `/sdlc-adopt`. Newer validators enforce rules older ones only claimed — read the [CHANGELOG](CHANGELOG.md) before upgrading CI.

## Quick start

```
# Once per project
/sdlc-init                 # 1. scaffolding + steering docs + rules
/sdlc-plan                 # 2. problem brief + entity dictionary + ADRs + architecture

# Once per feature
/sdlc-spec <feature>       # 3. spec.md — EARS requirements + design + test plan
/sdlc-implement <feature>  # 4. code + tests carrying KEY:REQ-* tags
/sdlc-review <feature>     # 5. validator + fresh-context review   ← needs a fresh session

# As needed
/sdlc-quickfix <feature>   # small change as a delta, promoted into the spec
/sdlc-adopt                # brownfield: relocate, reverse-engineer specs, annotate
```

`<feature>` becomes a slug (`User Auth` → `.sdlc/specs/user-auth/`).

| Skill | Produces | Scrum parallel |
|-------|----------|----------------|
| `/sdlc-init` | `.sdlc/` scaffolding, `product.md`, `tech.md`, `test-strategy.md`, `AGENTS.md`, `rules.md`. Greenfield is interviewed; brownfield gets a derived draft to confirm. | Sprint Zero |
| `/sdlc-plan` | `problem-brief.md` (`US-*`/`AC-*`/`NFR-*`), `entity-dictionary.md`, `adr/ADR-*.md`, `architecture.md`. Merges on re-run. | Backlog + architecture spike |
| `/sdlc-spec` | One `spec.md` per feature: EARS requirements, Feature Key, API, errors, correctness properties, test plan. | Refinement to "Ready" |
| `/sdlc-implement` | Code and tests from one coding sub-agent that reads the spec from disk; verifies tests, lint, validator (retry cap 2). | Sprint work |
| `/sdlc-review` | Validator, then a fresh-context review sub-agent. Verdict mapped by rule: APPROVE / REQUEST CHANGES / COMMENT. | Code review + DoD |
| `/sdlc-quickfix` | An `ADDED/MODIFIED/REMOVED` delta, implemented, reviewed inline, promoted into `spec.md`. | Hotfix lane |
| `/sdlc-adopt` | Legacy artifacts relocated under `.sdlc/` (history kept), specs reverse-engineered from code, source annotated, setup completed. | Tech-debt onboarding |

Phases are artifact stages, not ceremonies; standups, estimation and timeboxing stay yours. The fine print — paths, EARS dialect, ID scheme, file roles, approval tiers, parallel sessions — is in [`CONVENTIONS.md`](skills/sdlc-init/assets/CONVENTIONS.md), installed at `.sdlc/CONVENTIONS.md`.

## Real-world flows

Each phase reads its inputs from disk, not chat history, so you may run consecutive phases in one session. **The one exception is `/sdlc-review`**: run in the session that wrote the code — including one resumed with zrb's `/save`/`/load` — its verdict is capped at COMMENT.

- **Greenfield:** init → plan → spec → implement → review. The next feature starts at `/sdlc-spec`.
- **Another feature:** spec → implement → review. Features can run in parallel — each writes its own `.sdlc/specs/<slug>/`, and Feature Keys stop IDs colliding. Use a git worktree per parallel implementation.
- **Bug fix:** `/sdlc-quickfix <feature>` — describe it in a sentence, approve a 1–3 requirement delta.
- **Spec drift:** code changed outside the pipeline → `/sdlc-adopt` (document mode) writes a drift report → absorb each finding into the spec or fix the code → `/sdlc-review`.
- **Brownfield, never used these skills:** `/sdlc-init` (brownfield path) → `/sdlc-adopt` (document a subsystem) → `/sdlc-plan`.
- **Project from an older version:** artifacts already under `.sdlc/` need only `/sdlc-init`. A legacy layout (`docs/adr/`, root `rules.md`, `specs/`) needs `/sdlc-init` → `/sdlc-adopt`, and adopt finishes setup.

### Changing a requirement

| You are changing | Run |
|---|---|
| A `REQ-*` (text, add, remove) — 1–3 requirements, no new architecture | `/sdlc-quickfix <slug>` |
| The feature's shape, or more than a few requirements | `/sdlc-spec <slug>` |
| An `AC-*`/`US-*`/`NFR-*` in `problem-brief.md` | `/sdlc-plan` — project-level and single-writer, so its own session |

IDs are never renumbered or recycled; a removed requirement is retired in place (`REMOVED (date) — reason`).

## Traceability

Every spec declares a unique `**Feature Key:**` and IDs are written `KEY:REQ-NNN`:

```python
# SPEC: .sdlc/specs/user-authentication/spec.md
# IMPLEMENTS: AUTH:REQ-001, AUTH:NFR-002     # source file header
# COVERS: AUTH:REQ-002, AUTH:UT-005          # test file header
# @sdlc AUTH:REQ-003                         # above the function that fulfils it
```

`python3 .sdlc/tools/sdlc-validate.py` parses these back and exits `2` when the chain breaks: a requirement with no implementation or test, a tag pointing at nothing, a recycled ID, a duplicate key, or a requirement citing an `AC-*` the problem brief does not define. A tag counts only inside a real comment, only from the right kind of file (`IMPLEMENTS:` from source, `COVERS:` from a test), and never from documentation.

```bash
python3 .sdlc/tools/sdlc-validate.py                          # whole project
python3 .sdlc/tools/sdlc-validate.py --feature user-authentication
python3 .sdlc/tools/sdlc-validate.py --strict --json          # CI gate
```

Exit `0` clean, `1` warnings under `--strict`, `2` errors. Every finding id is listed in the validator's docstring; layout overrides go in `.sdlc/config.json`.

## Generated project structure

```
<project-root>/
├── AGENTS.md                          # AI assistant guide
└── .sdlc/
    ├── CONVENTIONS.md  ANNOTATION.md  config.json  rules.md
    ├── keys/<KEY>                     # Feature Key claims (parallel-session safety)
    ├── templates/*.md                 # project-owned; every skill generates from these
    ├── tools/sdlc-validate.py
    ├── docs/{product,tech,test-strategy,architecture}.md, adr/ADR-*.md
    ├── requirements/{problem-brief,entity-dictionary}.md
    ├── specs/<slug>/spec.md           # + quickfix-<ts>.md, drift-report-<ts>.md
    └── reviews/<slug>/report-<ts>.md
```

Source and tests stay wherever your project keeps them.

## Evals

`evals/golden/` holds five golden cases (one each for init, spec, implement, quickfix, adopt), and `evals/run.py` grades their deterministic `checks.json` assertions against a skill's output — no LLM needed. Rubric items stay human-graded. See [`evals/README.md`](evals/README.md).

```bash
python3 evals/run.py --list                   # list cases
python3 evals/run.py                          # lint case structure
python3 evals/run.py --actual /path/to/output # grade produced output
```

## Runtime compatibility

The skills say **what** to do, not which tool to use; the delegation blocks in implement, review and quickfix prefer the sub-agent reading files, and fall back to inlining. Validator and eval runner are stdlib-only Python 3.8+.

| Tool | Personal skills directory |
|------|---------------------------|
| Claude Code | `~/.claude/skills/` |
| zrb | `~/.zrb/skills/` |
| OpenAI Codex CLI | `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| GitHub Copilot | `~/.copilot/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| *(vendor-neutral)* | `~/.agents/skills/` — read by Copilot, OpenCode and others |

Only these rows were checked against each tool's documentation; the other installer targets follow the same `<dotdir>/skills/` convention, inherited from OpenSpec. Cursor is project-scoped only: `--dir .cursor/skills`. Claude Code ignores the zrb-specific `disable-model-invocation` / `user-invocable` frontmatter.

## Limitations

- **Approval tiers are instructions, not enforcement** — no runtime gates the writes.
- **The validator is structural, not semantic.** It checks IDs, tags and EARS shape, never whether code does what a requirement says, and never runs your tests: a `COVERS:` on a skipped test counts.
- **Tags are unversioned.** Reword a requirement and its tags still validate; re-checking meaning is `/sdlc-review`'s and the drift report's job.
- **Specs are snapshots.** Re-sync is manual, as in every spec-driven tool.
- **Evals grade deterministic checks only**, and a human still has to produce the output.

How this compares with Spec Kit, Kiro, OpenSpec and others: [product.md § Alternatives & Positioning](.sdlc/docs/product.md#alternatives--positioning).

## Contributing

Everything exists once. Only `sdlc-init` carries assets, which the installer copies verbatim:

| File | Role |
|------|------|
| `skills/<name>/SKILL.md` | The skill — workflow only, no embedded templates |
| `skills/sdlc-init/assets/templates/*.md` | Templates, installed to `.sdlc/templates/` |
| `skills/sdlc-init/assets/{CONVENTIONS,ANNOTATION}.md`, `config.json` | Installed to `.sdlc/` |
| `skills/sdlc-init/assets/tools/sdlc-validate.py` | Validator, installed to `.sdlc/tools/` |
| `tests/test_sdlc_validate.py` | Validator regression tests — one case per shipped bug |
| `tests/test_skill_prompts.py` | Static invariants over the prompts — one case per prompt bug |
| `tests/test_eval_runner.py`, `tests/test_install.sh` | Eval-runner and installer tests |
| `bin/test.sh` | Every check CI runs (also `zrb skill test`) |
| `.sdlc/`, `AGENTS.md` | This repo's own SDLC documents — product, tech, rules, brief, specs, architecture, ADRs. `bin/test.sh` holds the repo to its own `--strict` gate. |

```bash
bin/test.sh
```

Change behaviour through the repo's own workflow: update the spec in `.sdlc/specs/<feature>/` (or run `/sdlc-quickfix`), then the code, tests and tags. A validator or eval-runner change needs a case you have seen fail with the fix reverted (RULE-003). Names follow [kettanaito/naming-cheatsheet](https://github.com/kettanaito/naming-cheatsheet).
