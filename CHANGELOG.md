# Changelog

## Unreleased — the traceability gate enforces what it claimed

Projects that passed `sdlc-validate.py` before may fail now. Previously a project with **one source file carrying both an `IMPLEMENTS:` and a `COVERS:` header and zero test files** validated clean and exited 0 — as did "coverage" that was only a string literal, a line of unfenced README prose, or a commented-out implementation that kept its header.

### Breaking — the gate

- **A tag must sit inside a real comment and open it.** String literals, prose and `# This file does NOT IMPLEMENTS: X` no longer count. A header inside a Python docstring does not count either (a docstring is a string; `ANNOTATION.md` puts the header after it) — now pinned by a test.
- **`IMPLEMENTS:` counts only from a source file, `COVERS:` only from a test file.** Files are classified by path component and filename stem, never substring, covering Python, Go (`*_test.go`), Maven (`src/test/java`, Failsafe `*IT`), Jest, RSpec, .NET, Gradle (`src/integrationTest/`), Cypress/Playwright (`e2e/`, `cypress/`, `*.cy`, `*.e2e`) and monorepos. `features/` is deliberately not a default: `src/features/` is a component directory more often than a Cucumber suite.
- **Never scanned:** documentation (`.md`, `.rst`, `.adoc`) and prose/data (`.txt`, `.log`, `.csv`, `.tsv`, `.json`) — a `# IMPLEMENTS:` line in `notes.txt` used to satisfy coverage through the fallback comment leaders. `.jsonc`, `.json5` and `.yaml` carry real comments and still count.
- **An unknown `--feature` slug is an ERROR.** It exited 0, so a mistyped slug bought `/sdlc-review` an APPROVE.
- **A `REQ-*` under `## NFRs Validated Outside Code` is a WARNING.** It was silently ignored: not exempt, no message, still failing `trace-code`/`trace-test` elsewhere. The warning names the heading to use instead.

### Added

- **`--relax-tag-roles` / `gate.enforce_tag_roles: false`** — the migration ramp. A tag counts wherever it sits and a misplaced one is a WARNING that still names where it belongs; the comment rule stays on. Every relaxed run reports `gate-relaxed` as a WARNING, so it fails `--strict`. A non-boolean `gate` value is an ERROR.
- **`## Requirements With No In-Code Verification`** exempts `REQ-*`, separately from the NFR heading: exempting what the code is *for* is a bigger claim, and a shared heading would let a `REQ-*` be exempted by moving its line. The two heading patterns are disjoint by construction, pinned by a test ("Requirements Not Verified In Code" would match both and is not accepted). `headings.outside_code_functional` declares a renamed heading. Every exempted requirement is reported as `outside-code` on every run. The exemption is independent of the role gate — relaxing one never touches the other (pinned by test). There is still no project-wide off switch for a project with no tests.
- **`.sdlc/config.json`** — optional; overrides source/test classification, comment syntax per extension, headings (renamed or translated), `generated_globs`/`vendored_globs` (never scanned), and scan limits. Lists extend the defaults. A malformed config is an ERROR naming the key.
- **`.sdlc/ANNOTATION.md`** — per-language comment syntax and header placement, shared by implement, quickfix and adopt. The old guidance ("top of every generated source file") produced files that do not run: a `#` above a shebang runs the file as `/bin/sh`; two lines above a PEP 263 encoding line raise `SyntaxError`; `<!-- -->` above an XML prolog is a parse error. Also covers `<?php`, CSS (`//` is not a comment), single-file components, formats with no comment syntax, and generated files.
- **IaC and SQL as implementation.** `.tf`, `.tfvars`, `.hcl`, `.yaml` and `.sql` are documented as source (one header may cover a multi-statement migration). `*.tftest.hcl` is a default test stem. A policy file that gates the merge (OPA/Conftest `.rego`, Checkov, tfsec, kubeconform, post-migration SQL assertions) is a test; an advisory scan is not.
- **Parallel-session protocol:** single-writer files are listed, and `.sdlc/keys/<KEY>` turns a Feature Key collision on separate branches into a visible merge conflict.
- **`ac-uncited` (INFO):** a brief AC that no active requirement cites is now reported on whole-project runs, closing the upstream half of the chain. INFO rather than WARNING, because unspecified backlog is normal and must not fail `--strict`; a `--feature` run stays quiet.
- **Findings no longer vanish silently:** an oversized, binary or unreadable file is reported as `skipped-file`; an unclosed code fence in a spec or brief is a WARNING naming the line; a misplaced tag is named inside the coverage error it causes; a test-plan row citing a REMOVED or unknown requirement is an ERROR.

### Fixed — parser

- **EARS false negatives** now warn with the fix: "SHALL be fast and user-friendly", "AFTER x … SHALL", several SHALL clauses in one requirement, a bare "SHALL".
- **EARS false positives** removed: the canonical composite `WHERE …, IF …, THEN … SHALL` was flagged as deprecated, and `UNLESS` inside quoted UI copy as a keyword.
- **Prose no longer defines IDs:** `- REQ-001 was the hardest one` raised a duplicate-ID error; `- AC-777 was DELETED in March` defined AC-777 and disabled the citation check.
- **Fenced examples** in a spec were parsed as definitions (showing the `REMOVED` form retired the real requirement). The fence tracker now closes only on the same character, at least as long, with no info string, instead of toggling parity.
- **An `(AC-NNN)` citation without a colon** skipped the citation check.
- **A comment after an apostrophe** (`msg := "it's here" // IMPLEMENTS: …`) was dropped. Strings are now scanned with one active quote, and an unpartnered quote (Rust `&'a str`, Lisp `'(a b)`) opens nothing.
- **Templates are project-owned for real:** renaming `## Test Plan`, rewording the exemption heading, or dropping the bold from `**Feature Key:**` no longer breaks validation; common aliases are recognised and `headings` declares the rest.
- **`docs/architecture.md` alone is no longer a legacy marker** — MkDocs, Docusaurus and Diátaxis emit it, and it made `/sdlc-init` refuse to write steering documents on projects that never used these skills. A weak marker now needs its own text to cross-reference the scheme.
- **A requirement repeated under an exemption heading lost its definition.** The documented pattern — define `REQ-001` under `## Requirements`, repeat it under `## Requirements With No In-Code Verification` — replaced the requirement's text and citation with the exemption note, so the note was EARS-checked and the AC the real definition cites looked uncited. Found by running the gate over this repository.
- **`layout.generated_globs` / `layout.vendored_globs`**, which `ANNOTATION.md` told projects to set, were reported as unknown keys — failing the recommended `--strict` CI gate. They are now accepted, and matching files are not scanned.

### Changed — skills and process

- **No hardcoded `src/` + `tests/`** in the prompts (13 sites across 5 files); the layout comes from the project.
- **`/sdlc-implement` forbids the sub-agent editing the spec** and verifies it with `git diff`. Its retry loop made deleting a requirement the cheapest fix.
- **A fresh session is required only for `/sdlc-review`**, whose verdict is capped at COMMENT in the implementing session. Spec → implement may share a session.
- **`product.md` has an Alternatives & Positioning section** (status quo included, each row sourced, dated, never invented), and Out of Scope items state their trade-off. `/sdlc-init` asks what people use today instead.
- **Legacy detection, EARS table, ID and slug rules are stated once**, in `CONVENTIONS.md`; skills reference them instead of carrying copies.
- **Diagrams are Mermaid, and the structure view fits the project.** `architecture.md` keeps a System Context `flowchart` (not the experimental `C4Context`), but its mandatory "Container Diagram (C4 Level 2)" is replaced by a **Structure** section whose view is picked from the project's shape — containers only for separately running programs; modules, public API, commands, pipeline, deployment topology or artifact lifecycle otherwise. The Data Flow prose becomes Key Flows sequence diagrams. `entity-dictionary.md` states relationships as an `erDiagram` instead of a table. `/sdlc-plan` checks that every Mermaid block renders.
- **`SPEC:` is the header token everywhere** (was `GENERATED FROM SPEC:` in one skill). **Dates come from `date`**, never memory or a template's example.

### Installer

| Tool | Was | Now |
|---|---|---|
| GitHub Copilot | `~/.github/skills` | `~/.copilot/skills` |
| OpenCode | `~/.opencode/skills` | `~/.config/opencode/skills` |
| Cursor | `~/.cursor/skills` | *(removed — project-scoped; use `--dir .cursor/skills`)* |

Adds `agents` → `~/.agents/skills` (vendor-neutral). Every run sweeps the superseded directories above — only skills this repo ships or used to ship — so an upgrade does not leave two copies; `--keep-legacy` opts out. The documented `--dry-run --tools cursor` example, which exited with "Unknown tool ID", now uses `claude`.

### This repository follows its own method

`.sdlc/` now holds this repo's product, tech and test-strategy docs, `rules.md` (8 rules), problem brief (6 stories, 13 ACs), entity dictionary, architecture, 12 ADRs, and four specs — `VAL` (validator), `INST` (installer), `EVAL` (eval runner), `SKILL` (skill prompts) — with `IMPLEMENTS:`/`COVERS:` headers in the code and tests. `bin/test.sh` runs the validator over the repo with `--strict`. `.sdlc/`'s conventions, templates and validator are symlinks into `skills/sdlc-init/assets/`, so nothing is copied. `LANDSCAPE.md` moved into `.sdlc/docs/product.md`. Prompt requirements are exempted under the no-in-code-verification heading because the validator never scans Markdown — the framework cannot yet trace a requirement into a prompt.

### Tests and CI

- Validator regression suite: 24 → 81 cases, each verified to fail with its fix reverted. New `tests/test_skill_prompts.py`: 16 static invariants over the prompts, each pinning a prompt bug that shipped.
- `evals/run.py`: `absent_regex` no longer passes when the target file is missing; adds `file_absent` and `max_matches`; rejects unknown keys and bad severities; compiles every pattern at lint time.
- New `tests/test_eval_runner.py` (6 cases) and `tests/test_install.sh` (6 cases, adding auto-detect, dry-run and unknown-tool checks).
- `bin/test.sh` runs every check; CI and `zrb skill test` both call it instead of keeping twin command lists.
