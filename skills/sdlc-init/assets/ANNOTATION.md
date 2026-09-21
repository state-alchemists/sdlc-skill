# Annotation Reference

How to write a traceability header so the file still parses, still runs, and still passes its own linter. Read this **before** writing the first header, not after the test suite goes red.

`.sdlc/config.json` overrides this file per extension under `comments`. Where an extension appears in neither, ask — do not guess.

---

## The rule that matters most

> **Comments and headers only. Never logic, never formatting, never imports.** If a file needs restructuring to be taggable, do not restructure it — note it and move on.
>
> **Use the file's own comment syntax. Place file headers after any shebang, encoding line, or licence block, and after the module docstring — never above it.**

A header is not decoration. Put it in the wrong place and the file stops working:

| What you write | What actually happens |
|---|---|
| `#` header above `#!/usr/bin/env python3` | The shebang is no longer line 1. The kernel runs the file as `/bin/sh`: `syntax error near unexpected token` |
| Two header lines above `# -*- coding: utf-8 -*-` | PEP 263 requires the encoding on line 1 or 2. It is now line 3, silently ignored — or a `SyntaxError` |
| `<!-- -->` above `<?xml version="1.0"?>` | Hard parse failure: `XML or text declaration not at start of entity` |
| `//` above `<?php` | Everything before `<?php` is emitted as raw output — broken JSON, "headers already sent" |
| `//` in a `.css` file | `//` is not a CSS comment. The parser eats the rule that follows |
| A comment directly above Go's `package` | It becomes the package doc comment and shows up in `godoc` |

---

## Placement anchors

The header goes **after** whatever the file requires to come first. General rule, for anything not listed: *if the first line of a file is required by anything to be exactly what it is, the header goes after it.*

| ID | Put the header after | Applies to |
|----|----------------------|------------|
| **P0** | Nothing — first line is fine | most languages |
| **P1** | the `#!` shebang | `.py .sh .bash .zsh .rb .pl .lua`, any CLI entrypoint |
| **P2** | the encoding / magic comment (must stay on line 1–2) | `.py` (`coding:`), `.rb` (`frozen_string_literal:`), `.pl` |
| **P3** | the licence / copyright block | any — SPDX and licence scanners require it first |
| **P4** | the module docstring | `.py .ex .exs .clj .rkt` — a string that is no longer the first statement stops being a docstring |
| **P5** | `<?php` — never above it | `.php` |
| **P6** | the XML prolog / doctype, before the root element | `.xml .xsl .svg .plist .html` |
| **P7** | inside the `<script>` block, in that block's syntax | `.vue .svelte .astro` |
| **P8** | a first line a tool requires | `.sql` migrations (`-- +goose Up`, `-- migrate:up`), Haskell `{-# LANGUAGE #-}` pragmas |
| **P9** | **No header. Do not tag.** | formats with no comment syntax — see below |

Go has one extra rule: leave a **blank line** between the header and `package`, or the header becomes the package doc comment.

---

## Comment syntax by extension

| Line comment | Extensions | Anchor |
|---|---|---|
| `//` | `.js .jsx .mjs .cjs .ts .tsx .go .rs .java .kt .kts .swift .c .h .cpp .hpp .cc .cs .scala .dart .zig .groovy .proto .gradle .sol .v .sv` | P0 (P1 for JS CLI entrypoints; P3 where a licence header leads) |
| `//` | `.php` | **P5** |
| `#` | `.py` | **P1 → P2 → P4** |
| `#` | `.rb` | P1 → P2 |
| `#` | `.sh .bash .zsh .fish .pl .ps1` | P1 |
| `#` | `.yaml .yml .toml .tf .tfvars .r .jl .nim .cr .cmake .conf`, `Dockerfile`, `Makefile`/`.mk` | P0 — in a Makefile the header must sit at column 0, tabs are significant |
| `#` | `.ex .exs` | P4 (after `@moduledoc`) |
| `--` | `.sql` | **P8** |
| `--` | `.lua` | P1 |
| `--` | `.hs .lhs` | P8 (after `{-# LANGUAGE #-}`) |
| `--` | `.elm .adb .ads .vhd` | P0 |
| `;` | `.lisp .cl .clj .cljs .el .scm .rkt .asm .ini` | P4 for Clojure `ns` docstrings |
| `%` | `.tex .erl .m` (MATLAB) | P0 |
| `!` | `.f90 .f95 .f03 .f08` | P0 — fixed-form `.f`/`.for` needs `C` in column 1; prefer not to tag |
| `'` | `.vb .vbs` | P0 |
| `"` | `.vim` | P0 |

| Block comment only | Extensions | Anchor |
|---|---|---|
| `/* */` | **`.css`** — `//` is a parse error here, always use `/* */` | P0 |
| `/* */` | `.scss .less .styl` — `//` compiles away, `/* */` survives into the built stylesheet; use `/* */` for consistency across the tree | P0 |
| `<!-- -->` | `.html .htm .xml .xsl .svg .plist .xaml` | **P6** |
| `<!-- -->` | `.md .markdown` | P0 — but see "Documentation" below |

**Ambiguous by extension — resolve in `.sdlc/config.json`, never guess:** `.m` (MATLAB `%` vs Objective-C `//`), `.h` (C/C++ vs Objective-C), `.pl` (Perl `#` vs Prolog `%`), `.t`, `.sc`, `.res`.

An extension in neither table falls back to a generous set of line-comment leaders (`#`, `//`, `--`, `;`, `%`, `!`). That keeps an exotic language working, but declare it in `config.json` so the intent is recorded.

---

## Formats that cannot carry a comment

`.json`, `.geojson`, `*.lock`, `.csv`, `.tsv` and every binary format **get no header**.

1. Tag the **code that loads, validates or writes the file** — the schema class, the loader, the migration runner. That is where the requirement is actually implemented.
2. Where the file's *contents* are the deliverable, the header goes in the module that loads it, and the spec's Test Plan names the test that asserts those contents.
3. **Never invent a comment.** No `"_comment": "IMPLEMENTS: ..."` key, no `#` line in a JSON file, no header row in a CSV. That changes the data, and every consumer of that data becomes your problem.
4. `.jsonc`, `.json5` and `.yaml` **do** support comments — tag them normally.
5. `.ipynb` is JSON on disk but a cell's source is text: put the header at the top of the **first code cell**. Never hand-edit the notebook JSON.

## Generated and vendored files

**Never annotate a file you do not own.** A file is not yours when any of these holds:

- it matches `layout.generated_globs` or `layout.vendored_globs` in `.sdlc/config.json`;
- it sits under `node_modules/`, `vendor/`, `third_party/`, `dist/`, `build/`, `target/`, `.venv/`;
- its first five lines contain `DO NOT EDIT`, `@generated`, or `Code generated by`;
- `.gitattributes` marks it `linguist-generated`.

A header on a generated file is wiped by the next regeneration, and the validator then reports the requirement as **untraced** — worse than never tagging it, because the build fails later, at an unrelated moment, for a reason nobody will connect to the regeneration.

Instead: tag the generator's **input** (`.proto`, `openapi.yaml`, the schema file) — it is hand-written and carries comments — and the hand-written wrapper that consumes the generated code. **List every file you skipped, in your report.** A silent skip looks identical to a file you missed.

## Documentation

`.md`, `.rst`, `.adoc` and friends are **never scanned for tags**. A README that shows `IMPLEMENTS:` is teaching the format, not claiming coverage. Do not put real headers in documentation and expect them to count.

---

## Header mechanics

- A header is one or two lines: `SPEC: <path>` and then `IMPLEMENTS:` (source) or `COVERS:` (test). One blank line after, before the code.
- **Never wrap a header across lines.** The validator reads one line; a wrapped ID list silently loses its tail.
- In a block-comment-only language, put both lines inside **one** block comment.
- The tag must **open** its comment. `# This file does NOT IMPLEMENTS: X` is prose about the format and does not count — which is the point.
- A tag only counts inside a real comment, and only from the right kind of file: `IMPLEMENTS:` from source, `COVERS:` from a test. See `.sdlc/CONVENTIONS.md` § File roles.
- **Idempotent**: if a header already exists, edit it in place. Never add a second.

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session handling."""

# SPEC: .sdlc/specs/user-auth/spec.md
# IMPLEMENTS: AUTH:REQ-001, AUTH:REQ-003

# @sdlc AUTH:REQ-003
def validate_login(...): ...
```

```php
<?php
// SPEC: .sdlc/specs/user-auth/spec.md
// IMPLEMENTS: AUTH:REQ-004
```

```css
/*
 * SPEC: .sdlc/specs/user-auth/spec.md
 * IMPLEMENTS: AUTH:NFR-002
 */
```

After annotating, **run the test suite**. These edits add comments only, so a failure means a header landed inside a docstring, broke a continuation line, or displaced an encoding declaration. Fix it or revert that file.
