# ADR-010: Legacy layouts are detected by content; /sdlc-adopt finishes their setup

## Status
Accepted

## Context
Older projects keep artifacts at `docs/`, `specs/` and a root `rules.md`. Two past failures shaped this decision:
- Detecting by directory name flagged every project with a `docs/architecture.md` (a MkDocs, Docusaurus and Diátaxis default), and `/sdlc-init` then refused to write steering docs.
- Telling legacy projects to "re-run `/sdlc-init`" after adopting sent them back to a skill that stops again, for the same reason.

## Decision
- **Detection by content.** Conclusive markers are file names this project writes and little else does, or any existing tag in the code. A weak marker (`architecture.md`) counts only when its text cross-references the scheme. Matching is case-sensitive. The rule is written once, in `CONVENTIONS.md` § Legacy layout; the validator implements the same rule in code.
- **Routing by where the artifacts are**, not the project's age:
  - Artifacts already under `.sdlc/` → a full `/sdlc-init`.
  - Artifacts at a legacy path → `/sdlc-init` installs scaffolding and stops, to avoid a parallel tree. `/sdlc-adopt` then relocates the files with `git mv` and runs init's Phase 3b–5 on the relocated tree. Adopt is the last command.

## Consequences
### Positive
- Ordinary projects are never mistaken for legacy ones.
- A legacy project reaches a complete setup in two commands.
### Negative
- The rule has two implementations, prose and code, kept aligned by tests rather than by construction.
- `sdlc-adopt` is the longest skill (about 3.8k words).

## Implements Rules
- RULE-004 — Everything exists once

## Verification
- `tests/test_sdlc_validate.py`: `case_plain_docs_directory_is_not_legacy`, `case_ordinary_docs_architecture_is_not_legacy`, `case_docs_architecture_citing_the_scheme_is_legacy`, `case_legacy_steering_documents_are_detected`.
- `tests/test_skill_prompts.py`: `case_legacy_detection_rule_lives_in_one_place`, `case_adopt_is_the_last_command_of_the_legacy_journey`.

## References
- `.sdlc/CONVENTIONS.md` § Legacy layout · `skills/sdlc-adopt/SKILL.md` Mode A tail
