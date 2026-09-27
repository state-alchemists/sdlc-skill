# SDLC AI Plugin — Technology Overview

## Stack
| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language (skills, templates, docs) | Markdown with Agent Skills frontmatter; Mermaid diagrams | Agent Skills convention; Mermaid 11 | Loaded as-is by 30+ AI coding tools ([ADR-001](adr/ADR-001-chat-skills-not-a-cli.md)); diagrams render on GitHub and diff as text |
| Language (validator, eval runner, tests) | Python, standard library only | 3.8+ | Runs in any project's CI with no install ([ADR-003](adr/ADR-003-one-stdlib-validator-file.md), RULE-001) |
| Language (installer, test entry point) | Bash | 3.2+ | macOS default shell; no package manager needed (RULE-002) |
| CI/CD | GitHub Actions | `ubuntu-latest`, Python 3.8 | Runs `bin/test.sh` on every push to `main` and every pull request |

## Architecture Principles
1. **Everything exists once** — every shipped template, convention and script lives in exactly one file; skills reference `CONVENTIONS.md` instead of restating it (RULE-004, [ADR-007](adr/ADR-007-assets-ship-once-and-become-project-owned.md)).
2. **The gate is deterministic** — pass/fail is decided by parseable rules, never a model (RULE-006).
3. **Artifacts on disk are the state** — skills are stateless; chat history is never an input.
4. **Runtime-neutral skills** — describe what to do, never which tool to call.

## Constraints
- No third-party dependency in anything shipped or tested (RULE-001).
- The installer must never delete a skill this repository does not own (RULE-005).
- `.sdlc/` in this repository links to `skills/sdlc-init/assets/` rather than copying it, so the dogfooded layout does not create second copies.

## Dependencies
| Dependency | Purpose | License |
|------------|---------|---------|
| Python standard library | Validator, eval runner, tests | PSF |
| An AI coding tool that loads `SKILL.md` (zrb, Claude Code, …) | Runs the skills | per tool |
| `zrb` (optional) | `zrb skill test` / `zrb skill install` shortcuts in `zrb_init.py` | AGPL-3.0-or-later |
| `black` (maintainer tool, not enforced in CI) | Formatting of Python files | MIT |

## Property-Based Testing
- None configured.
