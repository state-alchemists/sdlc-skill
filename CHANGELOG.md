# Changelog

## Unreleased — the traceability gate now enforces what it claimed

**Breaking.** Projects that passed `sdlc-validate.py` before may fail now. That is the point: the
checks below were the ones the README's central claim rested on, and none of them were enforced.

### The gate

A project with **one source file carrying both an `IMPLEMENTS:` and a `COVERS:` header, and zero
test files**, used to validate clean and exit 0. So did a repo whose only "coverage" was the string
`"IMPLEMENTS: KEY:REQ-001"` inside a Python string literal, a line of un-fenced prose in a README,
or a commented-out implementation that kept its header.

- **A tag must sit inside a real comment**, and a header tag must *open* that comment. String
  literals, prose and `# This file does NOT IMPLEMENTS: X` no longer count.
- **`IMPLEMENTS:` counts only from a source file, `COVERS:` only from a test file.** Files are
  classified by path components and filename stems — never substrings — covering Python, Go
  (colocated `*_test.go`), Maven (`src/test/java`), Jest, RSpec, .NET and monorepos as shipped.
- **Documentation is never scanned.** A README showing the tag format is teaching it.
- **An unknown `--feature` slug is an ERROR.** It used to exit 0, so a mistyped slug bought
  `/sdlc-review` a clean validator and an APPROVE verdict.
- **A misplaced tag is named in the coverage error**, so the two findings read as one story.

### New: `.sdlc/config.json`

The first machine-readable configuration in the project. Optional — the built-in defaults cover
conventional layouts, and a project without one validates unchanged. It overrides source/test
classification, comment syntax per extension, renamed or translated headings, and scan limits.
Lists extend the defaults rather than replacing them. A malformed config is an ERROR naming the
key, never a silent fallback.

### New: `.sdlc/ANNOTATION.md`

Per-language comment syntax and header placement, shared by `/sdlc-implement`, `/sdlc-quickfix`
and `/sdlc-adopt`. Previously the only guidance was "`//` for JS/Go/Rust, `#` for Python/Ruby,
`--` for SQL" plus "top of every generated source file", which demonstrably produced files that do
not run: a `#` header above a shebang makes the kernel run the file as `/bin/sh`; two header lines
above a PEP 263 encoding declaration raise `SyntaxError`; `<!-- -->` above an XML prolog is a hard
parse error. Also covers `<?php`, CSS (`//` is not a comment there), single-file components,
formats with no comment syntax, and generated files whose headers are wiped on regeneration.

### Parser correctness

- **EARS false negatives**: "SHALL be fast and user-friendly", "AFTER x ... SHALL", several SHALL
  clauses in one requirement, and a bare "SHALL" all passed. Each now warns, with the fix.
- **EARS false positives**: the canonical composite `WHERE ..., IF ..., THEN ... SHALL` was flagged
  as the deprecated dialect — a form `CONVENTIONS.md` itself endorses — and `UNLESS` inside quoted
  UI copy was flagged as a keyword. Both fixed.
- **Fenced examples in a spec** were parsed as definitions: showing the `REMOVED` form inside a
  fence retired the real requirement. `parse_spec` now strips fences like the tag scanner does.
- **The fence tracker** is no longer a parity toggle: a fence closes only on the same character, at
  least as long, with no info string. Nested fences no longer flip parity for the rest of the file.
- **Prose no longer defines things.** `- REQ-001 was the hardest one` raised a duplicate-ID error;
  `- AC-777 was DELETED in March` made the brief "define" AC-777, disabling the citation check.
- **An `(AC-NNN)` citation without a colon** silently skipped the citation check entirely.
- **A test-plan row pointing at a REMOVED or unknown requirement** is now an error.
- **Skipped files are reported.** A file over the size limit, or containing a NUL byte, used to
  vanish silently and report its requirement as untraced with no explanation.

### Templates really are project-owned

Renaming `## Test Plan` used to produce a dangling-tag ERROR and a missing-test-plan WARNING;
rewording `## NFRs Validated Outside Code` produced three errors including a spurious duplicate ID;
dropping the bold from `**Feature Key:**` silently defaulted the key to the slug. All three now
work, common aliases are recognised, and `headings` in `config.json` declares anything else —
including a translated heading.

### SQL and infrastructure as code

An IaC manifest or a migration **is** the implementation in repositories built around one. The old
guidance — "tag the code that loads the file" — assumed a loader that does not exist there, and left
every such requirement to fail coverage.

- **`.tftest.hcl` is a test.** Terraform's native test framework exits non-zero on failure, so a
  requirement implemented in `.tf` can carry `COVERS:` from its own test file. It is a default stem
  pattern, like `*_test.go`.
- **A policy file that gates the merge is a test.** OPA/Conftest `.rego`, Checkov and tfsec rules,
  kubeconform schemas, and SQL assertions that run after a migration all carry `COVERS:` once their
  path resolves as a test. An advisory scan nobody fails on does not — that distinction is what
  makes the claim mean something, and `ANNOTATION.md` states it.
- **`.tf`, `.tfvars`, `.hcl`, `.yaml` and `.sql` are documented as source.** All five already
  parsed; what was missing was the instruction that in these trees the manifest is the deliverable.
  `.sql` also notes that one migration file legitimately carries one header for several statements.

### Requirements validated outside code

**Breaking for some projects.** A `REQ-*` listed under `## NFRs Validated Outside Code` now reports a
WARNING. It was *silently ignored* before: the exemption did not apply, no message said so, and the
requirement still failed `trace-code`/`trace-test` elsewhere in the same report. A project with a
stray functional requirement under that heading will see a new warning on upgrade. The warning is
correct — the requirement was never exempt — and names the heading to use instead.

- **`## Requirements With No In-Code Verification`** is the new heading, and exempts `REQ-*`. It is
  deliberately **not** the NFR heading widened: exempting a functional requirement is a bigger claim,
  since the code exists to implement it, and sharing one heading would let a `REQ-*` be exempted by
  moving its line — the cheapest way to turn a red gate green.
- The two patterns are **disjoint by construction**, pinned by a test. A heading matching both would
  mark one section as an NFR exemption and a functional exemption at once, so an NFR on the
  functional list would silently stop being tracked. "Requirements Not Verified In Code" collides
  this way and is not matched; "Validated Outside Code" phrasing lands in the NFR heading.
- `headings.outside_code_functional` declares a renamed or translated heading, separate from
  `headings.outside_code`.
- Both exemptions stay visible: every exempted requirement is reported as `outside-code` on every
  run, so an exemption is a recorded gap, not a deletion.
- A project with **no tests at all** still has no project-wide off switch. Requirements stay red
  until they have a real check or a declared exemption; `/sdlc-adopt` reports them as unadopted work.
- **The exemption is independent of the role gate.** `--relax-tag-roles` / `gate.enforce_tag_roles`
  loosen *where* a tag may sit; neither touches whether one is required. Relaxing the gate does not
  exempt a requirement, and does not suppress the misplaced-heading warning. Pinned by test, so a
  future change cannot quietly turn the migration ramp into an exemption switch.

### Genericity and process

- **`src/` + `tests/` is no longer hardcoded** in the prompts (13 sites across 5 files). The
  validator was always layout-agnostic; the instructions were not.
- **`docs/architecture.md` is no longer evidence of a legacy layout.** MkDocs, Docusaurus and
  Diátaxis all emit that filename, and treating it as a marker made `/sdlc-init` refuse to write
  steering documents on projects that had never run these skills. A weak marker now needs its own
  text to cross-reference the scheme.
- **`/sdlc-implement` forbids the sub-agent editing the spec** and verifies it afterwards. It was
  told to treat validator errors as failures to fix, with a retry loop, and the cheapest fix was
  to delete the requirement. `/sdlc-quickfix` had this guard; `/sdlc-implement` did not.
- **`SPEC:` is the header token everywhere** (was `GENERATED FROM SPEC:` in one skill).
- **A fresh session is required only for `/sdlc-review`.** `/sdlc-spec` → `/sdlc-implement` used to end with "Next, in a fresh session", mandating a close-and-reopen for every feature. Implementation reads `spec.md` from disk, so nothing about it depends on the spec session's context; freshness matters only for review independence, so the handoff now offers the same session. `CONVENTIONS.md` § Session handoff defines required-vs-optional, and the review blocks keep their fresh-session requirement.
- **Dates come from `date`**, not from memory or from a template's example.
- **Parallel sessions have a documented protocol**: which files are single-writer, and a
  `.sdlc/keys/<KEY>` claim file that turns a Feature Key collision on separate branches into a
  visible merge conflict.

### Tests and CI

- Validator regression suite: 24 → 77 cases. Each new case was verified to fail with its fix
  reverted.
- New `tests/test_skill_prompts.py`: static invariants over the prompts, which CI previously could
  not see at all. Nine cases, each pinning a prompt bug that actually shipped.
- `evals/run.py`: `absent_regex` no longer passes vacuously when the target file is missing — a
  case could pass by producing nothing. Adds `file_absent` and `max_matches`, rejects unknown keys
  and bad severities, and compiles every pattern at lint time.
- The duplicated `py_compile` file list in `zrb_init.py` and `ci.yml` is replaced by `compileall`.

### Installer

Three skills directories were wrong and are corrected, checked against each tool's own docs:

| Tool | Was | Now |
|---|---|---|
| GitHub Copilot | `~/.github/skills` | `~/.copilot/skills` |
| OpenCode | `~/.opencode/skills` | `~/.config/opencode/skills` |
| Cursor | `~/.cursor/skills` | *(removed — Cursor is project-scoped; use `--dir .cursor/skills`)* |

Adds `agents` → `~/.agents/skills`, the vendor-neutral location Copilot, OpenCode and others read
in addition to their own. CI pins all of these.

Correcting a path is not enough on its own: the previous version's copy stays where it was, and a
tool reading both has no way to tell which is current. Every run now sweeps the superseded
directories (`~/.opencode/skills`, `~/.github/skills`, `~/.cursor/skills`) under the same rule as
any other target — only skills this repo ships or used to ship — and `--keep-legacy` opts out. CI
pins the sweep, including that it leaves a user's own `sdlc-*` skill alone.

### Fixes to the above, before it ships

The strict gate was reviewed against real layouts, and four of its own defects are fixed here.

- **A comment after an apostrophe is no longer dropped.** Quote characters were counted
  independently, so `msg := "it's here" // IMPLEMENTS: KEY:REQ-001` looked like an open string: the
  tag vanished and its requirement reported as unimplemented with the header in plain sight. Now a
  single left-to-right pass with one active quote — and a quote with no partner on the line opens
  nothing, so Rust's `&'a str` and Lisp's `'(a b)` keep their trailing comments too.
- **Browser suites are tests.** `cypress/e2e/*.cy.ts` matched no built-in pattern, so a Cypress or
  Playwright project met the new rule with a wall of `tag-role` errors on files that were tests all
  along. `e2e`, `cypress`, `*.cy`, `*.e2e`, Failsafe's `*IT`, and Gradle's `src/integrationTest/`
  are defaults now. `features/` is deliberately still not one: `src/features/` is a component
  directory more often than a Cucumber suite, and a wrong default fails a *source* file.
- **Prose and data files are never scanned.** CONVENTIONS.md said a `.txt` file is not a claim, but
  the fallback comment leaders let `# IMPLEMENTS: KEY:REQ-001` in a `notes.txt` satisfy code
  coverage. `.txt`, `.log`, `.csv`, `.tsv` and `.json` join documentation as never-scanned;
  `.jsonc`, `.json5` and `.yaml` are configuration that really carries comments, and still count.
- **An unclosed code fence is reported.** Everything after it is blanked, so a requirement below a
  typo'd fence stopped existing and the tags pointing at it reported as dangling, with nothing
  connecting the two. Now a WARNING naming the line, in a spec and in the problem brief.

And one hole that was not a defect so much as a missing exit:

- **`--relax-tag-roles` / `gate.enforce_tag_roles`** is the migration ramp. It restores the old
  leniency for the role rule alone — a tag counts wherever it sits, a misplaced one is a WARNING
  that still names where it belongs — while the comment rule stays on. The relaxed gate announces
  itself as a WARNING on every run, so it is visible in the report and non-zero under `--strict`:
  a ramp for the first pass over an existing project, not a setting to forget. A `gate` value that
  is not `true`/`false` is an ERROR, never a silent "off".

One behaviour is now pinned rather than changed: a header inside a Python **docstring** does not
count, because a docstring is a string. `ANNOTATION.md` already put the `#` header after it; a test
now holds the parser and the guidance together.
