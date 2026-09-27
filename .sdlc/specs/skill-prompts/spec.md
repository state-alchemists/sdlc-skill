# Feature Spec: Skill prompts

**Feature Key:** SKILL

The seven `skills/sdlc-*/SKILL.md` files, and the conventions and templates they ship. Architecture: [ADR-001](../../docs/adr/ADR-001-chat-skills-not-a-cli.md), [ADR-007](../../docs/adr/ADR-007-assets-ship-once-and-become-project-owned.md), [ADR-008](../../docs/adr/ADR-008-rule-mapped-verdicts-and-review-independence.md), [ADR-010](../../docs/adr/ADR-010-legacy-detection-by-content.md), [ADR-011](../../docs/adr/ADR-011-single-delegation-that-cannot-edit-the-spec.md).

## Requirements

- `REQ-001` (AC-005): The skills SHALL write a file only after the user gives an explicit affirmative at the approval tier that `CONVENTIONS.md` assigns to it.
- `REQ-002` (AC-005): The `sdlc-implement` skill SHALL forbid its coding sub-agent from modifying `.sdlc/` and verify that with `git diff --name-only -- .sdlc/`.
- `REQ-003` (AC-006): WHEN `sdlc-review` starts, the skill SHALL ask whether this session wrote the implementation before reading any file.
- `REQ-004` (AC-006): IF a review runs in the session that wrote the implementation, THEN the skills SHALL cap its verdict at COMMENT.
- `REQ-005` (AC-007): The skills SHALL read the project's source and test layout instead of assuming `src/` and `tests/`.
- `REQ-006` (AC-007): The shipped `config.json` SHALL parse as JSON with every section present and tag-role enforcement on.
- `REQ-007` (AC-008): The skills SHALL state the legacy-layout rule only in `CONVENTIONS.md`, which `sdlc-init` and `sdlc-adopt` reference.
- `REQ-008` (AC-008): WHEN a project is on a legacy layout, the skills SHALL route it through `/sdlc-init` then `/sdlc-adopt`, with `/sdlc-adopt` completing the setup.
- `REQ-009` (AC-010): WHEN `sdlc-init` re-runs, the skill SHALL never overwrite the project's templates or `config.json`.
- `REQ-010` (AC-010): The templates SHALL ask for dates as values to obtain and contain only diagrams that parse as Mermaid.
- `REQ-011` (AC-011): Every skill SHALL read `.sdlc/CONVENTIONS.md` and end with an action block that follows its Session handoff section.
- `REQ-012` (AC-004): The skills that write code SHALL read `.sdlc/ANNOTATION.md`, which covers every placement hazard that broke a file.
- `REQ-013` (AC-004): The skills SHALL use `SPEC:` as the only spec header token.

## Requirements With No In-Code Verification
*These requirements are implemented in Markdown, which the validator never scans (ADR-004), so no file can carry their `IMPLEMENTS:` tag — the framework has no way yet to trace a requirement into a prompt. All but REQ-001 are still verified: `tests/test_skill_prompts.py` carries `COVERS:` for them, and the Test Plan below maps each one. REQ-001 depends on the host model following instructions and has no executable check at all.*

- `REQ-001`: explicit approval before writing — relies on the host model; no runtime gate exists (ADR-001).
- `REQ-002`: sub-agent may not edit `.sdlc/` — in Markdown; verified by UT-001.
- `REQ-003`: independence question first — in Markdown; verified by UT-002.
- `REQ-004`: in-session verdict capped at COMMENT — in Markdown; verified by UT-003.
- `REQ-005`: no hardcoded layout — in Markdown; verified by UT-004.
- `REQ-006`: shipped config valid — JSON cannot carry a comment; verified by UT-005.
- `REQ-007`: legacy rule stated once — in Markdown; verified by UT-006.
- `REQ-008`: legacy journey ends at `/sdlc-adopt` — in Markdown; verified by UT-007.
- `REQ-009`: templates and config never overwritten — in Markdown; verified by UT-008.
- `REQ-010`: dates and diagrams in templates — in Markdown; verified by UT-009.
- `REQ-011`: conventions read, action blocks — in Markdown; verified by UT-010.
- `REQ-012`: annotation reference — in Markdown; verified by UT-011.
- `REQ-013`: one header token — in Markdown; verified by UT-012.

## API Surface

| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| Slash command | `/sdlc-init`, `/sdlc-plan`, `/sdlc-spec <feature>`, `/sdlc-implement <feature>`, `/sdlc-review <feature>`, `/sdlc-quickfix <feature>`, `/sdlc-adopt` | free-text argument, interview answers, approvals | files under `.sdlc/` and the project's source and tests, then an action block | the user's approval per tier |

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| Required input missing (no scaffolding, no spec, no brief) | stop | names the skill to run first |
| Retry cap reached (`sdlc-implement`, `sdlc-quickfix`) | stop | what failed, what was tried |

## Correctness

- **Validation:** every skill checks its required inputs exist before generating, and runs the validator before handing off.

## Entities

See `.sdlc/requirements/entity-dictionary.md` — the skills create every entity in it.

## Test Plan

*Test naming convention: `case_<behaviour_stated_as_a_sentence>` in `tests/test_skill_prompts.py` — static checks over the prompt text, not behaviour.*

### Unit Tests
| ID | Req | Test Name | Input | Expected |
|----|-----|-----------|-------|----------|
| UT-001 | REQ-002 | `case_implement_forbids_editing_the_spec` | `sdlc-implement/SKILL.md` | prohibition and `git diff` check present |
| UT-002 | REQ-003 | `case_review_asks_for_independence_confirmation` | `sdlc-review/SKILL.md` | question names every contamination source |
| UT-003 | REQ-004 | `case_review_caps_verdict_without_fresh_context`, `case_review_handoffs_reference_the_rule` | review, implement, quickfix skills; report template | cap stated; handoffs reference the rule |
| UT-004 | REQ-005 | `case_no_skill_hardcodes_the_source_or_test_layout` | every skill | no bare `src/`/`tests/` outside examples |
| UT-005 | REQ-006 | `case_shipped_config_is_valid_json` | `assets/config.json` | parses; gate on |
| UT-006 | REQ-007 | `case_legacy_detection_rule_lives_in_one_place` | CONVENTIONS, init, adopt | one copy, two references |
| UT-007 | REQ-008 | `case_adopt_is_the_last_command_of_the_legacy_journey` | init, adopt, README | no second `/sdlc-init` |
| UT-008 | REQ-009 | `case_init_never_overwrites_project_owned_files` | `sdlc-init/SKILL.md` | "Never overwrite" rows present |
| UT-009 | REQ-010 | `case_templates_ask_for_a_date_not_a_date_format`, `case_template_diagrams_parse_as_mermaid` | templates | no date formats; no unparseable placeholders |
| UT-010 | REQ-011 | `case_every_skill_reads_the_conventions`, `case_every_transition_is_an_action_block` | every skill | both present |
| UT-011 | REQ-012 | `case_writing_skills_read_the_annotation_reference`, `case_annotation_covers_every_hazard_that_broke_a_file` | writing skills; ANNOTATION.md | reference and hazards present |
| UT-012 | REQ-013 | `case_no_skill_still_says_generated_from_spec` | every skill | old token absent |

### Integration Tests
N/A — behaviour is graded by the golden evals in `evals/golden/`, not by CI.

### End-to-End Tests
N/A — see test-strategy.md, Known gap.

### Property-Based Tests
N/A — no property-testing framework configured.

### Design Property Coverage
| Property | Covered By | Notes |
|----------|------------|-------|
| Validation | UT-004, UT-008 | static only |

### Test Data Strategy
- **Fixtures**: the real skill, template and convention files in this repository.
- **Synthetic data**: none.
- **Cleanup**: none — read-only.
