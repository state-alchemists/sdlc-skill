# SDLC Conventions

Single source of truth for paths, the EARS dialect, the ID/traceability scheme, and approval tiers. Every `sdlc-*` skill reads this file.

## Artifact paths (canonical)
| Artifact | Path |
|----------|------|
| Steering docs | `.sdlc/docs/` |
| ADRs | `.sdlc/docs/adr/` |
| Architecture | `.sdlc/docs/architecture.md` |
| Requirements | `.sdlc/requirements/` |
| Specs (requirements + design + test plan) | `.sdlc/specs/<slug>/spec.md` |
| Reviews | `.sdlc/reviews/<slug>/report-{YYYY-MM-DDTHH-MM-SS}.md` |
| Rules | `.sdlc/rules.md` |
| Templates | `.sdlc/templates/` |
| Validator | `.sdlc/tools/sdlc-validate.py` |
| Machine-readable config | `.sdlc/config.json` |
| Annotation reference | `.sdlc/ANNOTATION.md` |
| Feature Key claims | `.sdlc/keys/<KEY>` |

**Legacy fallback**: older projects keep steering docs at `docs/`, ADRs at `docs/adr/`, requirements at `requirements/`, rules at `rules.md`, and a separate test plan at `.sdlc/tests/<slug>/test-plan.md`. Skills read legacy locations if the canonical one is absent, but never write a parallel tree. Run `/sdlc-adopt` to consolidate.

<!-- legacy-detection:start -->
A project is on the **legacy SDLC layout** when either of these holds:

1. **A conclusive marker exists** — `docs/adr/ADR-*.md`; a root `rules.md` containing `RULE-`; `specs/<slug>/spec.md` (or `requirements.md` + `design.md`); `requirements/problem-brief.md` or `requirements/entity-dictionary.md`; or `docs/product.md`, `docs/tech.md` or `docs/test-strategy.md` — names this project writes and almost nothing else does.
2. **A weak marker exists and its own text cross-references the scheme** — `docs/architecture.md` containing `.sdlc/`, `ADR-<n>`, `RULE-<n>`, `US-<n>`, `AC-<n>`, `NFR-<n>` or `Feature Key`.

**`docs/architecture.md` on its own is not evidence.** MkDocs, Docusaurus and Diátaxis all emit that filename by default; far more projects have one than have ever run `/sdlc-init`. Treating it as a marker made `/sdlc-init` refuse to write steering documents on projects that had never used these skills.

Matching is case-sensitive: `ARCHITECTURE.md` is the project's own document, `architecture.md` is the one `/sdlc-init` writes. A near-miss is a miss — and the near-miss that bites is the lowercase collision, not the uppercase one.
<!-- legacy-detection:end -->

## Templates
Every document a skill writes comes from a template in `.sdlc/templates/`. Edit those files to change the shape of what the skills produce — they are project-owned, and skills read them at generation time rather than carrying their own copies.

| Template | Produces |
|----------|----------|
| `product.md` | `.sdlc/docs/product.md` |
| `tech.md` | `.sdlc/docs/tech.md` |
| `test-strategy.md` | `.sdlc/docs/test-strategy.md` |
| `agents.md` | `AGENTS.md` (repo root) |
| `rules.md` | `.sdlc/rules.md` |
| `problem-brief.md` | `.sdlc/requirements/problem-brief.md` |
| `entity-dictionary.md` | `.sdlc/requirements/entity-dictionary.md` |
| `adr.md` | `.sdlc/docs/adr/ADR-{N}.md` |
| `architecture.md` | `.sdlc/docs/architecture.md` |
| `spec.md` | `.sdlc/specs/<slug>/spec.md` |
| `quickfix.md` | `.sdlc/specs/<slug>/quickfix-{ts}.md` (archived to `<slug>/archive/` once promoted) |
| `review-report.md` | `.sdlc/reviews/<slug>/report-{ts}.md` |
| `drift-report.md` | `.sdlc/specs/<slug>/drift-report-{ts}.md` |

If `.sdlc/templates/` is missing, the project has not been initialised (or predates templates) — run `/sdlc-init`, which installs them without touching existing documents.

## File roles and `.sdlc/config.json`

The validator classifies every file it scans as **source**, **test**, or **documentation**, and a traceability tag only counts from the right one:

| Tag | Counts only from | Rationale |
|-----|------------------|-----------|
| `IMPLEMENTS:` | a **source** file | a requirement is implemented by code |
| `COVERS:` | a **test** file | a requirement is covered by a test that runs |
| any tag | inside a **real comment** | a string literal, a line of prose, or a `.txt` file is not a claim |

Two kinds of file are never scanned at all. Documentation (`.md`, `.rst`, `.adoc`, ...) shows the tag format rather than claiming coverage — a README teaching it is not a claim. Prose and data (`.txt`, `.log`, `.csv`, `.tsv`, `.json`, ...) implement nothing, so a `#`-prefixed line in one is not a header either; `.jsonc`, `.json5` and `.yaml` are configuration that really does carry comments, and are scanned normally.

A **comment is what the file's own syntax says it is**, not anything that looks like one. A Python docstring is a string, which is why `.sdlc/ANNOTATION.md` puts the `#` header *after* the module docstring rather than inside it.

**Test files are recognised by path components and filename stems, never by substring**: a `tests`/`test`/`spec`/`__tests__`/`e2e`/`cypress` directory, a `src/test/`, `src/it/` or `src/integrationTest/` path fragment, or a stem like `test_*`, `*_test`, `*_spec`, `*.test`, `*.spec`, `*.cy`, `*.tftest`, `*Test`, `*Tests`, `*IT`. That covers Python, Go's colocated `*_test.go`, Maven's `src/test/java` and Failsafe's `*IT.java`, Jest's `*.test.ts` and `__tests__/`, RSpec's `spec/`, Cypress's `cypress/e2e/*.cy.ts`, Playwright, .NET's `*Tests.cs`, Gradle's `src/integrationTest/`, Terraform's `*.tftest.hcl` and monorepo nesting — and it leaves `src/contest/models.py` and `src/latest_prices.py` as source, which substring matching would not. `features/` is deliberately *not* a default: `src/features/` is a component directory far more often than it is a Cucumber suite. Declare it in `test_directory_names` if yours is one.

A check is a test when **CI fails on it**, whatever its format. A policy file that gates the merge — OPA/Conftest `.rego`, a Checkov or tfsec rule set, a schema — carries `COVERS:` legitimately once its path resolves as a test; an advisory scan nobody fails on does not. See `.sdlc/ANNOTATION.md` for the IaC and SQL cases.

Everything above is a **default**, not a requirement. `.sdlc/config.json` overrides it; the file is optional, and a project without one validates on the defaults. Every list **extends** the built-in list rather than replacing it, so the file stays short and keeps working when the defaults grow.

```json
{
  "layout": {
    "test_directory_names": ["it"],
    "test_stem_patterns": ["*Check"],
    "test_path_fragments": ["app/spec/"],
    "source_overrides": ["src/testing/*"],
    "test_overrides": ["tools/smoke/*"]
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

- `source_overrides` and `test_overrides` are globs, matched against the whole path or the basename, and win over every other rule. `source_overrides` wins over `test_overrides`.
- `scan_directories` removes a name from the skip list — a project whose real code lives under `build/` needs it.
- `headings` names a renamed or translated `## Test Plan` / `## NFRs Validated Outside Code` heading. The built-in match already accepts `Tests`, `Test Cases`, `Test Design`, `Testing` and common rewordings of the exemption heading; declare anything else here.
- `headings.outside_code_functional` is a **separate** key from `outside_code`, because it exempts a different thing: `outside_code` covers `NFR-*` only, and a `REQ-*` listed under it is reported as a warning rather than exempted. The functional heading exempts `REQ-*`. Keep the two apart — a heading matching both patterns would mark one section as both kinds of exemption at once.
- `comments` teaches the validator a file extension it does not know. An unknown extension falls back to a generous set of line-comment leaders rather than losing its tags.
- `gate.enforce_tag_roles` is the **migration ramp**, and the only switch that weakens a check. Setting it to `false` — or passing `--relax-tag-roles` — makes a tag count wherever it sits and drops a misplaced one to a WARNING, which is how the validator behaved before this rule existed. Every run then reports `gate-relaxed` as a WARNING, so it is visible in the report and non-zero under `--strict`: it is a ramp for the first pass over an existing project, not a setting. The misplaced tags are still listed, so the worklist survives.
- A malformed `config.json` is an **ERROR** naming the key. Silently ignoring a layout declaration would report a project's real tags as missing, and a `gate` value that is not `true`/`false` is an error rather than a silent "off".

## Requirements validated outside code

Two headings in `spec.md` exempt a requirement from `IMPLEMENTS:`/`COVERS:`. They are separate because they make different claims.

| Heading | Exempts | Meaning |
|---|---|---|
| `## NFRs Validated Outside Code` | `NFR-*` only | a quality attribute checked by infra or process — a backup policy, an SLO |
| `## Requirements With No In-Code Verification` | any ID, in practice `REQ-*` | a functional requirement no executable check can reach |

Both work by the **presence of the heading**, never by the wording of the NFR table's "Validated By" cell. That was tried and removed: `process`, `manual` and `dashboard` are ordinary English words, and reading them as an exemption silently exempted work that was never verified at all.

Two rules the validator enforces:

- A `REQ-*` under the **NFR** heading is a **warning**, not an exemption. It used to be ignored in silence, which meant the requirement appeared exempt while still failing its coverage checks elsewhere in the report.
- Every exempted requirement is still reported, as `outside-code`, on every run. The gap stays visible; it is exempted, not hidden.

Prefer a real check. A policy file that gates the merge is a test, so most IaC requirements can carry `COVERS:` rather than an exemption — see `.sdlc/ANNOTATION.md`.

`gate.enforce_tag_roles` / `--relax-tag-roles` is **orthogonal** to both headings. It loosens *where* a tag may sit; it never changes whether a requirement needs one, and it does not suppress the misplaced-heading warning.

## Feature slugs
A feature directory name is the slug of the feature: lowercase; spaces/underscores to `-`; drop characters outside `[a-z0-9-]`; collapse repeated `-`; trim leading/trailing `-`. Slugs are stable — never rename once code references `.sdlc/specs/<slug>/`.

A slug may start with a digit (`2fa`), but a **Feature Key may not** — so the uppercased slug is not always a usable key. When it is not, declare one explicitly (`2fa` → `**Feature Key:** TWOFA`). The validator errors rather than guessing, because `2FA:REQ-001` does not parse as a keyed tag and the feature could never satisfy traceability.

## Canonical EARS dialect
| Pattern | Template |
|---------|----------|
| Ubiquitous | The `<system>` SHALL `<response>`. |
| Event-driven | WHEN `<trigger>`, the `<system>` SHALL `<response>`. |
| State-driven | WHILE `<state>`, the `<system>` SHALL `<response>`. |
| Optional feature | WHERE `<feature is included>`, the `<system>` SHALL `<response>`. |
| Unwanted behaviour | IF `<condition>`, THEN the `<system>` SHALL `<response>`. |
| Complex | Combine, e.g. WHILE `<state>`, WHEN `<trigger>`, the `<system>` SHALL `<response>`. |

This is canonical EARS (Mavin et al.). EARS keywords are written in uppercase — that is what makes them keywords, and the validator only treats uppercase occurrences as such. Deprecated dialect found in old specs migrates as: `ALWAYS SHALL` to ubiquitous (drop ALWAYS); `AS <c> THEN SHALL` to `IF <c>, THEN ... SHALL`; `UNLESS <b> THEN SHALL <d>` to `IF NOT <b>, THEN ... SHALL <d>`; old `WHERE <state>` (state-driven) to `WHILE <state>`.

## ID & traceability scheme
- Each `spec.md` declares `**Feature Key:** <KEY>` — an uppercase token `[A-Z][A-Z0-9_-]*`, globally unique across all features. Default suggestion: the uppercased slug, when that is a valid key.
- Requirement IDs are per-feature (`REQ-001`, `NFR-001`, `UT-001`, `IT-001`, `E2E-001`, `PBT-001`) and disambiguated globally by the key.
- `US-*`, `AC-*` and `NFR-*` in `problem-brief.md` are **project-level**; a spec cites them. Because tags are key-namespaced, one brief-level `NFR-001` cited by two features becomes two targets (`AUTH:NFR-001`, `BILL:NFR-001`) and needs its own `IMPLEMENTS:`/`COVERS:` under each key. That is intended: each feature carries its own share of the NFR.
- A requirement's `(AC-NNN)` citation is validated against `problem-brief.md` when one exists: citing an `AC-*` the brief does not define is an ERROR. This is the check that catches an AC renumbered upstream. Specs written by `/sdlc-adopt` before a brief exists carry no citation, and the check stays silent.
- **Where a header goes, and in what syntax**: `.sdlc/ANNOTATION.md` — the per-language comment table, the placement rules (after a shebang, an encoding line, a licence block, a module docstring, `<?php`, an XML prolog), and the policy for files that cannot carry a comment or that are generated. Never guess a comment syntax.
- Source header: `IMPLEMENTS: <KEY>:REQ-001, <KEY>:NFR-002`
- Test header: `COVERS: <KEY>:REQ-002, <KEY>:UT-005, <KEY>:IT-001`
- Inline tag: `@sdlc <KEY>:REQ-003, <KEY>:REQ-004`
- IDs are immutable: never renumber or recycle. A removed requirement keeps its ID, and its text **begins** with `REMOVED ({date}) — {reason}`, after the `(AC-NNN)` citation if it has one — the validator only treats a requirement as retired when the text starts that way:

  ```
  - `REQ-004` (AC-012): REMOVED (2026-03-01) — superseded by REQ-009.
  ```

  Retiring a requirement also means removing its ID from any `IMPLEMENTS:` header and deleting its `@sdlc` tags; a tag pointing at a retired ID is a dangling-tag ERROR.
- An NFR validated outside application code is listed once in the NFR table **and** repeated under "NFRs Validated Outside Code". The heading is the **only** thing that exempts it — wording in the "Validated By" cell exempts nothing, and neither does naming CI, because CI is where validation runs, not what performs it.
- Unkeyed legacy tags (`@sdlc REQ-003`) are reported as WARNINGs and **do not satisfy coverage** — the requirement still reports as untraced until the tag is re-keyed. Run `/sdlc-adopt` to re-key.
- Validate with `python3 .sdlc/tools/sdlc-validate.py [--feature <slug>] [--strict] [--exclude GLOB]` — exit 0 clean, 1 warnings (with `--strict`), 2 errors. `--feature` narrows the **findings**; every spec is still parsed, so other features' tags resolve. Fenced code blocks in Markdown are never read as tags, so documentation can show the format freely; `--exclude` covers anything else.

  Wire it into CI as the gate it was built to be:

  ```yaml
  - name: SDLC traceability
    run: python3 .sdlc/tools/sdlc-validate.py --strict
  ```

## Parallel sessions

Running several features at once is supported, but only some artifacts tolerate it.

**Safe to write from a parallel session** — each belongs to exactly one feature, so git merges them cleanly:
`.sdlc/specs/<slug>/**`, `.sdlc/keys/<KEY>`, and that feature's own source and test files.

**Single-writer — run these alone, in their own session**: `.sdlc/requirements/problem-brief.md`, `.sdlc/requirements/entity-dictionary.md`, `.sdlc/rules.md`, `.sdlc/docs/**`, `.sdlc/CONVENTIONS.md`, `.sdlc/config.json`. `/sdlc-init` and `/sdlc-plan` own these. Two sessions both appending "the next free `AC-*`" to the same brief will collide on exactly the IDs this scheme declares immutable — so do not run two of either at once, and do not let `/sdlc-spec` extend the brief.

**Claiming a Feature Key.** List what is taken with one command rather than re-reading every spec:

```bash
grep -h '^\*\*Feature Key:\*\*' .sdlc/specs/*/spec.md | sort
```

That grep cannot see a spec on another, unmerged branch. So when you choose a key, **create `.sdlc/keys/<KEY>` containing the slug, before writing the spec**. Two sessions choosing different keys create different files and always merge; two choosing the same key create the same path with different content, which git reports as an add/add conflict at merge time — loud, unmissable, and resolvable in seconds. `spec.md`'s `**Feature Key:**` stays authoritative; `.sdlc/keys/` is the allocation hint.

For parallel *implementation*, use a git worktree per feature.

## Dates and timestamps

Dates come from the system clock, never from memory and never from an example. Run the command once at the start of the phase that needs it and reuse the value:

```bash
date +%Y-%m-%d               # 2026-09-22           -> {{TODAY}}
date -u +%Y-%m-%dT%H-%M-%SZ  # 2026-09-22T14-03-09Z -> {{TIMESTAMP}}
```

`{{TIMESTAMP}}` is UTC so files produced by parallel sessions on different machines sort in real order. Colons are hyphens for filesystem safety.

Where an artifact records a fact about code, pair it with the commit: `git rev-parse --short HEAD`.

If no shell is available, ask the user for today's date. **Never guess it, and never copy a date out of a template or another document** — a date like `2026-03-01` appears in this file and in `spec.md` as an *example*, not as a value.

## Approval tiers
- **Tier 1 — explicit per-item approval**: global / hard-to-reverse writes — `rules.md` rule modifications, ADR supersessions, entity-dictionary conflict resolutions, overwriting an existing spec, file moves.
- **Tier 2 — one batched approval**: routine first-time generation (steering docs together; requirements together; spec together).
- **Tier 3 — no approval**: read-only analysis, validator runs, and review reports (the report is the deliverable, not a source mutation).
Anything other than an affirmative ("yes" / "ok" / "approved" / "go ahead") is a change request, at any tier. Silence or a vague reply is a change request.
