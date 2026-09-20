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

SPEC_HEADER = "# Feature Spec: User Management\n\n**Feature Key:** USERMGMT\n\n"


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
    """An NFR validated outside application code needs no IMPLEMENTS/COVERS."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        nfr_rows=["| NFR-001 | Backup retention | 30 days | infra policy |"],
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
    """A pre-Feature-Key tag is tolerated, with a nudge to re-key it."""
    findings = get_findings(
        requirements=["- `REQ-001` (AC-001): The system SHALL sign up users."],
        source="# IMPLEMENTS: USERMGMT:REQ-001\n# @sdlc REQ-001\n",
        test="# COVERS: USERMGMT:REQ-001, USERMGMT:UT-001\n",
    )
    assert has_finding(findings, check="unkeyed-tag"), \
        "an unkeyed tag was accepted without a warning"


def case_duplicate_feature_key_errors():
    """Two features may not share a Feature Key — ids would collide."""
    with tempfile.TemporaryDirectory() as root:
        for slug in ("user-mgmt", "billing"):
            write_spec(root, slug, ["- `REQ-001` (AC-001): The system SHALL work."],
                       nfr_rows=None, test_plan_rows=["| UT-001 | REQ-001 |"])
        findings = run_validator(root)
    assert has_finding(findings, check="key-unique"), \
        "two specs sharing a Feature Key were accepted"


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------
def get_findings(requirements, source, test, nfr_rows=None,
                 test_plan_rows=("| UT-001 | REQ-001 |",), legacy_test_plan=None):
    """Build a one-feature project in a temp dir and return the validator findings."""
    root = tempfile.mkdtemp()
    try:
        write_spec(root, "user-mgmt", requirements, nfr_rows, test_plan_rows)
        if legacy_test_plan:
            write_file(root, os.path.join(".sdlc", "tests", "user-mgmt",
                                          "test-plan.md"), legacy_test_plan)
        write_file(root, os.path.join("src", "users.py"), source + "def signup(): pass\n")
        write_file(root, os.path.join("tests", "test_users.py"),
                   test + "def test_signup(): pass\n")
        return run_validator(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def write_spec(root, slug, requirements, nfr_rows, test_plan_rows):
    """Write a spec.md for one feature, with optional NFR table and test plan."""
    sections = [SPEC_HEADER, "## Requirements\n\n", "\n".join(requirements), "\n\n"]
    if nfr_rows:
        sections += [
            "## Non-Functional Requirements\n\n",
            "| ID | Requirement | Target | Validated By |\n",
            "|----|-------------|--------|--------------|\n",
            "\n".join(nfr_rows), "\n\n",
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


def run_validator(root):
    """Validate the project at `root` and return its findings."""
    return load_validator().validate_project(root).findings


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
