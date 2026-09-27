# SDLC AI Plugin — Test Strategy

## Testing Levels
| Level | Scope | Tool | Target |
|-------|-------|------|--------|
| Unit | Validator parsing and checks; eval runner lint and grading | `tests/test_sdlc_validate.py`, `tests/test_eval_runner.py` (stdlib, `tests/harness.py`) | One case per shipped bug, seen to fail with the fix reverted (RULE-003) |
| Static | Invariants over the skill prompts and templates | `tests/test_skill_prompts.py` | One case per prompt bug that shipped |
| Integration | Installer against a throwaway `$HOME` | `tests/test_install.sh` | Every install, sweep and uninstall path |
| Traceability | This repository's own specs against its code | `sdlc-validate.py --strict` | 0 errors, 0 warnings |
| E2E | A skill run graded against golden output | `evals/run.py --actual DIR` | Manual — a human produces the output; CI only lints the cases |

## Test Naming Convention
- Python: `case_<behaviour_stated_as_a_sentence>` (e.g. `case_tag_in_a_string_literal_is_not_a_tag`), collected in definition order by `tests/harness.py`; the docstring states the bug the case pins.
- Bash: one `pass "<behaviour>"` line per block in `tests/test_install.sh`.

## CI Gates
| Gate | Trigger | Command | Blocking |
|------|---------|---------|----------|
| Compile | Every push / PR | `python3 -m compileall -q skills evals tests zrb_init.py` (in `bin/test.sh`) | Yes |
| Unit, static, integration, eval lint | Every push / PR | `bin/test.sh` | Yes |
| Traceability | Every push / PR | `python3 skills/sdlc-init/assets/tools/sdlc-validate.py --strict` (in `bin/test.sh`) | Yes |

## Environments
| Env | URL | Deploy | Data |
|-----|-----|--------|------|
| Developer machine | — | `bin/install.sh` | Synthetic (temp directories) |
| GitHub Actions | — | Auto on push / PR | Synthetic (temp directories) |

## Quality Goals
- **Regression coverage**: every validator and eval-runner fix lands with a case that fails without it.
- **Traceability**: this repository passes its own `--strict` gate.
- **Known gap**: no unattended E2E — prompt regressions are caught only when a human runs a skill and grades it; `/sdlc-plan` and `/sdlc-review` have no golden case. CI runs bash 5, so the bash 3.2 floor (RULE-002) is checked by review only.
