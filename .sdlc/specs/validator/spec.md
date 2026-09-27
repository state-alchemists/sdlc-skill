# Feature Spec: Traceability validator

**Feature Key:** VAL

`skills/sdlc-init/assets/tools/sdlc-validate.py` — installed into each project at `.sdlc/tools/`. Architecture: [ADR-002](../../docs/adr/ADR-002-traceability-lives-in-the-code.md), [ADR-003](../../docs/adr/ADR-003-one-stdlib-validator-file.md), [ADR-004](../../docs/adr/ADR-004-tags-count-only-in-real-comments-in-the-right-file.md).

## Requirements

- `REQ-001` (AC-001): IF an active, non-exempt requirement has no `IMPLEMENTS:` tag in a source file, THEN the validator SHALL report a `trace-code` ERROR.
- `REQ-002` (AC-001): IF an active, non-exempt requirement has no `COVERS:` tag in a test file, THEN the validator SHALL report a `trace-test` ERROR.
- `REQ-003` (AC-001): WHERE a requirement is listed under the exemption heading for its kind, the validator SHALL exempt it from `trace-code` and `trace-test` and report it as `outside-code` INFO.
- `REQ-004` (AC-001): IF `--feature` names a slug that has no spec, THEN the validator SHALL report an `unknown-feature` ERROR.
- `REQ-005` (AC-001): The validator SHALL exit with 2 when any ERROR is reported, with 1 when WARNINGs are reported under `--strict`, and with 0 otherwise.
- `REQ-006` (AC-001): WHILE tag-role enforcement is relaxed, the validator SHALL count a misplaced tag, report it as a WARNING, and report `gate-relaxed` as a WARNING.
- `REQ-007` (AC-002): IF a tag references a Feature Key or an ID that no spec defines as active, THEN the validator SHALL report a `dangling-tag` ERROR.
- `REQ-008` (AC-002): IF two specs declare the same Feature Key, or a spec has no usable Feature Key, THEN the validator SHALL report a `key-unique` or `feature-key` ERROR.
- `REQ-009` (AC-002): IF an ID is defined as active twice under one heading, or is both removed and active, THEN the validator SHALL report a `dup-id` or `recycled-id` ERROR.
- `REQ-010` (AC-003): IF a requirement cites an AC that the problem brief does not define, THEN the validator SHALL report an `ac-citation` ERROR.
- `REQ-011` (AC-003): WHEN the whole project is validated, the validator SHALL report each brief AC that no active requirement cites as `ac-uncited` INFO.
- `REQ-012` (AC-004): The validator SHALL count a tag only when the tag opens a real comment in the comment syntax of the file's extension.
- `REQ-013` (AC-004): The validator SHALL skip documentation, prose and data files when scanning for tags.
- `REQ-014` (AC-004): IF an `IMPLEMENTS:` tag sits in a test file or a `COVERS:` tag sits in a source file, THEN the validator SHALL report a `tag-role` ERROR and not count the tag.
- `REQ-015` (AC-007): The validator SHALL classify a file as a test by path component, path fragment or filename stem, and never by substring.
- `REQ-016` (AC-007): WHERE `.sdlc/config.json` declares layout, heading, comment or scan settings, the validator SHALL extend its defaults with them.
- `REQ-017` (AC-007): IF `.sdlc/config.json` is malformed, THEN the validator SHALL report a `config` ERROR naming the key.
- `REQ-018` (AC-008): WHEN an SDLC artifact sits at a legacy path, detected by exact file name or by content, the validator SHALL report `legacy-layout` INFO.
- `REQ-019` (AC-009): IF a requirement is not canonical uppercase EARS or contains an unverifiable term, THEN the validator SHALL report an `ears` WARNING.
- `REQ-020` (AC-001): IF a spec has no test plan, a plan row cites a removed or undefined ID, or a planned test id is covered by no test file, THEN the validator SHALL report the matching `missing-test-plan`, `plan-stale-row`, `plan-unknown-row` or `plan-test-uncovered` finding.
- `REQ-021` (AC-001): IF a scanned file is skipped, or a spec or brief has an unclosed code fence, THEN the validator SHALL report `skipped-file` or `unclosed-fence`.

## Non-Functional Requirements

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-001 | Runs on Python 3.8+ using only the standard library | no third-party import | test suite run on Python 3.8 with nothing installed |

## API Surface

| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| CLI | `sdlc-validate.py` | `[--root DIR] [--feature SLUG] [--strict] [--json] [--exclude GLOB]... [--relax-tag-roles]` | Findings as text, or `{"summary": {...}, "findings": [{severity, check, message, location}]}` with `--json` | none |

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| Any ERROR | exit 2 | findings, most severe first, then `N errors, M warnings, K info` |
| WARNINGs under `--strict` | exit 1 | same |
| Clean | exit 0 | same |

## Correctness

- **Uniqueness:** a Feature Key identifies exactly one spec, and an active ID is defined once per feature; violations are ERRORs, never silently merged.
- **Validation:** every value read from `.sdlc/config.json` is type-checked; an unusable value is an ERROR naming the key, never a silent fallback to defaults.

## Entities

See `.sdlc/requirements/entity-dictionary.md` — Feature (slug, feature_key), Requirement (id, status, exemption), PlannedTest (id, requirement_id), Tag (kind, target_id, file_path), AcceptanceCriterion (id).

## Test Plan

*Test naming convention: `case_<behaviour_stated_as_a_sentence>` in `tests/test_sdlc_validate.py` (see `.sdlc/docs/test-strategy.md`).*

### Unit Tests
| ID | Req | Test Name | Input | Expected |
|----|-----|-----------|-------|----------|
| UT-001 | REQ-001 | `case_implements_in_a_test_file_does_not_satisfy_code_coverage`, `case_requirement_mentioning_a_removed_thing_stays_active` | IMPLEMENTS only in a test file | `trace-code` |
| UT-002 | REQ-002 | `case_a_file_cannot_implement_and_cover_itself` | one file with both headers | `trace-test` |
| UT-003 | REQ-003 | `case_nfr_validated_by_infra_is_exempt`, `case_functional_requirement_without_in_code_verification_is_exempt`, `case_requirement_under_the_nfr_heading_warns_and_does_not_exempt`, `case_nfr_row_wording_alone_does_not_exempt` | exemption headings and a "Validated By" cell | exempt only under the right heading |
| UT-004 | REQ-004 | `case_unknown_feature_slug_errors` | `--feature user-mgmtt` | `unknown-feature` |
| UT-005 | REQ-005 | `case_exit_code_reflects_the_worst_finding` | untraced, warning-only, clean trees | exit 2 / 1 under `--strict` / 0 |
| UT-006 | REQ-006 | `case_relaxed_gate_counts_a_misplaced_tag_and_says_so`, `case_bad_gate_value_is_reported` | `--relax-tag-roles`; non-boolean gate | tag counts + `gate-relaxed`; `config` ERROR |
| UT-007 | REQ-007 | `case_unkeyed_tag_warns`, `case_genuinely_removed_requirement_is_retired` | unkeyed tag; tag on a removed ID | `unkeyed-tag`; `dangling-tag` |
| UT-008 | REQ-008 | `case_duplicate_feature_key_errors`, `case_slug_that_cannot_make_a_key_errors` | two specs one key; slug `2fa` | `key-unique`; `feature-key` |
| UT-009 | REQ-009 | `case_prose_mentioning_a_requirement_id_is_not_a_definition`, `case_fenced_example_in_a_spec_is_not_a_definition` | prose and fenced mentions | no false `dup-id` / `recycled-id` |
| UT-010 | REQ-010 | `case_unknown_ac_citation_errors`, `case_ac_citation_without_a_colon_is_checked` | citation of an undefined AC | `ac-citation` |
| UT-011 | REQ-011 | `case_acceptance_criterion_no_requirement_cites_is_reported` | uncited and removed-only-cited ACs | `ac-uncited` INFO, silent under `--feature` |
| UT-012 | REQ-012 | `case_tag_in_a_string_literal_is_not_a_tag`, `case_negated_mention_of_implements_is_not_a_tag`, `case_header_inside_a_python_docstring_does_not_count`, `case_apostrophe_inside_a_string_does_not_hide_the_comment` | tags in strings, prose, docstrings | only real comments count |
| UT-013 | REQ-013 | `case_markdown_examples_are_not_tags`, `case_tag_in_a_plain_text_file_is_not_a_tag` | tags in `.md` / `.txt` | not counted |
| UT-014 | REQ-014 | `case_covers_in_a_source_file_names_where_the_tag_actually_is` | COVERS in a source file | `tag-role`, path named in `trace-test` |
| UT-015 | REQ-015 | `case_colocated_go_test_is_classified_as_a_test`, `case_maven_layout_is_classified_correctly`, `case_browser_suite_is_classified_as_a_test`, `case_terraform_native_test_is_classified_as_a_test` | common layouts | classified as test |
| UT-016 | REQ-016 | `case_config_source_override_reclassifies_a_path`, `case_localised_heading_declared_in_config_resolves`, `case_generated_and_vendored_globs_are_accepted_and_skipped` | config overrides | defaults extended |
| UT-017 | REQ-017 | `case_malformed_config_is_reported_not_ignored` | invalid JSON | `config` ERROR |
| UT-018 | REQ-018 | `case_legacy_steering_documents_are_detected`, `case_ordinary_docs_architecture_is_not_legacy` | legacy files; plain `docs/architecture.md` | `legacy-layout` only for the former |
| UT-019 | REQ-019 | `case_lowercase_shall_is_flagged`, `case_vague_requirement_term_is_flagged`, `case_compound_requirement_is_flagged`, `case_canonical_ears_is_not_flagged_as_deprecated` | EARS variants | `ears` WARNING only for non-canonical |
| UT-020 | REQ-020 | `case_missing_test_plan_warns`, `case_planned_test_that_nothing_covers_warns`, `case_test_plan_row_for_a_removed_requirement_errors` | plan gaps | matching `plan-*` finding |
| UT-021 | REQ-021 | `case_oversized_file_skip_is_reported`, `case_unclosed_fence_in_a_spec_is_reported` | oversized file; unclosed fence | `skipped-file`; `unclosed-fence` |

### Integration Tests
N/A — the validator is a single file; every case above runs it end to end over a temporary project tree.

### End-to-End Tests
N/A — covered by the traceability gate over this repository in `bin/test.sh`.

### Property-Based Tests
N/A — no property-testing framework configured.

### Design Property Coverage
| Property | Covered By | Notes |
|----------|------------|-------|
| Uniqueness | UT-008, UT-009 | |
| Validation | UT-006, UT-017 | |

### Test Data Strategy
- **Fixtures**: built per case in a temporary directory by `get_findings` / `write_spec` in the test file.
- **Synthetic data**: a one-feature `user-mgmt` project with key `USERMGMT`.
- **Cleanup**: `shutil.rmtree` in a `finally` block.
