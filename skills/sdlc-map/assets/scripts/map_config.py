#!/usr/bin/env python3
"""What this project's map looks like, read from `map.json` for all four checkers.

The four checkers are one gate: a path that moved, a name that was renamed, a
tree that stopped being a map, a register that has gone stale. They read their
project-specific facts here, once, because a checker written against one
repository's folders is a checker that passes in exactly one repository.

    map.json                              at the project root, optional
    python3 scripts/check_references.py   and the other three

Every key has a default, and the defaults describe the smallest map this can
serve: pages under `_docs/`, the register in `_docs/unknowns/`, the six
sections, one repository — the project itself. A project that keeps its pages
somewhere else, groups them into tiers, or cites checkouts beside it, says so:

    {
      "pages": ["_docs"],
      "unknowns": "_docs/unknowns",
      "readme": "README.md",
      "line_cap": 150,
      "sections": ["In one paragraph", "…", "Unverified"],
      "checkers": [],
      "shapeless": {"_docs/index.md": "an index, not a page"},
      "tiers": ["systems", "stories"],
      "repositories": {"": "."},
      "subroots": [],
      "prefix_roots": {},
      "workspace": null,
      "exclude": [".git", "node_modules"]
    }

`repositories` is either a mapping of name to path, relative to the project
root, or the string `auto` — every git checkout one and two levels under
`workspace`, for a workspace that holds other repositories beside this one.

`prefix_roots` names a path prefix that is written against a lower root: a page
saying `pkg/module.py` may mean the module inside `pkg/`, so `{"pkg/": "pkg"}`
resolves it there first. `subroots` are the folders inside a cited repository
that its own code lives under, so a page may write `tasks/registry.py` after
naming a repository that keeps that package one level down.

`shapeless` exempts a page from the six sections — a map, an index, a look-up
table answers its own question with its own shape — and its value is why, so
that an exemption is argued for rather than merely left out.

`checkers` lists extra scripts a tend run wrote for this project. They run
after the four, in the order given. Listed rather than discovered, so a checker
added once is still run later; a name here with no file behind it is drift.

Stdlib only; Python 3.8+.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "map.json"

SECTIONS = (
    "In one paragraph",
    "How it works",
    "Diagram",
    "Where it lives",
    "What breaks if you change it",
    "Unverified",
)

DEFAULTS = {
    "pages": ["_docs"],
    "unknowns": "_docs/unknowns",
    "readme": "README.md",
    "line_cap": 150,
    "sections": list(SECTIONS),
    "checkers": [],
    "shapeless": {},
    "tiers": [],
    "repositories": {"": "."},
    "subroots": [],
    "prefix_roots": {},
    "workspace": None,
    "exclude": [".git", "node_modules", ".venv", "vendor", "dist", "build", "__pycache__"],
}


def load() -> dict:
    """Every setting, defaults overlaid with `map.json`.

    An unknown key stops the run instead of being ignored: a misspelt `"page"`
    would otherwise leave the checker reading `_docs/`, reporting a clean tree,
    and teaching its reader that the gate is green.
    """
    settings = json.loads(json.dumps(DEFAULTS))
    if not CONFIG_PATH.exists():
        return settings
    try:
        given = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except ValueError as error:
        sys.exit("map.json is not valid JSON: %s" % error)
    if not isinstance(given, dict):
        sys.exit("map.json must hold an object")
    unknown = sorted(set(given) - set(DEFAULTS))
    if unknown:
        sys.exit(
            "map.json names settings this checker does not read: %s (known: %s)"
            % (", ".join(unknown), ", ".join(sorted(DEFAULTS)))
        )
    settings.update(given)
    if isinstance(settings["pages"], str):
        settings["pages"] = [settings["pages"]]
    return settings


SETTINGS = load()


def get(name: str):
    """One setting, already defaulted."""
    return SETTINGS[name]


def relative(path: Path) -> str:
    """A path as a page names it: relative to the project root, POSIX."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def page_roots() -> list[Path]:
    """The directories whose markdown is a page."""
    return [ROOT / name for name in SETTINGS["pages"]]


def missing_roots() -> list[Path]:
    """A configured page root with no directory behind it.

    Reported rather than skipped: a checker that finds nothing to check prints
    a clean summary, and an empty map is the largest thing it could hide.
    """
    return [path for path in page_roots() if not path.is_dir()]


def get_readme() -> Path:
    """The page every other page must be reachable from."""
    return ROOT / SETTINGS["readme"]


def get_checkers() -> list[str]:
    """Extra checker scripts this project wrote, run after the four.

    Listed rather than discovered, so a checker one tend run wrote is still run
    by the next. A name here with no file behind it is drift, and the run stops
    on it rather than passing quietly over a gate that no longer exists.
    """
    return list(SETTINGS["checkers"])


def is_excluded(path: Path) -> bool:
    """Is this path inside a folder no page lives in?"""
    excluded = set(SETTINGS["exclude"])
    return any(part in excluded for part in path.parts)


def pages() -> list[Path]:
    """Every page: the markdown under each page root, plus the front page.

    The front page is included even when it sits above the page roots — it is
    the entry a reader arrives at, so its links and its length are claims like
    any other's.
    """
    found: dict[Path, Path] = {}
    for root in page_roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            try:
                inside = path.relative_to(ROOT)
            except ValueError:
                inside = path
            if not is_excluded(inside):
                found[path.resolve()] = path
    readme = get_readme()
    if readme.is_file():
        found[readme.resolve()] = readme
    return sorted(found.values(), key=relative)


def tier_of(page: Path) -> str:
    """The tier a page is filed under: its first folder below its page root."""
    for root in page_roots():
        try:
            parts = page.resolve().relative_to(root.resolve()).parts
        except (ValueError, OSError):
            continue
        if len(parts) > 1:
            return parts[0]
        return "root"
    return "root"


def get_tiers() -> list[str]:
    """The groups the unknowns register is filed under.

    Configured when the project names them, so an empty tier can still be
    declared. Otherwise the tiers are the ones the tree actually has, which
    means a project that never thought about tiers gets a register in the shape
    of its own folders.
    """
    if SETTINGS["tiers"]:
        return list(SETTINGS["tiers"])
    return sorted({tier_of(page) for page in pages() if page != get_readme()})


def get_workspace() -> Path:
    """The directory claims resolve under: the project, unless it says otherwise."""
    workspace = SETTINGS["workspace"]
    return (ROOT / workspace).resolve() if workspace else ROOT


def project_names(repo: Path) -> list[str]:
    """The project names a checkout answers to, read from its `origin` remote."""
    try:
        config = (repo / ".git" / "config").read_text(encoding="utf-8")
    except OSError:
        return []
    names: list[str] = []
    in_origin = False
    for line in config.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_origin = stripped == '[remote "origin"]'
            continue
        if not in_origin or not stripped.startswith("url"):
            continue
        url = stripped.split("=", 1)[-1].strip()
        name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        if name.endswith(".git"):
            name = name[: -len(".git")]
        if name:
            names.append(name)
    return names


def get_repositories() -> dict[str, Path]:
    """Every checkout a claim may resolve inside, by folder name and project name.

    A checkout answers to its folder name and, when it has one, to the project
    name in its `origin` remote — a folder is one machine's arrangement, and
    the project is the thing that exists. A folder name wins, so a checkout
    cloned under its own name is never shadowed by another's remote.
    """
    setting = SETTINGS["repositories"]
    if setting != "auto":
        return {name: (ROOT / path).resolve() for name, path in setting.items()}
    workspace = get_workspace()
    excluded = set(SETTINGS["exclude"])
    checkouts: list[Path] = []
    for outer in sorted(workspace.iterdir()):
        if not outer.is_dir() or outer.name.startswith("."):
            continue
        if (outer / ".git").exists():
            checkouts.append(outer)
        if outer.name in excluded or outer.resolve() == ROOT.resolve():
            continue
        for inner in sorted(outer.iterdir()):
            if inner.is_dir() and (inner / ".git").exists():
                checkouts.append(inner)
    found = {path.name: path for path in checkouts}
    for path in checkouts:
        for name in project_names(path):
            found.setdefault(name, path)
    return found
