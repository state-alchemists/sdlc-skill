# ADR-007: Assets ship once, inside sdlc-init, and become project-owned

## Status
Accepted

## Context
Skills that embed their own templates, or bundle copies of the validator, need a sync step and drift when someone forgets it. Teams also want their documents shaped their way without forking the plugin.

## Decision
- Every template, `CONVENTIONS.md`, `ANNOTATION.md`, `config.json` and the validator exist once, under `skills/sdlc-init/assets/`.
- `/sdlc-init` installs them into `.sdlc/`. Skills generate from `.sdlc/templates/` at run time and point to `CONVENTIONS.md` instead of restating its rules.
- On re-run, templates and `config.json` are **never** overwritten, the validator is **always** refreshed, and changes to `CONVENTIONS.md` and `ANNOTATION.md` are shown as a diff before replacing.

## Consequences
### Positive
- There is no sync step: edit a file and the change ships.
- Editing a template changes every later run, in that project only.
### Negative
- A project keeps an old template forever unless someone updates it by hand.
- On a first run `/sdlc-init` must read its own `assets/`, because `.sdlc/` does not exist yet.

## Implements Rules
- RULE-004 — Everything exists once

## Verification
- `tests/test_skill_prompts.py`: `case_legacy_detection_rule_lives_in_one_place`, `case_every_skill_reads_the_conventions`, `case_shipped_config_is_valid_json`, `case_templates_ask_for_a_date_not_a_date_format`.
- `tests/test_install.sh`: "upgrades over a previous version" checks that an installed `sdlc-init` carries `assets/tools/sdlc-validate.py`.

## References
- `README.md` § Contributing · `skills/sdlc-init/SKILL.md` Phase 2
