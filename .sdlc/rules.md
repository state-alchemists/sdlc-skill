# Project Rules — Constitution

*Dates: see `.sdlc/CONVENTIONS.md` § Dates and timestamps — run `date`, do not guess.*

> Immutable invariants. Every SDLC skill reads this file and refuses to violate it.
> Override process: see RULE-999 below. Do not edit rule statements without an Override Record.

## How to Use This File
- Every spec, design, test plan, and implementation must respect every rule below.
- `/sdlc-review` reports a `FAIL` for any code that violates a rule.
- To change a rule, follow the Override Process (RULE-999) and append (do not edit) an entry to the Override Log.

## Rules

### RULE-001 — Standard library only
| Field | Value |
|-------|-------|
| Category | Forbidden Patterns |
| Statement | NEVER import a third-party package in the validator, the eval runner, or the tests; they ALWAYS run on Python 3.8+. |
| Rationale | The validator is copied into projects of every language and must run in their CI with no install. |
| Enforcement | CI runs `bin/test.sh` on Python 3.8 with nothing installed; review. |
| Added | 2026-09-27 |

### RULE-002 — Portable bash
| Field | Value |
|-------|-------|
| Category | Required Patterns |
| Statement | Shell scripts ALWAYS run on bash 3.2: no associative arrays, and every `"${array[@]}"` expansion guarded against an empty array under `set -u`. |
| Rationale | bash 3.2 is the macOS default shell. |
| Enforcement | Review — CI runs a newer bash (see test-strategy.md, Known gap). |
| Added | 2026-09-27 |

### RULE-003 — A regression case per fix
| Field | Value |
|-------|-------|
| Category | Quality Gates |
| Statement | Every change to validator or eval-runner behaviour ALWAYS lands with a test case that was seen to fail with the change reverted. |
| Rationale | The validator is the only thing the project's central claim rests on; a check without a pinning case regresses silently. |
| Enforcement | Review checklist; `tests/test_sdlc_validate.py`, `tests/test_eval_runner.py`. |
| Added | 2026-09-27 |

### RULE-004 — Everything exists once
| Field | Value |
|-------|-------|
| Category | Required Patterns |
| Statement | Every shipped template, convention and script ALWAYS exists in exactly one file; skills reference `CONVENTIONS.md` instead of restating a rule, and this repository's `.sdlc/` links to the assets rather than copying them. |
| Rationale | Hand-synced copies drifted and shipped a false positive on every project with a `docs/architecture.md`. |
| Enforcement | `tests/test_skill_prompts.py` (`case_legacy_detection_rule_lives_in_one_place`); review. |
| Added | 2026-09-27 |

### RULE-005 — The installer removes only what it owns
| Field | Value |
|-------|-------|
| Category | Forbidden Patterns |
| Statement | The installer NEVER removes a skill directory this repository does not ship and never shipped, including a user's own `sdlc-*` skill. |
| Rationale | The `sdlc-*` namespace is shared with users' own skills; deleting one is data loss. |
| Enforcement | `tests/test_install.sh`. |
| Added | 2026-09-27 |

### RULE-006 — No model in the gate
| Field | Value |
|-------|-------|
| Category | Forbidden Patterns |
| Statement | NEVER let a language model decide a validator result, an eval grade, or the review verdict mapping. |
| Rationale | A gate must give the same answer twice; judgement belongs in a report a human reads. |
| Enforcement | Review; the verdict mapping is fixed text in `skills/sdlc-review/SKILL.md`. |
| Added | 2026-09-27 |

### RULE-007 — Naming
| Field | Value |
|-------|-------|
| Category | Coding Standards |
| Statement | Script names ALWAYS follow [kettanaito/naming-cheatsheet](https://github.com/kettanaito/naming-cheatsheet) (`get_`, `is_`, `has_`, `check_` prefixes; no abbreviations). |
| Rationale | Consistent names make the validator readable to contributors. |
| Enforcement | Review. |
| Added | 2026-09-27 |

### RULE-008 — The repository passes its own gate
| Field | Value |
|-------|-------|
| Category | Quality Gates |
| Statement | This repository ALWAYS passes `sdlc-validate.py --strict` over its own `.sdlc/specs/`. |
| Rationale | A traceability tool whose own code is untraced has no standing to require it of others. |
| Enforcement | `bin/test.sh` in CI. |
| Added | 2026-09-27 |

## Override Process — RULE-999
| Field | Value |
|-------|-------|
| Category | Process |
| Statement | A rule may only be overridden for a single change, recorded as an entry in the Override Log below, with the approver named. The rule statement itself is never edited. |
| Rationale | Prevents silent erosion of invariants. |
| Enforcement | Reviewers reject PRs that violate a rule without a matching Override Log entry. |

## Override Log

| Date | Rule | Scope (PR / commit) | Approver | Reason |
|------|------|---------------------|----------|--------|
