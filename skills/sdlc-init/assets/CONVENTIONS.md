# SDLC Conventions

Single source of truth for paths, the EARS dialect, the ID/traceability scheme, and approval tiers. Every `sdlc-*` skill reads this file; skills point here rather than restating a rule.

## Artifact paths

| Artifact | Path | Template |
|----------|------|----------|
| Steering docs | `.sdlc/docs/{product,tech,test-strategy}.md` | `product.md`, `tech.md`, `test-strategy.md` |
| AI assistant guide | `AGENTS.md` (repo root) | `agents.md` |
| Architecture | `.sdlc/docs/architecture.md` | `architecture.md` |
| ADRs | `.sdlc/docs/adr/ADR-{N}.md` | `adr.md` |
| Rules (constitution) | `.sdlc/rules.md` | `rules.md` |
| Problem brief | `.sdlc/requirements/problem-brief.md` | `problem-brief.md` |
| Entity dictionary | `.sdlc/requirements/entity-dictionary.md` | `entity-dictionary.md` |
| Spec (requirements + design + test plan) | `.sdlc/specs/<slug>/spec.md` | `spec.md` |
| Quickfix delta | `.sdlc/specs/<slug>/quickfix-{ts}.md` (to `<slug>/archive/` once promoted) | `quickfix.md` |
| Drift report | `.sdlc/specs/<slug>/drift-report-{ts}.md` | `drift-report.md` |
| Review report | `.sdlc/reviews/<slug>/report-{ts}.md` | `review-report.md` |
| Templates | `.sdlc/templates/` | — |
| Validator | `.sdlc/tools/sdlc-validate.py` | — |
| Config | `.sdlc/config.json` | — |
| Annotation reference | `.sdlc/ANNOTATION.md` | — |
| Feature Key claims | `.sdlc/keys/<KEY>` | — |

**Templates are project-owned.** Every document a skill writes is filled from `.sdlc/templates/`; edit a template to change what every later run produces. Missing `.sdlc/templates/` means the project is not initialised — run `/sdlc-init`, which installs them without touching existing documents.

## Legacy layout

Older projects keep steering docs at `docs/`, ADRs at `docs/adr/`, requirements at `requirements/`, rules at `rules.md`, specs at `specs/`, and a separate test plan at `.sdlc/tests/<slug>/test-plan.md`. Skills **read** a legacy location when the canonical one is absent, but never write a parallel tree.

A project is on the **legacy SDLC layout** when either holds:

1. **A conclusive marker exists** — `docs/adr/ADR-*.md`; a root `rules.md` containing `RULE-`; `specs/<slug>/spec.md` (or `requirements.md` + `design.md`); `requirements/problem-brief.md` or `requirements/entity-dictionary.md`; `docs/product.md`, `docs/tech.md` or `docs/test-strategy.md`; or any `@sdlc`, `IMPLEMENTS:` or `COVERS:` tag in the code.
2. **A weak marker cross-references the scheme** — `docs/architecture.md` whose text contains `.sdlc/`, `ADR-<n>`, `RULE-<n>`, `US-<n>`, `AC-<n>`, `NFR-<n>` or `Feature Key`. On its own it is not evidence: MkDocs, Docusaurus and Diátaxis all emit that filename.

Detect **by content, never by directory name** — most projects have a `docs/`. Matching is case-sensitive: `ARCHITECTURE.md` is the project's own document, `architecture.md` is the one `/sdlc-init` writes, and `docs/adr/0007-title.md` is not `ADR-0007-title.md`. A near-miss is a miss.

**Which command finishes setup depends on where the artifacts are, not how old the project is.**

| Artifacts are… | Run | Why |
|---|---|---|
| Nowhere (no scaffolding) | `/sdlc-init` | Creates the structure and finishes setup |
| Already under `.sdlc/` | `/sdlc-init` (brownfield path) | Fills gaps, e.g. a missing `.sdlc/rules.md`; nothing to relocate |
| At a legacy path (one marker is enough) | `/sdlc-init`, then `/sdlc-adopt` | Init installs scaffolding and stops — writing `.sdlc/docs/product.md` beside `docs/product.md` would be a parallel tree. Adopt relocates, then runs init's Phase 3b–5 on the relocated tree. Adopt is the last command. |

## File roles and `.sdlc/config.json`

The validator classifies every file as **source**, **test**, or **documentation**. A tag counts only:

| Tag | From | Because |
|-----|------|---------|
| `IMPLEMENTS:` | a **source** file | a requirement is implemented by code |
| `COVERS:` | a **test** file | a requirement is covered by a test that runs |
| any | inside a **real comment**, opening it | a string literal, prose, or `# does NOT IMPLEMENTS: X` is not a claim |

**Never scanned**: documentation (`.md`, `.rst`, `.adoc`, …) — a README teaching the format is not a claim — and prose/data (`.txt`, `.log`, `.csv`, `.tsv`, `.json`, …). `.jsonc`, `.json5` and `.yaml` carry real comments and are scanned. A comment is what the file's own syntax says: a Python docstring is a string, so `.sdlc/ANNOTATION.md` puts the header *after* it.

**Test files** are recognised by path component and filename stem, never substring: a `tests`/`test`/`spec`/`__tests__`/`e2e`/`cypress` directory; a `src/test/`, `src/it/` or `src/integrationTest/` fragment; or a stem like `test_*`, `*_test`, `*_spec`, `*.test`, `*.spec`, `*.cy`, `*.tftest`, `*Test`, `*Tests`, `*IT`. That covers Python, Go's `*_test.go`, Maven and Failsafe, Jest, RSpec, Cypress, Playwright, .NET, Gradle, Terraform tests and monorepos, while `src/contest/models.py` stays source. `features/` is deliberately not a default (`src/features/` is usually components); declare it if yours is a Cucumber suite.

A check is a test when **CI fails on it**, whatever its format: a policy file that gates the merge (OPA/Conftest `.rego`, Checkov, tfsec, a schema) carries `COVERS:` once its path resolves as a test; an advisory scan does not. See `.sdlc/ANNOTATION.md` for IaC and SQL.

Everything above is a default. `.sdlc/config.json` is optional; every list **extends** the built-in one:

```json
{
  "layout": {
    "test_directory_names": ["it"],
    "test_stem_patterns": ["*Check"],
    "test_path_fragments": ["app/spec/"],
    "source_overrides": ["src/testing/*"],
    "test_overrides": ["tools/smoke/*"],
    "generated_globs": ["gen/*"],
    "vendored_globs": ["third_party/*"]
  },
  "headings": {
    "test_plan": ["Rencana Pengujian"],
    "outside_code": [],
    "outside_code_functional": []
  },
  "comments": { ".myext": { "line": ["#"], "block": [["/*", "*/"]] } },
  "gate": { "enforce_tag_roles": true },
  "scan": {
    "skip_directories": ["generated"],
    "scan_directories": ["build"],
    "max_file_bytes": 2097152
  }
}
```

- **Globs** (`*_overrides`, `generated_globs`, `vendored_globs`) match the whole path or the basename. `source_overrides` beats `test_overrides`, and both beat every other rule. Files matching `generated_globs`/`vendored_globs` are never scanned and never annotated.
- `scan_directories` removes a name from the skip list (for real code under `build/`).
- `headings` declares a renamed or translated heading. Built-in matching already accepts `Tests`, `Test Cases`, `Test Design`, `Testing` and common rewordings of the exemption headings. `outside_code` (NFR exemption) and `outside_code_functional` (REQ exemption) are separate keys — see below.
- `comments` teaches the validator an extension. An unknown extension falls back to `#`, `//`, `--`, `;`, `%`, `!`.
- `gate.enforce_tag_roles: false` (or `--relax-tag-roles`) is the **migration ramp** and the only switch that weakens a check: a tag counts wherever it sits and a misplaced one is a WARNING. Every run then reports `gate-relaxed` as a WARNING, so `--strict` still fails. Misplaced tags are still listed.
- A malformed config — including a `gate` value that is not `true`/`false` — is an **ERROR** naming the key, never a silent fallback. An unknown key is a WARNING.

## Requirements validated outside code

Two headings in `spec.md` exempt a requirement from `IMPLEMENTS:`/`COVERS:`. They are separate because they make different claims:

| Heading | Exempts | For |
|---|---|---|
| `## NFRs Validated Outside Code` | `NFR-*` only | a quality attribute checked by infra or process (backup policy, SLO) |
| `## Requirements With No In-Code Verification` | `REQ-*` | a functional requirement no executable check can reach |

- **Only the heading exempts.** List the NFR once in the NFR table and repeat its ID under the heading. Wording in the "Validated By" cell exempts nothing (`process`, `manual` and `dashboard` are ordinary English), and neither does naming CI — CI is where validation runs, not what performs it.
- A `REQ-*` under the **NFR** heading is a WARNING, not an exemption.
- Every exempted requirement is reported as `outside-code` on every run: an exemption is a recorded gap, not a deletion.
- `gate.enforce_tag_roles` is orthogonal: it loosens *where* a tag may sit, never *whether* one is required.
- Prefer a real check. Most IaC requirements can carry `COVERS:` from a policy file that gates the merge.

## Feature slugs

Lowercase; spaces/underscores to `-`; drop characters outside `[a-z0-9-]`; collapse repeated `-`; trim leading/trailing `-`. Tell the user when the slug differs from their input. Slugs are stable — never rename once code references `.sdlc/specs/<slug>/`.

## Canonical EARS dialect

| Pattern | Template | Use for |
|---------|----------|---------|
| Ubiquitous | The `<system>` SHALL `<response>`. | an invariant on every path |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. | a user action or system event |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. | behaviour that holds while in a state |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. | a flag or configured feature |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. | an error, guard, or invalid input |
| Complex | WHILE `<state>`, WHEN `<trigger>`, the `<system>` SHALL `<response>`. | several clauses |

Canonical EARS (Mavin et al.). Keywords are **uppercase** — that is what makes them keywords; lowercase `when`/`shall` is prose and the validator warns. One requirement, one SHALL. No unverifiable words ("fast", "user-friendly") — state the threshold. Deprecated dialect migrates as: `ALWAYS SHALL` → ubiquitous; `AS <c> THEN SHALL` → `IF <c>, THEN … SHALL`; `UNLESS <b> THEN SHALL <d>` → `IF NOT <b>, THEN … SHALL <d>`; state-driven `WHERE <state>` → `WHILE <state>`.

## ID & traceability scheme

- **Feature Key**: each `spec.md` declares `**Feature Key:** <KEY>` — `[A-Z][A-Z0-9_-]*`, globally unique. Default: the uppercased slug when valid; a shorter alias is fine (`user-authentication` → `AUTH`). A digit-led slug cannot become a key (`2fa` → `2FA:REQ-001` does not parse), so declare one (`TWOFA`); the validator errors rather than guessing.
- **Per-feature IDs** (`REQ-`, `NFR-`, `UT-`, `IT-`, `E2E-`, `PBT-`) are disambiguated by the key: `AUTH:REQ-003`.
- **Project-level IDs**: `US-*`, `AC-*`, `NFR-*` live in `problem-brief.md`; a spec cites them. A brief-level `NFR-001` cited by two features becomes two targets (`AUTH:NFR-001`, `BILL:NFR-001`), each needing its own tags — each feature carries its share.
- **Citations**: a requirement's `(AC-NNN)` must exist in the brief (ERROR otherwise) — this catches an AC renumbered upstream. The reverse — a brief AC no active requirement cites — is reported as `ac-uncited` INFO on whole-project runs: normally unspecified backlog, so it never fails `--strict`. With no brief yet (specs `/sdlc-adopt` wrote from code), write no citation; the check stays silent. Never invent one.
- **Tags** — header syntax and placement per language are in `.sdlc/ANNOTATION.md`; never guess a comment syntax:
  - Source header: `IMPLEMENTS: <KEY>:REQ-001, <KEY>:NFR-002`
  - Test header: `COVERS: <KEY>:REQ-002, <KEY>:UT-005, <KEY>:IT-001`
  - Inline, above the unit that directly fulfils it: `@sdlc <KEY>:REQ-003, <KEY>:REQ-004`
- Every active `REQ-*` and `NFR-*` needs at least one `IMPLEMENTS:` and one `COVERS:`, unless exempted above. Unkeyed legacy tags (`@sdlc REQ-003`) WARN and **do not count** until re-keyed (`/sdlc-adopt`).
- **IDs are immutable**: continue from the highest existing ID; never renumber or recycle. Change a requirement by editing its text under the same ID. Retire it **in place** — its text must **begin** with `REMOVED ({date}) — {reason}`, directly after the citation; anything else between ID and `REMOVED` leaves it active:

  ```
  - `REQ-004` (AC-012): REMOVED (2026-03-01) — superseded by REQ-009.
  ```

  Retiring also means removing the ID from every `IMPLEMENTS:` header, deleting its `@sdlc` tags (a tag on a retired ID is a dangling-tag ERROR), and deleting its test-plan rows.
- **Validate**: `python3 .sdlc/tools/sdlc-validate.py [--feature <slug>] [--strict] [--exclude GLOB]` — exit 0 clean, 1 warnings under `--strict`, 2 errors. `--feature` narrows the findings, not the parse. Fenced code blocks in Markdown are never read. Wire it into CI:

  ```yaml
  - name: SDLC traceability
    run: python3 .sdlc/tools/sdlc-validate.py --strict
  ```

## Parallel sessions

**Safe in parallel** — each belongs to one feature, so git merges cleanly: `.sdlc/specs/<slug>/**`, `.sdlc/keys/<KEY>`, and that feature's own source and test files. For parallel *implementation*, use a git worktree per feature.

**Single-writer — one session at a time**: `.sdlc/requirements/*`, `.sdlc/rules.md`, `.sdlc/docs/**`, `.sdlc/CONVENTIONS.md`, `.sdlc/config.json`. `/sdlc-init` and `/sdlc-plan` own these. Two sessions appending "the next free `AC-*`" collide on IDs declared immutable — so never run two of either at once, and `/sdlc-spec` never extends the brief.

**Claiming a Feature Key**: list taken keys, then **create `.sdlc/keys/<KEY>` containing the slug before writing the spec**:

```bash
grep -h '^\*\*Feature Key:\*\*' .sdlc/specs/*/spec.md | sort
```

The grep cannot see unmerged branches; the claim file turns a same-key collision into a git add/add conflict — loud and quick to resolve. `spec.md`'s `**Feature Key:**` stays authoritative.

## Session handoff

Skills are stateless — each reads artifacts from disk — so the transition message is the only place a user learns what comes next. Every skill ends with an **action block**:

```
Next, in a fresh session — pick any order:

  [ ] /sdlc-spec billing-export        from the brief you just wrote
  [ ] /sdlc-spec audit-log             independent, safe to run in parallel

Both may run at once: each writes only its own .sdlc/specs/<slug>/ and key.
```

- **Paste-ready**: write the literal command with the slug already resolved (`/sdlc-implement user-auth`), never `<slug>`.
- **Only what the artifacts support**: no `/sdlc-review` for a feature with no code. Noise teaches users to skip the block. A single item is fine; do not pad.
- **Name the parallel opportunity** when two or more specs exist — the one thing a user cannot infer from the artifacts.
- **Fresh session is required only before `/sdlc-review`** (see § Review independence). Everywhere else it is context hygiene, not a gate: `/sdlc-spec` → `/sdlc-implement` may share a session, because the implementer reads `spec.md` from disk.

## Review independence

An APPROVE from the session that wrote the code is a false pass. Defined here once; skills reference it.

- `/sdlc-review` first asks whether this session wrote the implementation — via `/sdlc-implement`, `/sdlc-quickfix`, or `/sdlc-adopt` Mode C — or resumed one with `/save`/`/load` (a resumed session carries the context over). If so, or the user cannot rule it out, the review is **in-session**: the report records it and the verdict is **capped at COMMENT**. REQUEST CHANGES stays reachable.
- `/sdlc-quickfix`'s inline review is in-session by design and never independent. An independent verdict means `/sdlc-review <slug>` in a fresh session.

## Dates and timestamps

From the system clock, never memory or an example. Run once per phase and reuse:

```bash
date +%Y-%m-%d               # 2026-09-22           -> {{TODAY}}
date -u +%Y-%m-%dT%H-%M-%SZ  # 2026-09-22T14-03-09Z -> {{TIMESTAMP}}
```

`{{TIMESTAMP}}` is UTC so parallel sessions sort correctly; colons are hyphens for filesystem safety. Pair a fact about code with `git rev-parse --short HEAD`. No shell? Ask the user. Dates in this file and in templates are examples, never values.

## Approval tiers

- **Tier 1 — per-item approval**: hard-to-reverse writes — modifying a rule, superseding an ADR, resolving an entity conflict, overwriting an existing spec, moving files.
- **Tier 2 — one batched approval**: routine first-time generation (steering docs together; requirements together; a spec).
- **Tier 3 — none**: read-only analysis, validator runs, review reports.

Only an affirmative ("yes", "ok", "approved", "go ahead") approves, at any tier. Silence or a vague reply is a change request.
