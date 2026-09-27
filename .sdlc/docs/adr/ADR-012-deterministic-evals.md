# ADR-012: Evals are deterministic checks, with no LLM judge

## Status
Accepted

## Context
The prompts are the product, so a prompt tweak can regress output without any code changing. Grading with an LLM costs money and gives different answers on different runs. Graders in the host tools are not available to CI.

## Decision
Each case in `evals/golden/<skill>/<case>/` carries:
- `input.md` — the inputs the skill receives;
- `rubric.md` — full criteria, graded by a human;
- `checks.json` (optional) — machine-checkable assertions: `file_exists`/`file_absent`, `contains_regex`/`absent_regex`, `min_matches`/`max_matches`.

`evals/run.py` lints every case in CI and grades an output directory on demand. Its lint rejects unknown keys and bad severities, and compiles every regex.

## Consequences
### Positive
- Runs anywhere with Python and no API key. Case structure is checked on every push.
### Negative
- Producing the output to grade still needs a human to run the skill, so prompt regressions are not caught unattended.
- Five cases cover five of seven skills; `/sdlc-plan` and `/sdlc-review` have none.

## Implements Rules
- RULE-001 — Standard library only
- RULE-006 — No model in the gate

## Verification
- `bin/test.sh` runs `python3 evals/run.py` (lint) in CI.

## References
- `evals/README.md`
