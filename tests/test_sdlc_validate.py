#!/usr/bin/env python3
"""Regression tests for skills/sdlc-init/assets/tools/sdlc-validate.py.

Every case here is a bug the validator actually shipped, or a true positive that
a fix for one of them could plausibly break. Run it directly — no framework:

    python3 tests/test_sdlc_validate.py

Exit 0 means every case passed; a failed assertion names the case.
"""

import importlib.util
import os
import shutil
import sys
import tempfile

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR_PATH = os.path.join(
    REPOSITORY_ROOT, "skills", "sdlc-init", "assets", "tools", "sdlc-validate.py")

DEFAULT_FEATURE_KEY = "USERMGMT"


def get_spec_header(feature_key):
    """Return the spec preamble, or just a title when the key is omitted."""
    title = "# Feature Spec: User Management\n\n"
    return title if feature_key is None else (
        "%s**Feature Key:** %s\n\n" % (title, feature_key))


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
    ]
    failures = []
    for case in cases:
        try:
            case()
            print("PASS  %s" % case.__name__)
        except Exception as error:  # a crash is a failed case, not a lost run
            failures.append((case.__name__, error))
            print("FAIL  %s — %s: %s"
                  % (case.__name__, type(error).__name__, error))

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
    assert not has_finding(findings, check="dangling-tag"), \
        "a live requirement was retired, orphaning its tags"
    assert not has_finding(findings, check="trace-code"), \
        "coverage was silently skipped for a live requirement"


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
    assert not has_finding(findings, message="REQ-002"), \
        "a retired requirement was still required to be implemented"


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
    assert not has_finding(findings, check="ears"), \
        "canonical EARS was reported as the deprecated dialect"


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
        assert has_finding(findings, check="ears", message=requirement_id), \
            "%s should have been flagged" % requirement_id


def case_nfr_validated_by_a_test_in_ci_is_enforced():
    """CI is where validation runs, not what performs it — no exemption."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Signup latency | p95 < 200ms | load test in CI |"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="trace-code", message="NFR-001"), \
        "an NFR validated by a test in CI was silently exempted"


def case_nfr_validated_by_infra_is_exempt():
    """An NFR listed under the outside-code heading needs no IMPLEMENTS/COVERS."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Backup retention | 30 days | infra policy |"],
        outside_code_nfrs=["- `NFR-001`: Backup retention — validated by infra policy"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(findings, check="trace-code", message="NFR-001"), \
        "an infra-validated NFR was required to appear in code"
    assert has_finding(findings, check="outside-code", message="NFR-001"), \
        "the exemption was not reported"


def case_folded_test_plan_ids_are_valid_targets():
    """UT ids defined in the spec's own Test Plan resolve for COVERS tags."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(findings, check="dangling-tag"), \
        "a UT id from the spec's Test Plan did not resolve"


def case_legacy_test_plan_ids_are_valid_targets():
    """A pre-merge project keeps its plan in a separate file; its ids still resolve."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=None,
        legacy_test_plan="| ID | Req |\n|----|-----|\n| UT-001 | REQ-001 |\n",
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert not has_finding(findings, check="dangling-tag"), \
        "a UT id from a legacy test-plan.md did not resolve"
    assert has_finding(findings, check="legacy-test-plan"), \
        "the legacy test plan was not reported for migration"


def case_missing_test_plan_warns():
    """A spec with no plan anywhere is a warning, not silence."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=None,
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001\n",
    )
    assert has_finding(findings, check="missing-test-plan"), \
        "a spec with no test plan passed silently"


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
        assert has_finding(findings, check="unkeyed-tag"), \
            "an unkeyed tag was accepted without a warning (--feature %s)" % only_feature


def case_duplicate_feature_key_errors():
    """Two features may not share a Feature Key — ids would collide."""
    with tempfile.TemporaryDirectory() as root:
        for slug in ("user-mgmt", "billing"):
            write_spec(root, slug, ["- `REQ-001` (AC-001): The system SHALL work."],
                       nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        findings = run_validator(root)
    assert has_finding(findings, check="key-unique"), \
        "two specs sharing a Feature Key were accepted"


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
    assert not has_finding(findings, check="trace-code", message="REQ-002"), \
        "a retired requirement that kept its AC citation was still required in code"
    assert not has_finding(findings, check="ears", message="REQ-002"), \
        "a retired requirement was checked for EARS syntax"


def case_nfr_row_wording_alone_does_not_exempt():
    """Words in the Validated By cell exempt nothing — only the heading does."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Latency | p95 < 300ms | load test in the checkout process |"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="trace-code", message="NFR-001"), \
        "an NFR was exempted by the word 'process' in its Validated By cell"


def case_lowercase_shall_is_flagged():
    """Uppercase is what makes a keyword a keyword."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): the system shall sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="ears", message="REQ-001"), \
        "a lowercase 'shall' passed as canonical EARS"


def case_lowercase_ears_keyword_is_flagged():
    """A lowercase leading keyword is prose, not an event-driven requirement."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): when a user signs up, the system SHALL email them."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="ears", message="REQ-001"), \
        "a lowercase EARS keyword passed as canonical"


def case_feature_scope_leaves_other_features_alone():
    """--feature narrows findings; it must not dangle every other feature's tags."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "user-mgmt", ["- `REQ-001` (AC-001): The system SHALL sign up users."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        write_spec(root, "billing", ["- `REQ-001` (AC-002): The system SHALL charge cards."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"],
                   feature_key="BILLING")
        write_file(root, os.path.join("src", "users.py"),
                   "# IMPLEMENTS: USERMGMT:REQ-001\n")
        write_file(root, os.path.join("tests", "test_users.py"),
                   "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n")
        write_file(root, os.path.join("src", "billing.py"),
                   "# IMPLEMENTS: BILLING:REQ-001\n")
        write_file(root, os.path.join("tests", "test_billing.py"),
                   "# COVERS: BILLING:REQ-001, BILLING:UT-001\n")
        findings = run_validator(root, only_feature="user-mgmt")
    assert not has_finding(findings, check="dangling-tag"), \
        "--feature reported another feature's tags as dangling"
    assert not has_finding(findings, check="trace-code"), \
        "--feature reported coverage errors outside the selected feature"


def case_slug_that_cannot_make_a_key_errors():
    """`2fa` -> `2FA` is not a valid key: tags could never resolve, so say so."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "2fa", ["- `REQ-001` (AC-001): The system SHALL verify codes."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"],
                   feature_key=None)
        findings = run_validator(root)
    assert has_finding(findings, check="feature-key", message="2FA"), \
        "a slug that cannot produce a valid Feature Key was accepted silently"


def case_markdown_examples_are_not_tags():
    """A fenced example in a README documents the format; it claims nothing."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "user-mgmt", ["- `REQ-001` (AC-001): The system SHALL sign up users."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        write_file(root, os.path.join("src", "users.py"),
                   "# IMPLEMENTS: USERMGMT:REQ-001\n")
        write_file(root, os.path.join("tests", "test_users.py"),
                   "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n")
        write_file(root, "README.md",
                   "Tag source files like this:\n\n"
                   "```python\n# IMPLEMENTS: AUTH:REQ-042\n```\n")
        findings = run_validator(root)
    assert not has_finding(findings, check="dangling-tag"), \
        "an example inside a fenced code block was read as a real tag"


def case_excluded_file_is_not_scanned():
    """--exclude covers the examples that live outside a code fence."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "user-mgmt", ["- `REQ-001` (AC-001): The system SHALL sign up users."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        write_file(root, os.path.join("src", "users.py"),
                   "# IMPLEMENTS: USERMGMT:REQ-001\n")
        write_file(root, os.path.join("tests", "test_users.py"),
                   "# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n")
        write_file(root, "AGENTS.md", "Tag files like IMPLEMENTS: AUTH:REQ-042\n")
        findings = run_validator(root, excluded_patterns=["AGENTS.md"])
    assert not has_finding(findings, check="dangling-tag"), \
        "an excluded file was still scanned for tags"


def case_plain_docs_directory_is_not_legacy():
    """Most projects have a docs/. It is evidence of nothing."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "user-mgmt", ["- `REQ-001` (AC-001): The system SHALL sign up users."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        write_file(root, os.path.join("docs", "index.md"), "# Our docs\n")
        write_file(root, os.path.join("docs", "ARCHITECTURE.md"), "# Ours too\n")
        findings = run_validator(root)
    assert not has_finding(findings, check="legacy-layout"), \
        "a project's own docs/ directory was reported as a legacy SDLC layout"


def case_legacy_steering_documents_are_detected():
    """The files /sdlc-init writes, at their pre-.sdlc/ path, are the real signal."""
    with tempfile.TemporaryDirectory() as root:
        write_spec(root, "user-mgmt", ["- `REQ-001` (AC-001): The system SHALL sign up users."],
                   nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        write_file(root, os.path.join("docs", "product.md"), "# Product\n")
        findings = run_validator(root)
    assert has_finding(findings, check="legacy-layout", message="steering docs"), \
        "legacy steering documents were not reported"


def case_unknown_ac_citation_errors():
    """An AC renumbered upstream leaves specs citing an id that no longer exists."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-042): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n",
    )
    assert has_finding(findings, check="ac-citation", message="AC-042"), \
        "a requirement citing an AC the brief does not define was accepted"


def case_known_ac_citation_is_accepted():
    """The common case must stay silent, or the check is unusable."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
        problem_brief="- [ ] `AC-001` (US-001): A user can sign up.\n",
    )
    assert not has_finding(findings, check="ac-citation"), \
        "a valid AC citation was reported as unknown"


def case_planned_test_that_nothing_covers_warns():
    """A test plan row with no test behind it is a gap the validator can see."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        test_plan_rows=["| UT-001 | REQ-001 |", "| UT-002 | REQ-001 |"],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="plan-test-uncovered", message="UT-002"), \
        "a planned test that no test file covers passed silently"


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------
def get_findings(requirements, source, test, nfr_rows=None,
                 test_plan_rows=("| UT-001 | REQ-001 |",), legacy_test_plan=None,
                 outside_code_nfrs=None, problem_brief=None, only_feature=None):
    """Build a one-feature project in a temp dir and return the validator findings."""
    root = tempfile.mkdtemp()
    try:
        write_spec(root, "user-mgmt", requirements, nfr_rows, test_plan_rows,
                   outside_code_nfrs=outside_code_nfrs)
        if problem_brief:
            write_file(root, os.path.join(".sdlc", "requirements",
                                          "problem-brief.md"), problem_brief)
        if legacy_test_plan:
            write_file(root, os.path.join(".sdlc", "tests", "user-mgmt",
                                          "test-plan.md"), legacy_test_plan)
        write_file(root, os.path.join("src", "users.py"), source + "def signup(): pass\n")
        write_file(root, os.path.join("tests", "test_users.py"),
                   test + "def test_signup(): pass\n")
        return run_validator(root, only_feature=only_feature)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def write_spec(root, slug, requirements, nfr_rows, test_plan_rows,
               outside_code_nfrs=None, feature_key=DEFAULT_FEATURE_KEY):
    """Write a spec.md for one feature, with optional NFR table and test plan."""
    sections = [get_spec_header(feature_key), "## Requirements\n\n",
                "\n".join(requirements), "\n\n"]
    if nfr_rows:
        sections += [
            "## Non-Functional Requirements\n\n",
            "| ID | Requirement | Target | Validated By |\n",
            "|----|-------------|--------|--------------|\n",
            "\n".join(nfr_rows), "\n\n",
        ]
    if outside_code_nfrs:
        sections += [
            "## NFRs Validated Outside Code\n\n",
            "\n".join(outside_code_nfrs), "\n\n",
        ]
    if test_plan_rows:
        sections += [
            "## Test Plan\n\n### Unit Tests\n",
            "| ID | Req |\n|----|-----|\n",
            "\n".join(test_plan_rows), "\n",
        ]
    write_file(root, os.path.join(".sdlc", "specs", slug, "spec.md"),
               "".join(sections))


def write_file(root, relative_path, content):
    """Write one file, creating its parent directories."""
    path = os.path.join(root, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        file_handle.write(content)


def run_validator(root, only_feature=None, excluded_patterns=()):
    """Validate the project at `root` and return its findings."""
    return load_validator().validate_project(
        root, only_feature=only_feature,
        excluded_patterns=excluded_patterns).findings


def has_finding(findings, check=None, message=None):
    """Return True when a finding matches the given check name and message fragment."""
    for _, finding_check, finding_message, _ in findings:
        if check and finding_check != check:
            continue
        if message and message not in finding_message:
            continue
        return True
    return False


def load_validator():
    """Import the validator by path — its filename is not a valid module name."""
    module_spec = importlib.util.spec_from_file_location(
        "sdlc_validate", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    sys.exit(main())
