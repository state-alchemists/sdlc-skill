# Feature Spec: Eval runner

**Feature Key:** EVAL

`evals/run.py` — lints golden cases and grades a skill's output against them. Architecture: [ADR-012](../../docs/adr/ADR-012-deterministic-evals.md).

## Requirements

- `REQ-001` (AC-012): IF a case lacks `input.md` or `rubric.md`, THEN the runner SHALL report a lint problem.
- `REQ-002` (AC-012): IF a check has an unknown type or key, a bad severity, a missing target, pattern or threshold, or an invalid regex, THEN the runner SHALL report a lint problem.
- `REQ-003` (AC-012): WHEN grading a case, the runner SHALL return FAIL when an error-severity check fails, PARTIAL when only warning-severity checks fail, and SKIP when the case has no `checks.json`.
- `REQ-004` (AC-012): IF the target file of an `absent_regex` check is missing, THEN the runner SHALL fail that check.
- `REQ-005` (AC-012): The runner SHALL treat `min_count` and `max_count` as inclusive bounds on the number of matches.
- `REQ-006` (AC-012): The runner SHALL exit with 1 when any graded case fails or any case has a lint problem, and with 0 otherwise.

## Non-Functional Requirements

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-001 | Runs on Python 3.8+ using only the standard library | no third-party import | test suite run on Python 3.8 with nothing installed |

## API Surface

| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| CLI | `evals/run.py` | `[--list] [--skill NAME] [--case SKILL/CASE] [--actual DIR]` | `LINT OK/FAIL` lines, or per-check `[PASS]/[FAIL]` and `Overall:` | none |

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| No matching case, a lint problem, or a failed case | exit 1 | the problems or failing checks |
| All clean | exit 0 | summary |

## Correctness

- **Validation:** every check definition is linted, and every regex compiled, before any grading runs.

## Entities

None — checks and cases are defined in `evals/README.md`.

## Test Plan

*Test naming convention: `case_<behaviour_stated_as_a_sentence>` in `tests/test_eval_runner.py`.*

### Unit Tests
| ID | Req | Test Name | Input | Expected |
|----|-----|-----------|-------|----------|
| UT-001 | REQ-001 | `case_case_without_input_or_rubric_is_a_lint_problem` | empty case directory | both files reported missing |
| UT-002 | REQ-002 | `case_malformed_check_definitions_are_lint_problems` | seven malformed checks | each reported |
| UT-003 | REQ-003 | `case_severity_decides_fail_or_partial` | failing error / warning check; no checks.json | FAIL / PARTIAL / SKIP |
| UT-004 | REQ-004 | `case_absent_regex_on_a_missing_file_fails` | missing target | check fails |
| UT-005 | REQ-005 | `case_min_and_max_matches_bound_the_count` | three matches | 3 passes both bounds, 4/2 fail |
| UT-006 | REQ-006 | `case_exit_code_reflects_failures` | failing then passing case | exit 1, then 0 |

### Integration Tests
N/A — `bin/test.sh` lints the real golden cases on every run.

### End-to-End Tests
N/A — grading real skill output is manual (see test-strategy.md, Known gap).

### Property-Based Tests
N/A — no property-testing framework configured.

### Design Property Coverage
| Property | Covered By | Notes |
|----------|------------|-------|
| Validation | UT-002 | |

### Test Data Strategy
- **Fixtures**: temporary case and output directories per test.
- **Synthetic data**: minimal `checks.json` written by `write_checks`.
- **Cleanup**: `temporary_directory()` context manager.
