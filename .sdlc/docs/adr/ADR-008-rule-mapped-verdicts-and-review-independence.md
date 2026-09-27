# ADR-008: Review verdicts are mapped by rule and capped without independence

## Status
Accepted

## Context
An LLM's opinion is not reproducible, so it cannot gate a merge. An APPROVE from the session that wrote the code is a false pass. So is an APPROVE with no validator run, or one against a mistyped `--feature` slug.

## Decision
`/sdlc-review` runs the validator first, then a fresh-context sub-agent for what a parser cannot judge: correctness, entity fidelity, ADR and rule compliance, test coverage. The verdict is mapped by rule:
- **REQUEST CHANGES** — any validator ERROR, FAIL check, or rule violation without an Override Log entry.
- **COMMENT** — only warnings or PARTIALs.
- **APPROVE** — everything clean.

Before reading anything, the review asks whether this session wrote the implementation (via implement, quickfix or adopt Mode C, or a `/save`/`/load` resume). If so, or if the user cannot rule it out, the verdict is **capped at COMMENT**. Falling back to grep because the validator is missing also caps it. An unknown `--feature` slug is a validator ERROR.

## Consequences
### Positive
- The same inputs give the same verdict, and APPROVE means something.
### Negative
- It costs a fresh session per review. That is the only phase where freshness is required.
- The judgement pass is still a model's output, audited by spot-checks rather than proof.

## Implements Rules
- RULE-006 — No model in the gate

## Verification
- `tests/test_skill_prompts.py`: `case_review_asks_for_independence_confirmation`, `case_review_caps_verdict_without_fresh_context`, `case_review_handoffs_reference_the_rule`.
- `tests/test_sdlc_validate.py`: `case_unknown_feature_slug_errors`, `case_feature_scope_leaves_other_features_alone`.

## References
- `.sdlc/CONVENTIONS.md` § Review independence · `skills/sdlc-review/SKILL.md`
