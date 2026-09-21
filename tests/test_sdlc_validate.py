#!/usr/bin/env python3
"""Regression tests for skills/sdlc-init/assets/tools/sdlc-validate.py.

Every case here is a bug the validator actually shipped, or a true positive that
a fix for one of them could plausibly break. Run it directly — no framework:

    python3 tests/test_sdlc_validate.py

Exit 0 means every case passed; a failed assertion names the case.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR_PATH = os.path.join(
    REPOSITORY_ROOT, "skills", "sdlc-init", "assets", "tools", "sdlc-validate.py"
)

DEFAULT_FEATURE_KEY = "USERMGMT"


def get_spec_header(feature_key):
    """Return the spec preamble, or just a title when the key is omitted."""
    title = "# Feature Spec: User Management\n\n"
    return (
        title
        if feature_key is None
        else ("%s**Feature Key:** %s\n\n" % (title, feature_key))
    )


def main():
    """Run every case, printing one line each, and return an exit code."""
    cases = [
        case_requirement_mentioning_a_removed_thing_stays_active,
        case_genuinely_removed_requirement_is_retired,
        case_canonical_ears_is_not_flagged_as_deprecated,
        case_deprecated_ears_is_still_flagged,
        case_nfr_validated_by_a_test_in_ci_is_enforced,
        case_nfr_validated_by_infra_is_exempt,
        case_folded_test_plan_ids_are_valid_targets,
        case_legacy_test_plan_ids_are_valid_targets,
        case_missing_test_plan_warns,
        case_unkeyed_tag_warns,
        case_duplicate_feature_key_errors,
        case_removed_requirement_keeping_its_citation_is_retired,
        case_nfr_row_wording_alone_does_not_exempt,
        case_lowercase_shall_is_flagged,
        case_lowercase_ears_keyword_is_flagged,
        case_feature_scope_leaves_other_features_alone,
        case_slug_that_cannot_make_a_key_errors,
        case_markdown_examples_are_not_tags,
        case_excluded_file_is_not_scanned,
        case_plain_docs_directory_is_not_legacy,
        case_legacy_steering_documents_are_detected,
        case_unknown_ac_citation_errors,
        case_known_ac_citation_is_accepted,
        case_planned_test_that_nothing_covers_warns,
        case_unknown_feature_slug_errors,
        case_a_file_cannot_implement_and_cover_itself,
        case_covers_in_a_source_file_names_where_the_tag_actually_is,
        case_implements_in_a_test_file_does_not_satisfy_code_coverage,
        case_colocated_go_test_is_classified_as_a_test,
        case_maven_layout_is_classified_correctly,
        case_tag_in_a_string_literal_is_not_a_tag,
        case_negated_mention_of_implements_is_not_a_tag,
        case_tag_in_a_plain_text_file_is_not_a_tag,
        case_unfenced_documentation_prose_is_not_a_tag,
        case_tag_in_a_block_comment_is_a_tag,
        case_missing_config_uses_built_in_defaults,
        case_malformed_config_is_reported_not_ignored,
        case_config_source_override_reclassifies_a_path,
        case_oversized_file_skip_is_reported,
        case_vague_requirement_term_is_flagged,
        case_compound_requirement_is_flagged,
        case_non_ears_leading_keyword_is_flagged,
        case_requirement_without_a_subject_is_flagged,
        case_canonical_composite_where_if_then_is_not_deprecated,
        case_ears_keyword_inside_quoted_copy_is_not_deprecated,
        case_fenced_example_in_a_spec_is_not_a_definition,
        case_prose_mentioning_a_requirement_id_is_not_a_definition,
        case_ac_citation_without_a_colon_is_checked,
        case_prose_mentioning_an_ac_does_not_define_it,
        case_test_plan_row_for_a_removed_requirement_errors,
        case_nested_code_fence_does_not_flip_parity,
        case_renamed_test_plan_heading_still_resolves,
        case_reworded_outside_code_heading_still_exempts,
        case_unbolded_feature_key_is_read,
        case_localised_heading_declared_in_config_resolves,
        case_ordinary_docs_architecture_is_not_legacy,
        case_docs_architecture_citing_the_scheme_is_legacy,
    ]
    failures = []
    for case in cases:
        try:
            case()
            print("PASS  %s" % case.__name__)
        except Exception as error:  # a crash is a failed case, not a lost run
            failures.append((case.__name__, error))
            print("FAIL  %s — %s: %s" % (case.__name__, type(error).__name__, error))

    print("\n%d case(s), %d failed" % (len(cases), len(failures)))
    return 1 if failures else 0


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------
def case_requirement_mentioning_a_removed_thing_stays_active():
    """A requirement whose prose contains "removed" is not a retired requirement."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): WHEN an admin deletes an account, the system "
            "SHALL revoke all sessions of the removed user."
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="dangling-tag"
    ), "a live requirement was retired, orphaning its tags"
    assert not has_finding(
        findings, check="trace-code"
    ), "coverage was silently skipped for a live requirement"


def case_genuinely_removed_requirement_is_retired():
    """`REQ-NNN: REMOVED (date) — reason` demands no implementation."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): The system SHALL hash passwords.",
            "- `REQ-002`: REMOVED (2026-01-11) — superseded by REQ-001.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    for check in ("trace-code", "trace-test", "plan-coverage", "ears"):
        assert not has_finding(findings, check=check, message="REQ-002"), (
            "a retired requirement still produced a %s finding" % check
        )


def case_canonical_ears_is_not_flagged_as_deprecated():
    """The English words "as" and "unless" inside canonical EARS are not keywords."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): IF a file is uploaded as a draft, THEN the "
            "system SHALL keep it private.",
            "- `REQ-002` (AC-002): The system SHALL reject a login unless the "
            "account is verified.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001, USERMGMT:REQ-002\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:REQ-002, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="ears"
    ), "canonical EARS was reported as the deprecated dialect"


def case_deprecated_ears_is_still_flagged():
    """Uppercase AS/THEN and ALWAYS SHALL remain deprecated-dialect warnings."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): AS the cache is cold, THEN the system SHALL warm it.",
            "- `REQ-002` (AC-002): The system ALWAYS SHALL log access.",
            "- `REQ-003` (AC-003): The system rejects bad input.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001, USERMGMT:REQ-002, USERMGMT:REQ-003\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:REQ-002, USERMGMT:REQ-003, "
        "USERMGMT:UT-001\n",
    )
    for requirement_id in ("REQ-001", "REQ-002", "REQ-003"):
        assert has_finding(findings, check="ears", message=requirement_id), (
            "%s should have been flagged" % requirement_id
        )


def case_nfr_validated_by_a_test_in_ci_is_enforced():
    """CI is where validation runs, not what performs it — no exemption."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Signup latency | p95 < 200ms | load test in CI |"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="trace-code", message="NFR-001"
    ), "an NFR validated by a test in CI was silently exempted"


def case_nfr_validated_by_infra_is_exempt():
    """An NFR listed under the outside-code heading needs no IMPLEMENTS/COVERS."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Backup retention | 30 days | infra policy |"],
        outside_code_nfrs=["- `NFR-001`: Backup retention — validated by infra policy"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="trace-code", message="NFR-001"
    ), "an infra-validated NFR was required to appear in code"
    assert has_finding(
        findings, check="outside-code", message="NFR-001"
    ), "the exemption was not reported"


def case_folded_test_plan_ids_are_valid_targets():
    """UT ids defined in the spec's own Test Plan resolve for COVERS tags."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="dangling-tag"
    ), "a UT id from the spec's Test Plan did not resolve"


def case_legacy_test_plan_ids_are_valid_targets():
    """A pre-merge project keeps its plan in a separate file; its ids still resolve."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=None,
        legacy_test_plan="| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n",
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="dangling-tag"
    ), "a UT id from a legacy test-plan.md did not resolve"
    assert has_finding(
        findings, check="legacy-test-plan"
    ), "the legacy test plan was not reported for migration"


def case_missing_test_plan_warns():
    """A spec with no plan anywhere is a warning, not silence."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=None,
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001\n",
    )
    assert has_finding(
        findings, check="missing-test-plan"
    ), "a spec with no test plan passed silently"


def case_unkeyed_tag_warns():
    """A pre-Feature-Key tag is tolerated, with a nudge to re-key it.

    Also under --feature: an unkeyed tag belongs to no feature, so scoping must
    not swallow the one warning that explains an otherwise untraced requirement.
    """
    for only_feature in (None, "user-mgmt"):
        findings = get_findings(
            requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
            source="# IMPLEMENTS: USERMGMT:REQ-001\n# @sdlc REQ-001\n",
            test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
            only_feature=only_feature,
        )
        assert has_finding(findings, check="unkeyed-tag"), (
            "an unkeyed tag was accepted without a warning (--feature %s)"
            % only_feature
        )


def case_duplicate_feature_key_errors():
    """Two features may not share a Feature Key — ids would collide."""
    with tempfile.TemporaryDirectory() as root:
        for slug in ("user-mgmt", "billing"):
            write_spec(
                root,
                slug,
                ["- `REQ-001` (AC-001): The system SHALL work."],
                nfr_rows=None,
                test_plan_rows=["| UT-001 | REQ-001 |"],
            )
        findings = run_validator(root)
    assert has_finding(
        findings, check="key-unique"
    ), "two specs sharing a Feature Key were accepted"


def case_removed_requirement_keeping_its_citation_is_retired():
    """`REQ-002 (AC-002): REMOVED ...` is the form the spec template produces."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): The system SHALL sign up users.",
            "- `REQ-002` (AC-002): REMOVED (2026-01-01) — superseded by REQ-001.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="trace-code", message="REQ-002"
    ), "a retired requirement that kept its AC citation was still required in code"
    assert not has_finding(
        findings, check="ears", message="REQ-002"
    ), "a retired requirement was checked for EARS syntax"


def case_nfr_row_wording_alone_does_not_exempt():
    """Words in the Validated By cell exempt nothing — only the heading does."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=[
            "| NFR-001 | Latency | p95 < 300ms | load test in the checkout process |"
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="trace-code", message="NFR-001"
    ), "an NFR was exempted by the word 'process' in its Validated By cell"


def case_lowercase_shall_is_flagged():
    """Uppercase is what makes a keyword a keyword."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): the system shall sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="ears", message="REQ-001"
    ), "a lowercase 'shall' passed as canonical EARS"


def case_lowercase_ears_keyword_is_flagged():
    """A lowercase leading keyword is prose, not an event-driven requirement."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): when a user signs up, the system SHALL email them."
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="ears", message="REQ-001"
    ), "a lowercase EARS keyword passed as canonical"


def case_feature_scope_leaves_other_features_alone():
    """--feature narrows findings; it must not dangle every other feature's tags."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_spec(
            root,
            "billing",
            ["- `REQ-001` (AC-002): The system SHALL charge cards."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
            feature_key="BILLING",
        )
        write_file(
            root, os.path.join("src", "users.py"), "# IMPLEMENTS: USERMGMT:REQ-001\n"
        )
        write_file(
            root,
            os.path.join("tests", "test_users.py"),
            "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        )
        write_file(
            root, os.path.join("src", "billing.py"), "# IMPLEMENTS: BILLING:REQ-001\n"
        )
        write_file(
            root,
            os.path.join("tests", "test_billing.py"),
            "# COVERS: BILLING:REQ-001, BILLING:UT-001\n",
        )
        findings = run_validator(root, only_feature="user-mgmt")
    assert not has_finding(
        findings, check="dangling-tag"
    ), "--feature reported another feature's tags as dangling"
    assert not has_finding(
        findings, check="trace-code"
    ), "--feature reported coverage errors outside the selected feature"


def case_slug_that_cannot_make_a_key_errors():
    """`2fa` -> `2FA` is not a valid key: tags could never resolve, so say so."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "2fa",
            ["- `REQ-001` (AC-001): The system SHALL verify codes."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
            feature_key=None,
        )
        findings = run_validator(root)
    assert has_finding(
        findings, check="feature-key", message="2FA"
    ), "a slug that cannot produce a valid Feature Key was accepted silently"


def case_markdown_examples_are_not_tags():
    """A fenced example in a README documents the format; it claims nothing."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(
            root, os.path.join("src", "users.py"), "# IMPLEMENTS: USERMGMT:REQ-001\n"
        )
        write_file(
            root,
            os.path.join("tests", "test_users.py"),
            "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        )
        write_file(
            root,
            "README.md",
            "Tag source files like this:\n\n"
            "```python\n# IMPLEMENTS: AUTH:REQ-042\n```\n",
        )
        findings = run_validator(root)
    assert not has_finding(
        findings, check="dangling-tag"
    ), "an example inside a fenced code block was read as a real tag"


def case_excluded_file_is_not_scanned():
    """--exclude covers the examples that live outside a code fence."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(
            root, os.path.join("src", "users.py"), "# IMPLEMENTS: USERMGMT:REQ-001\n"
        )
        write_file(
            root,
            os.path.join("tests", "test_users.py"),
            "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        )
        write_file(root, "AGENTS.md", "Tag files like IMPLEMENTS: AUTH:REQ-042\n")
        findings = run_validator(root, excluded_patterns=["AGENTS.md"])
    assert not has_finding(
        findings, check="dangling-tag"
    ), "an excluded file was still scanned for tags"


def case_plain_docs_directory_is_not_legacy():
    """Most projects have a docs/. It is evidence of nothing."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(root, os.path.join("docs", "index.md"), "# Our docs\n")
        write_file(root, os.path.join("docs", "ARCHITECTURE.md"), "# Ours too\n")
        findings = run_validator(root)
    assert not has_finding(
        findings, check="legacy-layout"
    ), "a project's own docs/ directory was reported as a legacy SDLC layout"


def case_legacy_steering_documents_are_detected():
    """The files /sdlc-init writes, at their pre-.sdlc/ path, are the real signal."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(root, os.path.join("docs", "product.md"), "# Product\n")
        findings = run_validator(root)
    assert has_finding(
        findings, check="legacy-layout", message="steering docs"
    ), "legacy steering documents were not reported"


def case_unknown_ac_citation_errors():
    """An AC renumbered upstream leaves specs citing an id that no longer exists."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-042): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n",
    )
    assert has_finding(
        findings, check="ac-citation", message="AC-042"
    ), "a requirement citing an AC the brief does not define was accepted"


def case_known_ac_citation_is_accepted():
    """The common case must stay silent, or the check is unusable."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n",
    )
    assert not has_finding(
        findings, check="ac-citation"
    ), "a valid AC citation was reported as unknown"


def case_planned_test_that_nothing_covers_warns():
    """A test plan row with no test behind it is a gap the validator can see."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=["| UT-001 | REQ-001 |", "| UT-002 | REQ-001 |"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="plan-test-uncovered", message="UT-002"
    ), "a planned test that no test file covers passed silently"


def case_unknown_feature_slug_errors():
    """A mistyped --feature used to exit 0, buying /sdlc-review a green APPROVE."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        findings = run_validator(root, only_feature="user-mgmtt")
    assert has_finding(
        findings, check="unknown-feature", message="user-mgmtt"
    ), "a --feature slug with no spec was not reported"
    assert has_severity(
        findings, "ERROR", check="unknown-feature"
    ), "an unknown --feature slug was reported below ERROR, so the gate still passes"
    assert has_finding(
        findings, check="unknown-feature", message="user-mgmt."
    ), "the error did not name the features that do exist"


# --- File roles: a tag only counts from the right kind of file ---------------


def case_a_file_cannot_implement_and_cover_itself():
    """The headline defect: one source file, both headers, and no tests at all
    used to validate clean and exit 0."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        test=None,
    )
    assert has_finding(
        findings, check="trace-test", message="USERMGMT:REQ-001"
    ), "a source file covering itself still satisfied test coverage"
    assert has_finding(
        findings, check="tag-role", message="COVERS"
    ), "a COVERS: tag in a source file was not reported"


def case_covers_in_a_source_file_names_where_the_tag_actually_is():
    """The coverage error cross-references the misplaced tag, so the two
    findings read as one story instead of two unrelated failures."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        test=None,
    )
    assert has_finding(
        findings, check="trace-test", message="src/users.py"
    ), "the coverage error did not name the file holding the misplaced tag"


def case_implements_in_a_test_file_does_not_satisfy_code_coverage():
    """Roles inverted: IMPLEMENTS in tests/, COVERS in src/, used to be clean."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        test="# IMPLEMENTS: USERMGMT:REQ-001\n",
    )
    assert has_finding(
        findings, check="trace-code", message="USERMGMT:REQ-001"
    ), "an IMPLEMENTS: header in a test file still satisfied code coverage"
    assert has_finding(
        findings, check="tag-role", message="IMPLEMENTS"
    ), "an IMPLEMENTS: tag in a test file was not reported"


def case_colocated_go_test_is_classified_as_a_test():
    """Go puts `auth_test.go` beside `auth.go` with no tests/ directory."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="// IMPLEMENTS: USERMGMT:REQ-001\n",
        test="// COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        source_path=os.path.join("internal", "auth", "auth.go"),
        test_path=os.path.join("internal", "auth", "auth_test.go"),
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "a Go source file outside src/ was not recognised as source"
    assert not has_finding(
        findings, check="trace-test"
    ), "a colocated Go _test.go file was not recognised as a test"
    assert not has_finding(
        findings, check="tag-role"
    ), "a correct Go layout produced a tag-role finding"


def case_maven_layout_is_classified_correctly():
    """src/test/java is a test tree even though it sits under src/."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="// IMPLEMENTS: USERMGMT:REQ-001\n",
        test="// COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        source_path=os.path.join("src", "main", "java", "Users.java"),
        test_path=os.path.join("src", "test", "java", "UsersTest.java"),
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "src/main/java was not recognised as source"
    assert not has_finding(
        findings, check="trace-test"
    ), "src/test/java was not recognised as a test tree"


# --- Comment awareness: a tag only counts inside a real comment --------------


def case_tag_in_a_string_literal_is_not_a_tag():
    """`MSG = "IMPLEMENTS: ..."` is data, not a traceability claim."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source='MSG = "IMPLEMENTS: USERMGMT:REQ-001"\n',
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="trace-code", message="USERMGMT:REQ-001"
    ), "a tag inside a string literal still satisfied code coverage"


def case_negated_mention_of_implements_is_not_a_tag():
    """A comment ABOUT the format is not a claim. The tag must open its comment."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# This file does NOT IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(
        findings, check="trace-code", message="USERMGMT:REQ-001"
    ), "prose mentioning IMPLEMENTS: mid-sentence still claimed coverage"


def case_tag_in_a_plain_text_file_is_not_a_tag():
    """notes.txt is not code. It used to satisfy both checks on its own."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source=None,
        test=None,
        extra_files={
            "notes.txt": "IMPLEMENTS: USERMGMT:REQ-001\n"
            "COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n"
        },
    )
    assert has_finding(
        findings, check="trace-code", message="USERMGMT:REQ-001"
    ), "a plain text file satisfied code coverage"
    assert has_finding(
        findings, check="trace-test", message="USERMGMT:REQ-001"
    ), "a plain text file satisfied test coverage"


def case_unfenced_documentation_prose_is_not_a_tag():
    """Documentation shows the format; it never claims coverage, fenced or not."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        extra_files={"README.md": "Write IMPLEMENTS: AUTH:REQ-042 at the top.\n"},
    )
    assert not has_finding(
        findings, check="dangling-tag"
    ), "un-fenced prose in a README was read as a real tag"


def case_tag_in_a_block_comment_is_a_tag():
    """The true-positive guard: /* */ and <!-- --> are real comments."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="/*\n * IMPLEMENTS: USERMGMT:REQ-001\n */\n",
        test="// COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        source_path=os.path.join("src", "users.ts"),
        test_path=os.path.join("src", "users.test.ts"),
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "a tag inside a /* */ block comment was not counted"
    assert not has_finding(
        findings, check="trace-test"
    ), "a // tag in a colocated .test.ts file was not counted"


# --- Project configuration ---------------------------------------------------


def case_missing_config_uses_built_in_defaults():
    """A project that has never seen .sdlc/config.json validates silently."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="config"
    ), "an absent config produced a finding; defaults must be silent"


def case_malformed_config_is_reported_not_ignored():
    """Silently ignoring a layout declaration would report real tags as missing."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        config="{not json at all",
    )
    assert has_finding(
        findings, check="config", message="not valid JSON"
    ), "a malformed config.json was silently ignored"


def case_config_source_override_reclassifies_a_path():
    """A `testing/` package holds helpers, not tests. The project says so."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        source_path=os.path.join("src", "testing", "fixtures.py"),
        config={"layout": {"source_overrides": ["src/testing/*"]}},
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "layout.source_overrides did not reclassify the path as source"
    assert not has_finding(
        findings, check="tag-role"
    ), "an overridden path still reported a tag-role finding"


def case_oversized_file_skip_is_reported():
    """A silently skipped file made a real tag vanish with no explanation."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n" + ("# pad\n" * 200),
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        config={"scan": {"max_file_bytes": 64}},
    )
    assert has_finding(
        findings, check="skipped-file", message="src/users.py"
    ), "an oversized file was skipped without saying so"


# --- EARS: false negatives the SHALL-grep let through ------------------------


def case_vague_requirement_term_is_flagged():
    """ "fast and user-friendly" is exactly what sdlc-plan Phase 2 forbids."""
    findings = get_ears_findings("The system SHALL be fast and user-friendly.")
    assert has_finding(
        findings, check="ears", message="unverifiable term"
    ), "an untestable requirement passed the EARS check"


def case_compound_requirement_is_flagged():
    """One requirement, one SHALL — that is what EARS is for."""
    findings = get_ears_findings(
        "WHEN a user signs up, the system SHALL send mail and SHALL log it "
        "and SHALL bill them."
    )
    assert has_finding(
        findings, check="ears", message="SHALL clauses"
    ), "three requirements crammed into one line passed the EARS check"


def case_non_ears_leading_keyword_is_flagged():
    """AFTER looks like a keyword and is not one."""
    findings = get_ears_findings(
        "AFTER the user logs in, the system SHALL redirect to the dashboard."
    )
    assert has_finding(
        findings, check="ears", message="not an EARS keyword"
    ), "a non-EARS opening keyword passed"
    assert has_finding(
        findings, check="ears", message="use WHEN"
    ), "the migration hint for AFTER was not offered"


def case_requirement_without_a_subject_is_flagged():
    """A bare SHALL names nobody and demands nothing."""
    findings = get_ears_findings("SHALL")
    assert has_finding(
        findings, check="ears", message="no subject before SHALL"
    ), "a requirement with no subject passed"


# --- EARS: false positives that trained users to ignore warnings -------------


def case_canonical_composite_where_if_then_is_not_deprecated():
    """CONVENTIONS.md endorses this shape; the validator used to flag it."""
    findings = get_ears_findings(
        "WHERE the audit module is included, IF the record is deleted, THEN "
        "the system SHALL write an audit row."
    )
    assert not has_finding(
        findings, check="ears"
    ), "the canonical WHERE/IF/THEN composite was flagged as deprecated"


def case_ears_keyword_inside_quoted_copy_is_not_deprecated():
    """UNLESS inside UI copy is a string the system emits, not a keyword."""
    findings = get_ears_findings(
        "WHEN validation fails, the system SHALL display "
        '"Access denied UNLESS you verify your email".'
    )
    assert not has_finding(
        findings, check="ears"
    ), "an EARS keyword inside quoted copy was read as the deprecated dialect"


# --- Spec parsing ------------------------------------------------------------


def case_fenced_example_in_a_spec_is_not_a_definition():
    """A spec that SHOWS the REMOVED form is documenting it, not using it."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): The system SHALL sign up users.",
            "",
            "How to retire a requirement:",
            "",
            "```",
            "- `REQ-001` (AC-001): REMOVED (2026-01-01) — example only",
            "```",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="recycled-id"
    ), "a fenced example retired the real requirement"


def case_prose_mentioning_a_requirement_id_is_not_a_definition():
    """`- REQ-001 was the hardest one` defines nothing."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): The system SHALL sign up users.",
            "",
            "### Notes",
            "- REQ-001 was the hardest one to get right.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="dup-id"
    ), "a prose bullet mentioning an ID was read as a second definition"


def case_ac_citation_without_a_colon_is_checked():
    """A missing colon used to disable the citation check silently."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-042) The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n",
    )
    assert has_finding(
        findings, check="ac-citation", message="AC-042"
    ), "a citation on a colon-less line was never checked"


def case_prose_mentioning_an_ac_does_not_define_it():
    """`- AC-777 was DELETED in March` is not a definition."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-777): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n"
        "\n## Changelog\n- AC-777 was DELETED in March.\n",
    )
    assert has_finding(
        findings, check="ac-citation", message="AC-777"
    ), "an AC the brief merely mentions was accepted as defined"


def case_test_plan_row_for_a_removed_requirement_errors():
    """A row planning a retired requirement is dead weight that reads as real."""
    findings = get_findings(
        requirements=[
            "- `REQ-001` (AC-001): The system SHALL sign up users.",
            "- `REQ-002` (AC-001): REMOVED (2026-01-01) — dropped.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001, USERMGMT:UT-002\n",
        test_plan_rows=["| UT-001 | REQ-001 |", "| UT-002 | REQ-002 |"],
    )
    assert has_finding(
        findings, check="plan-stale-row", message="REQ-002"
    ), "a test-plan row for a REMOVED requirement was not reported"


def case_nested_code_fence_does_not_flip_parity():
    """Documenting Markdown inside Markdown used to hide the rest of the file."""
    findings = get_findings(
        requirements=[
            "````markdown",
            "```",
            "````",
            "",
            "- `REQ-001` (AC-001): The system SHALL sign up users.",
        ],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "a nested fence swallowed the requirements that followed it"


# --- Templates are project-owned: headings may be renamed --------------------


def case_renamed_test_plan_heading_still_resolves():
    """The README invites editing templates; a rename must not break parsing."""
    findings = get_spec_text_findings(
        "# Feature Spec: Demo\n\n**Feature Key:** USERMGMT\n\n"
        "## Requirements\n\n- `REQ-001` (AC-001): The system SHALL sign up users.\n"
        "\n## Tests\n\n| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n"
    )
    assert not has_finding(
        findings, check="missing-test-plan"
    ), "a renamed test-plan heading was not recognised"
    assert not has_finding(
        findings, check="dangling-tag"
    ), "a renamed test-plan heading turned its UT ids into dangling tags"


def case_reworded_outside_code_heading_still_exempts():
    """The exemption is the meaning of the heading, not its exact wording."""
    findings = get_spec_text_findings(
        "# Feature Spec: Demo\n\n**Feature Key:** USERMGMT\n\n"
        "## Requirements\n\n- `REQ-001` (AC-001): The system SHALL sign up users.\n"
        "\n| ID | Requirement | Target | Validated By |\n|--|--|--|--|\n"
        "| NFR-001 | TLS everywhere | 1.3 | terraform |\n"
        "\n## NFRs Validated Outside Code by Infrastructure\n"
        "- `NFR-001`: TLS everywhere — terraform\n"
        "\n## Test Plan\n\n| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n"
    )
    assert not has_finding(
        findings, check="dup-id"
    ), "re-listing an NFR under a reworded heading produced a duplicate-id error"
    assert not has_finding(
        findings, check="trace-code", message="NFR-001"
    ), "a reworded exemption heading lost the NFR exemption"


def case_unbolded_feature_key_is_read():
    """Dropping the asterisks still declares a key; it used to vanish silently."""
    findings = get_spec_text_findings(
        "# Feature Spec: Demo\n\nFeature Key: PAYMENTS\n\n"
        "## Requirements\n\n- `REQ-001` (AC-001): The system SHALL sign up users.\n"
        "\n## Test Plan\n\n| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n",
        source="# IMPLEMENTS: PAYMENTS:REQ-001\n",
        test="# COVERS: PAYMENTS:REQ-001, PAYMENTS:UT-001\n",
    )
    assert not has_finding(
        findings, check="trace-code"
    ), "an unbolded Feature Key was ignored and the key defaulted to the slug"


def case_localised_heading_declared_in_config_resolves():
    """A non-English team renames the heading and says so in config.json."""
    findings = get_spec_text_findings(
        "# Feature Spec: Demo\n\n**Feature Key:** USERMGMT\n\n"
        "## Requirements\n\n- `REQ-001` (AC-001): The system SHALL sign up users.\n"
        "\n## Rencana Pengujian\n\n| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n",
        config={"headings": {"test_plan": ["Rencana Pengujian"]}},
    )
    assert not has_finding(
        findings, check="missing-test-plan"
    ), "a test-plan heading declared in config.json was not recognised"


def case_ordinary_docs_architecture_is_not_legacy():
    """MkDocs, Docusaurus and Diataxis all emit docs/architecture.md. Treating it
    as a marker made /sdlc-init refuse to write steering docs on virgin projects."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(root, "mkdocs.yml", "site_name: Our Project\n")
        write_file(root, os.path.join("docs", "index.md"), "# Welcome\n")
        write_file(
            root,
            os.path.join("docs", "architecture.md"),
            "# How our system is put together\n\nWe use a queue.\n",
        )
        findings = run_validator(root)
    assert not has_finding(
        findings, check="legacy-layout"
    ), "an ordinary project's docs/architecture.md was reported as a legacy layout"


def case_docs_architecture_citing_the_scheme_is_legacy():
    """The true-positive guard: a weak name counts when its text corroborates it."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(
            root,
            "user-mgmt",
            ["- `REQ-001` (AC-001): The system SHALL sign up users."],
            nfr_rows=None,
            test_plan_rows=["| UT-001 | REQ-001 |"],
        )
        write_file(
            root,
            os.path.join("docs", "architecture.md"),
            "# Architecture\n\nKey decisions: see ADR-0007 for the database.\n",
        )
        findings = run_validator(root)
    assert has_finding(
        findings, check="legacy-layout", message="steering docs"
    ), "a legacy architecture.md that cites an ADR was not detected"


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------
def get_ears_findings(requirement):
    """Return the findings for a project whose single requirement is `requirement`."""
    return get_findings(
        requirements=["- `REQ-001` (AC-001): %s" % requirement],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )


def get_spec_text_findings(spec_text, source=None, test=None, config=None):
    """Return the findings for a project whose spec.md is written out verbatim."""
    root = tempfile.mkdtemp()
    try:
        write_file(
            root, os.path.join(".sdlc", "specs", "user-mgmt", "spec.md"), spec_text
        )
        if config is not None:
            write_file(root, os.path.join(".sdlc", "config.json"), json.dumps(config))
        write_file(
            root,
            os.path.join("src", "users.py"),
            source or "# IMPLEMENTS: USERMGMT:REQ-001\n",
        )
        write_file(
            root,
            os.path.join("tests", "test_users.py"),
            test or "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        )
        return run_validator(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def get_findings(
    requirements,
    source,
    test,
    nfr_rows=None,
    test_plan_rows=("| UT-001 | REQ-001 |",),
    legacy_test_plan=None,
    outside_code_nfrs=None,
    problem_brief=None,
    only_feature=None,
    extra_files=None,
    config=None,
    source_path=None,
    test_path=None,
):
    """Build a one-feature project in a temp dir and return the validator findings.

    `source_path`/`test_path` place the tagged files somewhere other than the
    default `src/users.py` and `tests/test_users.py`, which is how the file-role
    classification is exercised across real-world layouts.
    """
    root = tempfile.mkdtemp()
    try:
        write_spec(
            root,
            "user-mgmt",
            requirements,
            nfr_rows,
            test_plan_rows,
            outside_code_nfrs=outside_code_nfrs,
        )
        if problem_brief:
            write_file(
                root,
                os.path.join(".sdlc", "requirements", "problem-brief.md"),
                problem_brief,
            )
        if legacy_test_plan:
            write_file(
                root,
                os.path.join(".sdlc", "tests", "user-mgmt", "test-plan.md"),
                legacy_test_plan,
            )
        if config is not None:
            write_file(
                root,
                os.path.join(".sdlc", "config.json"),
                config if isinstance(config, str) else json.dumps(config),
            )
        if source is not None:
            write_file(
                root,
                source_path or os.path.join("src", "users.py"),
                source + "def signup(): pass\n",
            )
        if test is not None:
            write_file(
                root,
                test_path or os.path.join("tests", "test_users.py"),
                test + "def test_signup(): pass\n",
            )
        for relative_path, content in sorted((extra_files or {}).items()):
            write_file(root, relative_path, content)
        return run_validator(root, only_feature=only_feature)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def write_spec(
    root,
    slug,
    requirements,
    nfr_rows,
    test_plan_rows,
    outside_code_nfrs=None,
    feature_key=DEFAULT_FEATURE_KEY,
):
    """Write a spec.md for one feature, with optional NFR table and test plan."""
    sections = [
        get_spec_header(feature_key),
        "## Requirements\n\n",
        "\n".join(requirements),
        "\n\n",
    ]
    if nfr_rows:
        sections += [
            "## Non-Functional Requirements\n\n",
            "| ID | Requirement | Target | Validated By |\n",
            "|----|-------------|--------|--------------|\n",
            "\n".join(nfr_rows),
            "\n\n",
        ]
    if outside_code_nfrs:
        sections += [
            "## NFRs Validated Outside Code\n\n",
            "\n".join(outside_code_nfrs),
            "\n\n",
        ]
    if test_plan_rows:
        sections += [
            "## Test Plan\n\n### Unit Tests\n",
            "| ID | Req |\n|----|-----|\n",
            "\n".join(test_plan_rows),
            "\n",
        ]
    write_file(root, os.path.join(".sdlc", "specs", slug, "spec.md"), "".join(sections))


def write_file(root, relative_path, content):
    """Write one file, creating its parent directories."""
    path = os.path.join(root, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        file_handle.write(content)


def run_validator(root, only_feature=None, excluded_patterns=()):
    """Validate the project at `root` and return its findings."""
    return (
        load_validator()
        .validate_project(
            root, only_feature=only_feature, excluded_patterns=excluded_patterns
        )
        .findings
    )


def has_finding(findings, check=None, message=None):
    """Return True when a finding matches the given check name and message fragment."""
    for _, finding_check, finding_message, _ in findings:
        if check and finding_check != check:
            continue
        if message and message not in finding_message:
            continue
        return True
    return False


def has_severity(findings, severity, check=None):
    """Return True when a finding of this severity (and optionally check) exists."""
    for finding_severity, finding_check, _, _ in findings:
        if finding_severity != severity:
            continue
        if check and finding_check != check:
            continue
        return True
    return False


def load_validator():
    """Import the validator by path — its filename is not a valid module name."""
    module_spec = importlib.util.spec_from_file_location(
        "sdlc_validate", VALIDATOR_PATH
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    sys.exit(main())
