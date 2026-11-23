#!/usr/bin/env python3
"""Fail when the tree stops being a map.

The other two checkers read what a page *claims about the code*: that a path
exists, that a name is still in the file. Neither can see the tree's own shape,
which is what a reader navigates by:

  - every relative link resolves, and every page is reachable from the front page;
  - no page is longer than the configured cap;
  - every page carries the six sections, in order — except the front page, a
    page named in `shapeless`, and the generated register, each of which says
    why it is exempt in `map.json`;
  - no file or folder name starts with a digit;
  - no page names a host path, which is one machine's checkout;
  - no generated page is older than the pages it is generated from.

    python3 scripts/check_structure.py

A link to a directory (`../systems/`) is a link to that directory's
`README.md`; a link to a heading in the same page is not a file claim.

What is a page, which sections it must carry, and where the register lives are
in `map.json` — see `map_config.py`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# A gate must not write into the tree it judges. Importing the sibling modules
# would leave a `__pycache__` beside the checkers, which is an edit to someone
# else's project and lands in their next commit.
sys.dont_write_bytecode = True

import map_config as config

ROOT = config.ROOT
CAP = config.get("line_cap")
SECTIONS = tuple(config.get("sections"))
SHAPELESS = config.get("shapeless")
REGISTER = (ROOT / config.get("unknowns")).resolve()
FENCE = re.compile(r"^\s*```")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HOST_PATH = re.compile(r"/Users/|/home/[a-z][^/]*/|file:///|C:\\\\")


def pages() -> list[Path]:
    """Every page, as `map.json` defines one."""
    return config.pages()


def visible(path: Path) -> list[tuple[int, str]]:
    """The page's lines outside fenced blocks, with their numbers.

    A fence holds examples — a mermaid edge, a shell command — and none of it is
    a link or a heading, so reading it as either invents failures.
    """
    kept: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            kept.append((number, line))
    return kept


def target_of(link: str, page: Path) -> Path | None:
    """The file a relative link names, or None when it names no file here."""
    if link.startswith(("http://", "https://", "#", "mailto:")):
        return None
    path = link.split("#", 1)[0]
    if not path:
        return None
    resolved = (page.parent / path).resolve()
    if path.endswith("/"):
        resolved = resolved / "README.md"
    return resolved


def relative(path: Path) -> str:
    return config.relative(path)


def check_links(problem) -> None:
    """Every relative link resolves; every page is reachable from the front page."""
    edges: dict[Path, set[Path]] = {}
    for page in pages():
        out: set[Path] = set()
        for number, line in visible(page):
            for link in LINK.findall(line):
                target = target_of(link, page)
                if target is None:
                    continue
                if not target.exists():
                    problem(f"BROKEN {relative(page)}:{number}: {link}")
                    continue
                if target.suffix == ".md":
                    out.add(target)
        edges[page.resolve()] = out

    seen: set[Path] = set()
    queue = [config.get_readme()]
    while queue:
        page = queue.pop().resolve()
        if page in seen or page not in edges:
            continue
        seen.add(page)
        queue.extend(edges[page])
    for page in pages():
        if page.resolve() == config.get_readme().resolve() or page.resolve() in seen:
            continue
        try:
            page.resolve().relative_to(REGISTER)
            continue
        except ValueError:
            pass
        problem(f"UNREACHABLE {relative(page)} — no page links to it")


def check_shape(problem) -> None:
    """The length cap, the six sections, numbered names and host paths."""
    front = config.get_readme().resolve()
    for page in pages():
        name = relative(page)
        lines = page.read_text(encoding="utf-8").splitlines()
        if len(lines) > CAP:
            problem(f"TOO LONG {name}: {len(lines)} lines, cap {CAP}")
        for part in page.relative_to(ROOT).parts:
            if part[0].isdigit():
                problem(f"NUMBERED {name}: {part} starts with a digit")
                break
        for number, line in visible(page):
            if HOST_PATH.search(line):
                problem(f"HOST PATH {name}:{number}: {line.strip()[:60]}")
        if page.resolve() == front or name in SHAPELESS:
            continue
        try:
            page.resolve().relative_to(REGISTER)
            continue
        except ValueError:
            pass
        found = tuple(
            line[3:].strip() for _, line in visible(page) if line.startswith("## ")
        )
        if found != SECTIONS:
            problem(f"SHAPE {name}: expected {', '.join(SECTIONS)}; found {', '.join(found) or 'none'}")


def check_generated(problem) -> None:
    """A generated page on disk is what its generator makes today.

    The register is an index of claims that live on other pages. Nothing keeps
    it honest except regenerating it, so the check is run here rather than left
    to a command someone has to remember.
    """
    script = Path(__file__).resolve().parent / "collect_unknowns.py"
    if not script.is_file():
        problem(f"NO GENERATOR {script.name} is missing, so the register cannot be checked")
        return
    result = subprocess.run(
        [sys.executable, str(script), "--check"], capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("STALE"):
            problem(line)
    if result.returncode != 0 and not result.stdout.strip():
        problem(f"STALE {config.get('unknowns')} — the generator failed: {result.stderr.strip()[:120]}")


def check_roots(problem) -> None:
    """A configured page root that is not there, so nothing was actually checked."""
    for path in config.missing_roots():
        problem(f"MISSING ROOT {relative(path)} — map.json names a page root with no directory")


def main() -> int:
    problems: list[str] = []
    check_roots(problems.append)
    check_links(problems.append)
    check_shape(problems.append)
    check_generated(problems.append)
    for entry in problems:
        print(entry)
    print(f"{len(pages())} pages, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
