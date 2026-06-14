#!/usr/bin/env python3
"""run.py — eval runner for the sdlc-* skills.

Rule-based, deterministic, stdlib-only. Each golden case under evals/golden/
may carry a `checks.json` of machine-checkable assertions. Point the runner at
a directory of actual skill output and it grades each check PASS/FAIL.

USAGE
    python3 evals/run.py --list                       # list all cases
    python3 evals/run.py                               # lint: validate case structure
    python3 evals/run.py --actual DIR                  # grade all cases against DIR
    python3 evals/run.py --skill sdlc-spec --actual DIR
    python3 evals/run.py --case sdlc-init/personal-todo-app --actual DIR

A case directory contains:
    input.md     — transcript of inputs the skill receives (interview answers, files it reads)
    rubric.md    — human-readable PASS/FAIL/PARTIAL criteria
    checks.json  — (optional) deterministic checks the runner can grade
    expected/    — (optional) reference output tree

checks.json schema:
    {
      "case": "sdlc-init/personal-todo-app",
      "checks": [
        {"id": "C1", "description": "...", "type": "file_exists",
         "target_file": ".sdlc/docs/product.md", "severity": "error"},
        {"id": "C2", "description": "...", "type": "contains_regex",
         "target_file": ".sdlc/rules.md", "pattern": "RULE-999", "severity": "error"},
        {"id": "C3", "description": "...", "type": "absent_regex",
         "target_file": ".sdlc/specs/email-verification/spec.md",
         "pattern": "\\bALWAYS SHALL\\b", "severity": "error"},
        {"id": "C4", "description": "...", "type": "min_matches",
         "target_file": ".sdlc/specs/email-verification/spec.md",
         "pattern": "REQ-\\d+", "min_count": 3, "severity": "error"}
      ]
    }

check types:
    file_exists   — target_file exists under --actual.
    contains_regex— target_file exists AND `pattern` is found.
    absent_regex  — target_file (if present) does NOT contain `pattern`.
    min_matches   — target_file contains >= `min_count` matches of `pattern`.

severity:
    error (default) — a FAIL makes the case FAIL.
    warning         — a FAIL makes the case PARTIAL (not a hard fail).

EXIT CODES
    0  all graded cases PASS (or lint clean)
    1  one or more cases FAIL, or a structural/lint error
"""

import argparse
import json
import os
import re
import sys

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


def discover_cases():
    """Yield (skill, case_name, case_dir) for every golden case."""
    if not os.path.isdir(GOLDEN):
        return
    for skill in sorted(os.listdir(GOLDEN)):
        sdir = os.path.join(GOLDEN, skill)
        if not os.path.isdir(sdir):
            continue
        for case in sorted(os.listdir(sdir)):
            cdir = os.path.join(sdir, case)
            if os.path.isdir(cdir):
                yield skill, case, cdir


def lint_case(cdir):
    """Return a list of structural problems for a case (empty == clean)."""
    problems = []
    for required in ("input.md", "rubric.md"):
        if not os.path.exists(os.path.join(cdir, required)):
            problems.append("missing %s" % required)
    checks_path = os.path.join(cdir, "checks.json")
    if os.path.exists(checks_path):
        try:
            with open(checks_path, encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError) as exc:
            problems.append("checks.json not valid JSON: %s" % exc)
            return problems
        if not isinstance(data.get("checks"), list):
            problems.append("checks.json has no 'checks' list")
        else:
            valid_types = {"file_exists", "contains_regex", "absent_regex", "min_matches"}
            for i, chk in enumerate(data["checks"]):
                if chk.get("type") not in valid_types:
                    problems.append("check #%d: bad type %r" % (i, chk.get("type")))
                if not chk.get("target_file"):
                    problems.append("check #%d: missing target_file" % i)
                if chk.get("type") in ("contains_regex", "absent_regex", "min_matches") and not chk.get("pattern"):
                    problems.append("check #%d: missing pattern" % i)
                if chk.get("type") == "min_matches" and not isinstance(chk.get("min_count"), int):
                    problems.append("check #%d: min_matches needs integer min_count" % i)
    return problems


def grade_check(chk, actual_dir):
    """Return (passed: bool, detail: str)."""
    target = os.path.join(actual_dir, chk["target_file"])
    ctype = chk["type"]
    if ctype == "file_exists":
        return (os.path.exists(target), "exists" if os.path.exists(target) else "missing")
    if ctype == "absent_regex":
        if not os.path.exists(target):
            return (True, "file absent (vacuously absent)")
        with open(target, encoding="utf-8", errors="replace") as f:
            text = f.read()
        hit = re.search(chk["pattern"], text)
        return (hit is None, "pattern absent" if hit is None else "found forbidden %r" % chk["pattern"])
    # remaining types require the file to exist
    if not os.path.exists(target):
        return (False, "file missing")
    with open(target, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if ctype == "contains_regex":
        hit = re.search(chk["pattern"], text)
        return (hit is not None, "found" if hit else "pattern %r not found" % chk["pattern"])
    if ctype == "min_matches":
        n = len(re.findall(chk["pattern"], text))
        need = chk["min_count"]
        return (n >= need, "%d matches (need %d)" % (n, need))
    return (False, "unknown check type")


def grade_case(cdir, actual_dir):
    """Return (verdict, results) where verdict in PASS/FAIL/PARTIAL."""
    checks_path = os.path.join(cdir, "checks.json")
    if not os.path.exists(checks_path):
        return ("SKIP", [("—", True, "no checks.json (rubric is human-graded)")])
    with open(checks_path, encoding="utf-8") as f:
        data = json.load(f)
    results = []
    hard_fail = soft_fail = False
    for chk in data.get("checks", []):
        ok, detail = grade_check(chk, actual_dir)
        sev = chk.get("severity", "error")
        if not ok:
            if sev == "warning":
                soft_fail = True
            else:
                hard_fail = True
        results.append((chk.get("id", "?"), ok, "%s — %s" % (chk.get("description", chk["type"]), detail)))
    verdict = "FAIL" if hard_fail else ("PARTIAL" if soft_fail else "PASS")
    return (verdict, results)


def grade_with_llm(case_dir, actual_dir):
    """TODO (future hook): grade fuzzy rubric.md items an LLM-as-judge can assess.

    This would read rubric.md, feed each non-deterministic criterion plus the
    actual output to an Anthropic model (the latest Claude), and collect a
    PASS/FAIL/PARTIAL judgement per item — mirroring skill-creator's comparator
    pattern (blind A/B vs a no-skill baseline). Not wired up: the rule-based
    checks.json path above is what runs in CI today.
    """
    raise NotImplementedError("LLM-as-judge grading is a future hook; use checks.json for now.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Eval runner for sdlc-* skills.")
    ap.add_argument("--list", action="store_true", help="list cases and exit")
    ap.add_argument("--skill", help="restrict to one skill (e.g. sdlc-spec)")
    ap.add_argument("--case", help="restrict to one case (skill/case-name)")
    ap.add_argument("--actual", help="directory of actual skill output to grade against")
    args = ap.parse_args(argv)

    cases = list(discover_cases())
    if args.skill:
        cases = [c for c in cases if c[0] == args.skill]
    if args.case:
        cases = [c for c in cases if "%s/%s" % (c[0], c[1]) == args.case]

    if not cases:
        print("No matching cases.")
        return 1

    if args.list:
        for skill, case, cdir in cases:
            has = "checks.json" if os.path.exists(os.path.join(cdir, "checks.json")) else "rubric-only"
            print("%s/%s  [%s]" % (skill, case, has))
        return 0

    # Lint mode (no --actual): validate structure only.
    if not args.actual:
        bad = 0
        for skill, case, cdir in cases:
            problems = lint_case(cdir)
            if problems:
                bad += 1
                print("LINT FAIL %s/%s: %s" % (skill, case, "; ".join(problems)))
            else:
                print("LINT OK   %s/%s" % (skill, case))
        print("\n%d case(s), %d with problems" % (len(cases), bad))
        return 1 if bad else 0

    # Grade mode.
    actual = os.path.abspath(args.actual)
    any_fail = False
    for skill, case, cdir in cases:
        verdict, results = grade_case(cdir, actual)
        print("\n=== %s/%s: %s ===" % (skill, case, verdict))
        for cid, ok, detail in results:
            print("  [%s] %s  %s" % ("PASS" if ok else "FAIL", cid, detail))
        if verdict == "FAIL":
            any_fail = True
    print("\nOverall: %s" % ("FAIL" if any_fail else "PASS"))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
