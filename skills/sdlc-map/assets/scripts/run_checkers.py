#!/usr/bin/env python3
"""Run every checker this map has, in one command, for CI.

The four ship with the map; `/sdlc-tend` may add one more for an invariant the
map says nothing enforces, and lists it in `map.json` -> `checkers`. A checker
nothing runs is the paragraph it replaced, so wiring a project's CI is this one
line, which cannot drift from the list:

    python3 scripts/run_checkers.py

And its second half, which proves each generated checker can still fail after
the code under it has moved:

    python3 scripts/run_checkers.py --self-test

The register generator is asked to CHECK rather than rewrite: CI must not edit
the tree it is judging.

Exit `0` when every checker passed, `1` when one reported a problem, `2` when a
listed checker is missing or could not start — drift in the list rather than a
finding in the map.

What the checkers read, and where they are blind, is in `map.json` — see
`map_config.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import map_config

ROOT = map_config.ROOT

# The four that ship with the map, in the order the map documents them.
SHIPPED_CHECKERS = (
    ("collect_unknowns.py", ("--check",)),
    ("check_references.py", ()),
    ("check_symbols.py", ()),
    ("check_structure.py", ()),
)

EXIT_CLEAN, EXIT_PROBLEMS, EXIT_DRIFT = 0, 1, 2


def get_jobs(self_test: bool) -> list[tuple[Path, tuple[str, ...]]]:
    """The checkers to run, and the arguments each one needs.

    A self-test run is about the checkers a tend run wrote: the four ship
    without a plant, and asking them for one asks a question they were never
    given.
    """
    if self_test:
        return [(ROOT / name, ("--self-test",)) for name in map_config.get_checkers()]
    jobs = [
        (Path(__file__).resolve().parent / name, arguments)
        for name, arguments in SHIPPED_CHECKERS
    ]
    jobs.extend((ROOT / name, ()) for name in map_config.get_checkers())
    return jobs


def run(script: Path, arguments: tuple[str, ...]) -> tuple[int, str]:
    """Run one checker from the project root; return its exit code and output."""
    if not script.is_file():
        return EXIT_DRIFT, "MISSING %s — listed in map.json but not on disk." % script.name
    try:
        completed = subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return EXIT_DRIFT, "CANNOT START %s — %s" % (script.name, error)
    return completed.returncode, (completed.stdout + completed.stderr).rstrip()


def worst(codes: list[int]) -> int:
    """Drift outranks a finding, which outranks a clean run."""
    if EXIT_DRIFT in codes:
        return EXIT_DRIFT
    return EXIT_PROBLEMS if EXIT_PROBLEMS in codes else EXIT_CLEAN


def main(argv: list[str]) -> int:
    """Run every job, print what each said, and return the worst exit code."""
    jobs = get_jobs("--self-test" in argv)
    if not jobs:
        print("No map checkers were listed; nothing to run.")
        return EXIT_CLEAN
    codes = []
    for script, arguments in jobs:
        code, output = run(script, arguments)
        print("== %s %s" % (script.name, " ".join(arguments)))
        if output:
            print(output)
        codes.append(code)
    failures = sum(1 for code in codes if code != EXIT_CLEAN)
    print("\n%d checker(s), %d failed" % (len(jobs), failures))
    return worst(codes)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
