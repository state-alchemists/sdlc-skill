#!/usr/bin/env python3
"""The four map checkers, run against a project that is not the one they were written in.

They shipped with one repository's tree baked in: pages at the repository root,
the register at `reference/unknowns/`, seven tiers named after that project's
own folders. So the gate passed in exactly one place and failed everywhere else
on the tree's shape, before it checked a single claim — the failure mode a
checker is supposed to prevent, worn by the checkers themselves.

Each case here builds a small project that shares no folder name with this
repository, runs a checker against it, and asserts what it says. The last case
is static, and is the pin: it fails on the copies that had the names in them.

Run it directly:

    python3 tests/test_map_checkers.py

Exit 0 means every case passed; a failed assertion names the case.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harness import run_cases

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPOSITORY_ROOT / "skills" / "sdlc-map" / "assets" / "scripts"
CHECKERS = ("check_references.py", "check_symbols.py", "check_structure.py", "collect_unknowns.py")
GENERATOR = "collect_unknowns.py"

FRONT = """# Demo

A project nobody has mapped. The map starts at [_docs/systems/thing.md](_docs/systems/thing.md).
"""

SOURCE = """def load_config(path):
    return path
"""

PAGE = """# Thing

## In one paragraph

`load_config` reads a path and hands it back.

## How it works

The loader is `load_config` in `src/app.py`.

## Diagram

```mermaid
flowchart LR
    A(["a caller"]) --> B(["the path"])
```

## Where it lives

| What | Repository | Path |
| --- | --- | --- |
| the loader | this project | `src/app.py` |

## What breaks if you change it

| Change | Which way it breaks | How you would find out |
| --- | --- | --- |
| the signature | every caller | the test suite |

## Unverified

- **Nobody has tried a read-only mount.** Settle: run the suite against one.
"""


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------
def case_a_project_that_is_not_this_repository_passes_all_four():
    """The gate has to be green on a tree with no `reference/`, no tiers and no
    `lcicd/` — otherwise it is green only where it was written."""
    project = build_project()
    code, output = run(project, GENERATOR)
    assert code == 0, output
    for checker in CHECKERS:
        code, output = run(project, checker)
        assert code == 0, "%s failed on a plain project:\n%s" % (checker, output)
    assert "0 problems" in run(project, "check_structure.py")[1]


def case_the_register_is_filed_under_the_projects_own_folders():
    """Tiers come from the tree, so a project that never named one still gets a
    register in the shape of its own folders."""
    project = build_project()
    code, output = run(project, GENERATOR)
    assert code == 0, output
    register = project / "_docs" / "unknowns"
    assert (register / "systems.md").is_file(), sorted(p.name for p in register.glob("*.md"))
    text = (register / "systems.md").read_text(encoding="utf-8")
    assert "Nobody has tried a read-only mount" in text
    assert "](../systems/thing.md)" in text, text


def case_a_moved_file_is_reported_missing():
    """A page citing a file that is gone is the claim the checker exists for."""
    project = build_project()
    (project / "src" / "app.py").unlink()
    code, output = run(project, "check_references.py")
    assert code == 1, output
    assert "MISSING _docs/systems/thing.md" in output, output
    assert "src/app.py" in output, output


def case_a_renamed_symbol_is_reported_stale():
    """A file that still exists but no longer holds the name the page quotes."""
    project = build_project()
    (project / "src" / "app.py").write_text(
        "def read_config(path):\n    return path\n", encoding="utf-8"
    )
    code, output = run(project, "check_symbols.py", "--strict")
    assert code == 1, output
    assert "STALE" in output and "load_config" in output, output


def case_a_line_citation_is_refused():
    """A line number is true for one commit and drifts silently afterwards."""
    project = build_project()
    page = project / "_docs" / "systems" / "thing.md"
    page.write_text(
        page.read_text(encoding="utf-8").replace("`src/app.py`", "`src/app.py:12`"),
        encoding="utf-8",
    )
    code, output = run(project, "check_references.py")
    assert code == 1, output
    assert "LINE-NUMBER" in output, output


def case_a_page_without_the_six_sections_is_reported():
    """The one shape rule the whole map leans on."""
    project = build_project()
    page = project / "_docs" / "systems" / "thing.md"
    page.write_text("# Thing\n\n## Where it lives\n\nSomewhere.\n", encoding="utf-8")
    code, output = run(project, "check_structure.py")
    assert code == 1, output
    assert "SHAPE _docs/systems/thing.md" in output, output


def case_a_broken_link_and_a_stale_register_are_reported():
    """Two ways a page stops being true: a link that no longer resolves, and a
    claim added without regenerating the index that counts it."""
    project = build_project()
    assert run(project, GENERATOR)[0] == 0
    front = project / "README.md"
    front.write_text(
        front.read_text(encoding="utf-8").replace("_docs/systems/thing.md", "_docs/oops.md"),
        encoding="utf-8",
    )
    page = project / "_docs" / "systems" / "thing.md"
    page.write_text(
        page.read_text(encoding="utf-8")
        + "- **The second case has never run.** Settle: run it once.\n",
        encoding="utf-8",
    )
    code, output = run(project, "check_structure.py")
    assert code == 1, output
    assert "BROKEN README.md" in output, output
    assert "STALE _docs/unknowns/systems.md" in output, output


def case_a_page_root_that_is_absent_is_reported_instead_of_passing_clean():
    """A checker that finds nothing to check prints a clean summary, and an
    empty map is the largest thing it could hide."""
    project = build_project()
    shutil.rmtree(project / "_docs")
    code, output = run(project, "check_structure.py")
    assert code == 1, output
    assert "MISSING ROOT _docs" in output, output


def case_the_checkers_name_no_folder_of_this_repository():
    """The pin. Every one of these tokens was in the shipped copies, and each
    made the gate wrong for a project that does not have that folder."""
    forbidden = ("lcicd", "soda/", "bsim", "delivery-atlas", "reference/unknowns", "platform-ci")
    offenders = []
    for checker in CHECKERS + ("map_config.py",):
        text = (SCRIPTS / checker).read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append("%s names %r" % (checker, token))
    assert not offenders, "; ".join(offenders)
    for checker in CHECKERS:
        text = (SCRIPTS / checker).read_text(encoding="utf-8")
        assert "map_config" in text, (
            "%s reads project facts somewhere other than map_config.py" % checker
        )


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def build_project(settings=None) -> Path:
    """A project that shares no folder name with this repository."""
    project = Path(tempfile.mkdtemp(prefix="sdlc-map-"))
    shutil.copytree(str(SCRIPTS), str(project / "scripts"))
    if settings is not None:
        (project / "map.json").write_text(json.dumps(settings), encoding="utf-8")
    (project / "README.md").write_text(FRONT, encoding="utf-8")
    (project / "src").mkdir()
    (project / "src" / "app.py").write_text(SOURCE, encoding="utf-8")
    page = project / "_docs" / "systems" / "thing.md"
    page.parent.mkdir(parents=True)
    page.write_text(PAGE, encoding="utf-8")
    return project


def run(project: Path, script: str, *arguments: str):
    """Run one checker inside the project, and return (exit code, its output)."""
    result = subprocess.run(
        [sys.executable, str(project / "scripts" / script)] + list(arguments),
        cwd=str(project),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


if __name__ == "__main__":
    sys.exit(run_cases(globals()))
