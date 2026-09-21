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
- **Dates come from `date`**, not from memory or from a template's example.
- **Parallel sessions have a documented protocol**: which files are single-writer, and a
  `.sdlc/keys/<KEY>` claim file that turns a Feature Key collision on separate branches into a
  visible merge conflict.

### Tests and CI

- Validator regression suite: 24 → 57 cases. Each new case was verified to fail with its fix
  reverted.
- New `tests/test_skill_prompts.py`: static invariants over the prompts, which CI previously could
  not see at all. Nine cases, each pinning a prompt bug that actually shipped.
- `evals/run.py`: `absent_regex` no longer passes vacuously when the target file is missing — a
  case could pass by producing nothing. Adds `file_absent` and `max_matches`, rejects unknown keys
  and bad severities, and compiles every pattern at lint time.
- The duplicated `py_compile` file list in `zrb_init.py` and `ci.yml` is replaced by `compileall`.
- **`--tools all` now means every *verified* tool** (zrb, Claude Code). It used to sweep in ~30
  IDs inherited from OpenSpec's rules-file table, creating `~/.cospec`, `~/.bob`, `~/.qoder` and
  friends for software the user had never installed. Those IDs still work when named explicitly,
  with a warning.
