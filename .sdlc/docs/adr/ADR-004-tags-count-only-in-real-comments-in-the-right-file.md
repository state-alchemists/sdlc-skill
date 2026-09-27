# ADR-004: A tag counts only in a real comment, in the right kind of file

## Status
Accepted

## Context
Under the original lenient rules, one source file carrying both `IMPLEMENTS:` and `COVERS:` — with zero tests — validated clean. So did a tag inside a string literal, a line of README prose, or a `notes.txt`. That gate proved nothing.

## Decision
A tag counts only when:
1. It opens a real comment in that file's own syntax. The comment syntax comes from per-extension tables; a docstring is a string, not a comment.
2. It sits in the right kind of file: `IMPLEMENTS:` in **source**, `COVERS:` in **test**. A file is a test by path component or filename stem (`tests/`, `*_test.go`, `src/test/`), never by substring.
3. The file is not documentation, prose or data, which are never scanned.

`.sdlc/config.json` overrides every default, and its lists extend the built-ins. `gate.enforce_tag_roles: false` (or `--relax-tag-roles`) is the only switch that weakens a check. It is a migration ramp and announces itself as a WARNING on every run.

## Consequences
### Positive
- A green gate means a separate test file claims each requirement.
- Go, Maven, Jest, RSpec, .NET, Cypress, Terraform and monorepo layouts work without configuration.
### Negative
- The file scanner reads comments line by line without a full parser. Unusual syntax needs a `comments` entry in config.
- Existing projects meet a wall of `tag-role` errors on upgrade, which is what the ramp is for.

## Implements Rules
- RULE-003 — A regression case per fix

## Verification
- `tests/test_sdlc_validate.py`: `case_a_file_cannot_implement_and_cover_itself`, `case_tag_in_a_string_literal_is_not_a_tag`, `case_negated_mention_of_implements_is_not_a_tag`, `case_header_inside_a_python_docstring_does_not_count`, `case_colocated_go_test_is_classified_as_a_test`, `case_relaxed_gate_counts_a_misplaced_tag_and_says_so`, `case_malformed_config_is_reported_not_ignored`.

## References
- `.sdlc/CONVENTIONS.md` § File roles and `.sdlc/config.json` · `.sdlc/ANNOTATION.md`
