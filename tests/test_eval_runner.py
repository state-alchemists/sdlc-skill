#!/usr/bin/env python3
"""Regression tests for evals/run.py. Run directly: python3 tests/test_eval_runner.py"""

# SPEC: .sdlc/specs/eval-runner/spec.md
# COVERS: EVAL:REQ-001, EVAL:REQ-002, EVAL:REQ-003, EVAL:REQ-004, EVAL:REQ-005, EVAL:REQ-006, EVAL:NFR-001, EVAL:UT-001, EVAL:UT-002, EVAL:UT-003, EVAL:UT-004, EVAL:UT-005, EVAL:UT-006

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

from harness import run_cases

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER_PATH = os.path.join(REPOSITORY_ROOT, "evals", "run.py")


def case_case_without_input_or_rubric_is_a_lint_problem():
    """A case is only gradeable by a human if both files exist."""
    with temporary_directory() as case_directory:
        problems = load_runner().get_case_problems(case_directory)
    assert "missing input.md" in problems and "missing rubric.md" in problems, problems


def case_malformed_check_definitions_are_lint_problems():
    """A typo'd key silently dropped a threshold; bad regexes failed at grading."""
    runner = load_runner()
    for check, expected in (
        ({"type": "nope", "target_file": "a"}, "bad type"),
        ({"type": "file_exists"}, "missing target_file"),
        ({"type": "contains_regex", "target_file": "a"}, "missing pattern"),
        ({"type": "min_matches", "target_file": "a", "pattern": "x"}, "min_count"),
        ({"type": "file_exists", "target_file": "a", "min_cuont": 3}, "unknown key"),
        ({"type": "file_exists", "target_file": "a", "severity": "fatal"}, "severity"),
        ({"type": "contains_regex", "target_file": "a", "pattern": "("}, "bad regex"),
    ):
        problems = runner.get_check_problems(check, 0)
        assert any(expected in problem for problem in problems), (check, problems)


def case_absent_regex_on_a_missing_file_fails():
    """It passed vacuously, so a case could pass by producing nothing."""
    with temporary_directory() as actual_directory:
        is_passing, _ = load_runner().grade_check(
            {"type": "absent_regex", "target_file": "spec.md", "pattern": "X"},
            actual_directory,
        )
    assert not is_passing, "absent_regex passed although the target file is missing"


def case_severity_decides_fail_or_partial():
    """An error-severity failure fails the case; warning-only makes it PARTIAL."""
    runner = load_runner()
    with temporary_directory() as case_directory, temporary_directory() as actual:
        for severity, expected in (("error", "FAIL"), ("warning", "PARTIAL")):
            write_checks(case_directory, [check_missing_file(severity)])
            verdict, _ = runner.grade_case(case_directory, actual)
            assert verdict == expected, (severity, verdict)
        os.remove(os.path.join(case_directory, "checks.json"))
        verdict, _ = runner.grade_case(case_directory, actual)
        assert verdict == "SKIP", "a rubric-only case was not reported as SKIP"


def case_min_and_max_matches_bound_the_count():
    """Both thresholds are inclusive."""
    runner = load_runner()
    with temporary_directory() as actual:
        with open(os.path.join(actual, "spec.md"), "w") as file_handle:
            file_handle.write("REQ-1 REQ-2 REQ-3")
        base = {"target_file": "spec.md", "pattern": r"REQ-\d"}
        assert runner.grade_check(dict(base, type="min_matches", min_count=3), actual)[
            0
        ]
        assert not runner.grade_check(
            dict(base, type="min_matches", min_count=4), actual
        )[0]
        assert runner.grade_check(dict(base, type="max_matches", max_count=3), actual)[
            0
        ]
        assert not runner.grade_check(
            dict(base, type="max_matches", max_count=2), actual
        )[0]


def case_exit_code_reflects_failures():
    """CI reads the exit code, so a failing case must exit 1 and a pass 0."""
    runner = load_runner()
    with temporary_directory() as case_directory, temporary_directory() as actual:
        for name in ("input.md", "rubric.md"):
            open(os.path.join(case_directory, name), "w").close()
        cases = [("sdlc-x", "case", case_directory)]
        write_checks(case_directory, [check_missing_file("error")])
        with contextlib.redirect_stdout(io.StringIO()):
            assert runner.grade_cases(cases, actual) == 1
            assert runner.lint_cases(cases) == 0
        open(os.path.join(actual, "missing.md"), "w").close()
        with contextlib.redirect_stdout(io.StringIO()):
            assert runner.grade_cases(cases, actual) == 0


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------
def check_missing_file(severity):
    """Return a file_exists check on a file the fixture does not create."""
    return {
        "id": "C1",
        "type": "file_exists",
        "target_file": "missing.md",
        "severity": severity,
    }


def write_checks(case_directory, checks):
    """Write a checks.json holding `checks`."""
    with open(os.path.join(case_directory, "checks.json"), "w") as file_handle:
        json.dump({"checks": checks}, file_handle)


@contextlib.contextmanager
def temporary_directory():
    """Yield a fresh directory, removed afterwards."""
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def load_runner():
    """Import evals/run.py by path."""
    module_spec = importlib.util.spec_from_file_location("eval_run", RUNNER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    sys.exit(run_cases(globals()))
