# ADR-003: The validator is one stdlib-only Python file, copied into each project

## Status
Accepted

## Context
The gate has to run in any project's CI, whatever its language, without a package install, and a project must keep passing when the plugin is uninstalled. A Spec Kit fork's 720-line gate was abandoned after its machinery outgrew what it enforced.

## Decision
`sdlc-validate.py` is a single file that imports only the standard library and supports Python 3.8+. `/sdlc-init` copies it to `.sdlc/tools/`, and each re-run replaces it (it is tooling, not content). Its exit code is the contract: 0 clean, 1 warnings under `--strict`, 2 errors. Every check is deterministic; there is no LLM in the gate.

## Consequences
### Positive
- CI needs one line: `python3 .sdlc/tools/sdlc-validate.py --strict`.
- The version a project runs is pinned in its own repo.
### Negative
- The single file is 1,755 lines. Keep the share that is actual checks (currently 22%) from shrinking.
- A project runs whatever copy it has until someone re-runs `/sdlc-init`.

## Implements Rules
- RULE-001 — Standard library only
- RULE-006 — No model in the gate

## Verification
- CI runs `bin/test.sh` on Python 3.8, including `compileall` over `skills/`.
- Every validator change adds a case to `tests/test_sdlc_validate.py`, seen to fail with the fix reverted.

## References
- `skills/sdlc-init/SKILL.md` Phase 2 (upgrade table) · `.sdlc/docs/product.md` § Alternatives & Positioning
