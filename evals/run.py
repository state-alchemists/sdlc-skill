#!/usr/bin/env python3
"""run.py — eval runner for the sdlc-* skills.

Rule-based, deterministic, stdlib only. Each golden case under evals/golden/
may carry a `checks.json` of machine-checkable assertions. Point the runner at
a directory of actual skill output and it grades each check PASS/FAIL.

USAGE
    python3 evals/run.py --list                       # list all cases
    python3 evals/run.py                              # lint: validate case structure
    python3 evals/run.py --actual DIR                 # grade all cases against DIR
    python3 evals/run.py --skill sdlc-spec --actual DIR
    python3 evals/run.py --case sdlc-spec/email-verification --actual DIR

A case directory contains:
    input.md     — the inputs the skill receives (interview answers, files it reads)
    rubric.md    — human-readable PASS / FAIL / PARTIAL criteria
    checks.json  — optional deterministic checks this runner grades
    expected/    — optional reference output tree

checks.json schema:
    {
      "case": "sdlc-spec/email-verification",
      "checks": [
        {"id": "SPEC-1", "description": "...", "type": "file_exists",
         "target_file": ".sdlc/specs/email-verification/spec.md", "severity": "error"},
        {"id": "SPEC-4", "description": "...", "type": "absent_regex",
         "target_file": "...", "pattern": "ALWAYS\\s+SHALL", "severity": "error"},
        {"id": "SPEC-7", "description": "...", "type": "min_matches",
         "target_file": "...", "pattern": "REQ-\\d+", "min_count": 3, "severity": "error"}
      ]
    }

check types:
    file_exists    — target_file exists under --actual.
    contains_regex — target_file exists AND `pattern` is found.
    absent_regex   — target_file (if present) does NOT contain `pattern`.
    min_matches    — target_file contains >= `min_count` matches of `pattern`.

severity:
    error (default) — a failed check makes the case FAIL.
    warning         — a failed check makes the case PARTIAL.

EXIT CODES
    0  all graded cases PASS (or lint clean)
    1  one or more cases FAIL, or a structural problem
"""

import argparse
import json
import os
import re
import sys

EXIT_PASS, EXIT_FAIL = 0, 1

GOLDEN_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "golden")

CHECK_TYPES = {"file_exists", "file_absent", "contains_regex", "absent_regex",
               "min_matches", "max_matches"}
PATTERN_CHECK_TYPES = {"contains_regex", "absent_regex", "min_matches",
                       "max_matches"}
KNOWN_CHECK_KEYS = {"id", "description", "type", "target_file", "pattern",
                    "min_count", "max_count", "severity"}
KNOWN_SEVERITIES = {"error", "warning"}
REQUIRED_CASE_FILES = ("input.md", "rubric.md")


def main(argv=None):
    """Parse arguments, then list, lint, or grade the selected cases."""
    parser = argparse.ArgumentParser(description="Eval runner for sdlc-* skills.")
    parser.add_argument("--list", action="store_true", help="list cases and exit")
    parser.add_argument("--skill", help="restrict to one skill (e.g. sdlc-spec)")
    parser.add_argument("--case", help="restrict to one case (skill/case-name)")
    parser.add_argument("--actual", help="directory of skill output to grade")
    arguments = parser.parse_args(argv)

    cases = get_selected_cases(arguments.skill, arguments.case)
    if not cases:
        print("No matching cases.")
        return EXIT_FAIL

    if arguments.list:
        return list_cases(cases)
    if not arguments.actual:
        return lint_cases(cases)
    return grade_cases(cases, os.path.abspath(arguments.actual))


def get_selected_cases(skill_filter, case_filter):
    """Return the golden cases matching the filters, as (skill, name, path)."""
    cases = get_golden_cases()
    if skill_filter:
        cases = [case for case in cases if case[0] == skill_filter]
    if case_filter:
        cases = [case for case in cases if "%s/%s" % (case[0], case[1]) == case_filter]
    return cases


def get_golden_cases():
    """Return every (skill, case_name, case_directory) under evals/golden/."""
    cases = []
    if not os.path.isdir(GOLDEN_DIRECTORY):
        return cases
    for skill in sorted(os.listdir(GOLDEN_DIRECTORY)):
        skill_directory = os.path.join(GOLDEN_DIRECTORY, skill)
        if not os.path.isdir(skill_directory):
            continue
        for case_name in sorted(os.listdir(skill_directory)):
            case_directory = os.path.join(skill_directory, case_name)
            if os.path.isdir(case_directory):
                cases.append((skill, case_name, case_directory))
    return cases


def list_cases(cases):
    """Print each case and whether it carries deterministic checks."""
    for skill, case_name, case_directory in cases:
        has_checks = os.path.exists(os.path.join(case_directory, "checks.json"))
        print("%s/%s  [%s]"
              % (skill, case_name, "checks.json" if has_checks else "rubric-only"))
    return EXIT_PASS


def lint_cases(cases):
    """Validate every case's structure without grading anything."""
    problem_count = 0
    for skill, case_name, case_directory in cases:
        problems = get_case_problems(case_directory)
        if problems:
            problem_count += 1
            print("LINT FAIL %s/%s: %s" % (skill, case_name, "; ".join(problems)))
        else:
            print("LINT OK   %s/%s" % (skill, case_name))
    print("\n%d case(s), %d with problems" % (len(cases), problem_count))
    return EXIT_FAIL if problem_count else EXIT_PASS


def grade_cases(cases, actual_directory):
    """Grade every case against the produced output and print the results."""
    has_failure = False
    for skill, case_name, case_directory in cases:
        verdict, results = grade_case(case_directory, actual_directory)
        print("\n=== %s/%s: %s ===" % (skill, case_name, verdict))
        for check_id, is_passing, detail in results:
            print("  [%s] %s  %s" % ("PASS" if is_passing else "FAIL", check_id, detail))
        if verdict == "FAIL":
            has_failure = True
    print("\nOverall: %s" % ("FAIL" if has_failure else "PASS"))
    return EXIT_FAIL if has_failure else EXIT_PASS


def get_case_problems(case_directory):
    """Return a list of structural problems for one case (empty means clean)."""
    problems = []
    for required_file in REQUIRED_CASE_FILES:
        if not os.path.exists(os.path.join(case_directory, required_file)):
            problems.append("missing %s" % required_file)

    checks_path = os.path.join(case_directory, "checks.json")
    if not os.path.exists(checks_path):
        return problems
    try:
        with open(checks_path, encoding="utf-8") as file_handle:
            case_data = json.load(file_handle)
    except (ValueError, OSError) as error:
        problems.append("checks.json not valid JSON: %s" % error)
        return problems

    checks = case_data.get("checks")
    if not isinstance(checks, list):
        problems.append("checks.json has no 'checks' list")
        return problems
    for index, check in enumerate(checks):
        problems.extend(get_check_problems(check, index))
    return problems


def get_check_problems(check, index):
    """Return a list of problems with one check definition."""
    problems = []
    check_type = check.get("type")
    if check_type not in CHECK_TYPES:
        problems.append("check #%d: bad type %r" % (index, check_type))
    if not check.get("target_file"):
        problems.append("check #%d: missing target_file" % index)
    if check_type in PATTERN_CHECK_TYPES and not check.get("pattern"):
        problems.append("check #%d: missing pattern" % index)
    if check_type == "min_matches" and not isinstance(check.get("min_count"), int):
        problems.append("check #%d: min_matches needs integer min_count" % index)
    if check_type == "max_matches" and not isinstance(check.get("max_count"), int):
        problems.append("check #%d: max_matches needs integer max_count" % index)
    # An unknown key is almost always a typo that silently disables a threshold.
    for key in sorted(set(check) - KNOWN_CHECK_KEYS):
        problems.append("check #%d: unknown key %r" % (index, key))
    severity = check.get("severity", "error")
    if severity not in KNOWN_SEVERITIES:
        problems.append("check #%d: bad severity %r" % (index, severity))
    # Compile now, so an invalid regex fails at lint rather than at grade time.
    if check.get("pattern"):
        try:
            re.compile(check["pattern"])
        except re.error as error:
            problems.append("check #%d: bad regex %r (%s)"
                            % (index, check["pattern"], error))
    return problems


def grade_case(case_directory, actual_directory):
    """Grade one case, returning (verdict, results) with verdict PASS/FAIL/PARTIAL/SKIP."""
    checks_path = os.path.join(case_directory, "checks.json")
    if not os.path.exists(checks_path):
        return ("SKIP", [("—", True, "no checks.json (rubric is human-graded)")])

    with open(checks_path, encoding="utf-8") as file_handle:
        case_data = json.load(file_handle)

    results = []
    has_blocking_failure = False
    has_warning_failure = False
    for check in case_data.get("checks", []):
        is_passing, detail = grade_check(check, actual_directory)
        if not is_passing:
            if check.get("severity", "error") == "warning":
                has_warning_failure = True
            else:
                has_blocking_failure = True
        results.append((
            check.get("id", "?"),
            is_passing,
            "%s — %s" % (check.get("description", check["type"]), detail),
        ))

    if has_blocking_failure:
        return ("FAIL", results)
    return ("PARTIAL" if has_warning_failure else "PASS", results)


def grade_check(check, actual_directory):
    """Grade one check against the produced output, returning (is_passing, detail)."""
    target_path = os.path.join(actual_directory, check["target_file"])
    check_type = check["type"]
    is_present = os.path.exists(target_path)

    if check_type == "file_exists":
        return (is_present, "exists" if is_present else "missing")

    if check_type == "file_absent":
        return (not is_present, "absent" if not is_present else "unexpectedly present")

    if check_type == "absent_regex":
        # A missing file used to pass this vacuously, so a case could pass by
        # producing nothing at all. Use `file_absent` when absence is the point.
        if not is_present:
            return (False, "file missing — absent_regex requires the target to "
                           "exist; use file_absent to assert absence")
        match = re.search(check["pattern"], read_file_text(target_path))
        if match:
            return (False, "found forbidden %r" % check["pattern"])
        return (True, "pattern absent")

    if not is_present:
        return (False, "file missing")
    text = read_file_text(target_path)

    if check_type == "contains_regex":
        match = re.search(check["pattern"], text)
        return (match is not None,
                "found" if match else "pattern %r not found" % check["pattern"])

    if check_type == "min_matches":
        match_count = len(re.findall(check["pattern"], text))
        return (match_count >= check["min_count"],
                "%d matches (need %d)" % (match_count, check["min_count"]))

    if check_type == "max_matches":
        match_count = len(re.findall(check["pattern"], text))
        return (match_count <= check["max_count"],
                "%d matches (allow %d)" % (match_count, check["max_count"]))

    return (False, "unknown check type")


def read_file_text(path):
    """Return a file's text, replacing undecodable bytes."""
    with open(path, encoding="utf-8", errors="replace") as file_handle:
        return file_handle.read()


if __name__ == "__main__":
    sys.exit(main())
