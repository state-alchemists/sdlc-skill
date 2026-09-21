# Rubric: sdlc-adopt / legacy-layout-migration

Grader evaluates the migrated tree. Deterministic subset in `checks.json`; the
judgement items below are human-graded.

## Mode A — layout

| Check | Pass criteria |
|-------|---------------|
| History preserved | Files were moved with `git mv`, not copied — `git log --follow` on `.sdlc/docs/product.md` reaches the original |
| Nothing left behind | No legacy path still holds a migrated artifact |
| Cross-references repointed | Links in `README.md` / `AGENTS.md` to moved paths still resolve |
| Two-file spec merged | `requirements.md` + `design.md` became one `spec.md` with a declared Feature Key |

## Mode B — documented from code

| Check | Pass criteria |
|-------|---------------|
| Spec reflects the code | Requirements describe what `src/auth/` actually does, not what it should do |
| No invented citations | Requirements carry no `(AC-NNN)` when no problem brief exists |
| Drift report written | States `UNCHANGED` / `MODIFIED` / `ADDED` / `REMOVED-from-code` per finding |

## Mode C — annotation

| Check | Pass criteria |
|-------|---------------|
| **Shebang intact** | `src/auth/session.py` still begins with `#!/usr/bin/env python3` |
| **Encoding line intact** | `src/auth/cli.py` still has its `coding:` declaration on line 1 or 2 |
| Headers in the right files | `IMPLEMENTS:` only in source, `COVERS:` only in tests |
| Vendored untouched | `vendor/lib/x.py` carries no header |
| Generated untouched | `api/gen/user_pb2.py` carries no header |
| Skips reported | The report names every file skipped and why |
| Suite still passes | Mode C added comments only; the test suite runs green |
| Project's own docs untouched | `src/auth/README.md` is byte-identical |

## Reporting

| Check | Pass criteria |
|-------|---------------|
| Change Plan preceded writes | One plan, with risk levels, approved before anything was written |
| Before/after counts given | Source files carrying `IMPLEMENTS:`, tests carrying `COVERS:`, features with a spec |
