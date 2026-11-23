#!/usr/bin/env python3
"""Fail when a page names a path that no longer exists, or a line number.

Every backticked path in a page is treated as a claim about a repository's
layout, so a refactor that moves a file breaks the build instead of quietly
leaving a wrong page behind.

    python3 scripts/check_references.py

A claim resolves in three ways:

1. **Against a repository named on the same line** — a row naming
   `platform-api` may then say `templates/deploy.yml`, which resolves inside
   that repository's checkout. This is most of a map's citations.
2. **Against the workspace** — a token whose head is a folder under the
   directory named by `workspace` in `map.json`.
3. **Against this project's root** — so a page in `_docs/` may write
   `src/app.py` and mean the file beside the map.

Two shapes are never claims: a token starting with `/` is a host path
(`/etc/hosts`), and one starting with `./` is written relative to a repository
root. Neither says anything about a checkout here.

A line citation (`file.py:126`, `:45-52`) fails the build on purpose. A line
number is true for one commit and drifts silently afterwards, so a page names
the function or method instead, and `check_symbols.py` checks that the name is
still in the file.

Which repositories exist is in `map.json` — see `map_config.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A gate must not write into the tree it judges. Importing the sibling modules
# would leave a `__pycache__` beside the checkers, which is an edit to someone
# else's project and lands in their next commit.
sys.dont_write_bytecode = True

import map_config as config

ROOT = config.ROOT
WORKSPACE = config.get_workspace()
REPOS = config.get_repositories()
PREFIX_ROOTS = config.get("prefix_roots")
SUBROOTS = config.get("subroots")

TOKEN = re.compile(r"`([^`\n]+)`")
URL = re.compile(r"https?://[^\s)\]|]+")
LINE_CITATION = re.compile(r":\d+([,-]\d+)*$")
NOT_A_PATH = ("http://", "https://")
FILE_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def anchors_for(line: str) -> tuple[Path, ...]:
    """The checkouts a line is talking about, named either as a token or a URL.

    `[platform-api](https://…/group/platform-api)` and a bare `platform-api`
    both name a repository; a path written after either is relative to it.
    """
    anchors: list[Path] = []
    for match in URL.finditer(line):
        name = match.group(0).rstrip("/").rsplit("/", 1)[-1]
        if name in REPOS:
            anchors.append(REPOS[name])
    for match in TOKEN.finditer(line):
        token = LINE_CITATION.sub("", match.group(1).strip())
        parts = token.split("/")
        for part in reversed(parts):
            if part in REPOS:
                anchors.append(REPOS[part])
                break
    return tuple(dict.fromkeys(anchors))


def roots_for(token: str) -> tuple[Path, ...]:
    """The roots a claim may resolve under, absent a repository named on its line.

    `prefix_roots` answers a path prefix whose meaning is a lower root: a page
    that writes `pkg/module.py` may mean the module inside `pkg/`, and that is
    the one prefix it shares with a stray directory of the same name.
    """
    for prefix, root in PREFIX_ROOTS.items():
        if token.startswith(prefix):
            return (ROOT / root, WORKSPACE, ROOT)
    return (WORKSPACE, ROOT)


def is_path_shaped(token: str) -> bool:
    """Could this token be a path at all? Says nothing about whether it exists.

    A placeholder inside a package (`artifacts/<stack>/`, `bin/*.sh`) is a shape,
    not a claim about a checkout, so the characters that make it one are refused.
    """
    if not token or token.startswith(NOT_A_PATH):
        return False
    if token.startswith(("-", "/", "./")) or " " in token or "=" in token:
        return False
    if any(mark in token for mark in "*<>{}[]$"):
        return False
    if ":" in token:
        # An image reference (`sonatype/nexus3:latest`) is not a path in a checkout.
        return False
    if token.endswith("/"):
        # A directory named inside a built package (`evidence/`) is a shape, and a
        # bare directory name is not a claim a checkout can answer.
        return False
    head = token.split("/", 1)[0]
    if "." in head:
        # A version or a format id (`release/2`) is not a path.
        return False
    return "/" in token or bool(FILE_EXTENSION.search(token))


def candidates(token: str, page: Path, anchors: tuple[Path, ...] = ()) -> tuple[Path, ...]:
    """Every place a claim could live, most specific first.

    A repository named on the line answers first. A repository that keeps its
    package one level down (`subroots`) is tried inside it too, so a page may
    write `tasks/registry.py` after naming that repository.
    """
    path = LINE_CITATION.sub("", token.strip())
    direct: list[Path] = []
    head, _, rest = path.partition("/")
    if head in REPOS and rest:
        direct.append(REPOS[head] / rest)  # the path is already rooted at the repository
    bases: list[Path] = []
    for anchor in anchors:
        bases.append(anchor)
        for subroot in SUBROOTS:
            bases.append(anchor / subroot)
    bases.extend(roots_for(path))
    bases.append(page.parent)
    joined = (base / path for base in dict.fromkeys(bases))
    return tuple(direct) + tuple(joined)


def resolve(token: str, page: Path, anchors: tuple[Path, ...] = ()) -> Path | None:
    """The first existing candidate for a claim, or None.

    Last resort: the same relative path inside any repository. A page that cites
    a file without naming its repository on that line is still citing a file
    that exists, and the page's own `Where it lives` table carries the
    attribution.
    """
    for candidate in candidates(token, page, anchors):
        if candidate.exists():
            return candidate
    path = LINE_CITATION.sub("", token.strip())
    for repo in REPOS.values():
        if (repo / path).exists():
            return repo / path
    return None


SKIP = {".git", "__pycache__", "node_modules", "vendor", ".venv", "dist", "build", ".mypy_cache"}
_INDEX: dict[Path, list[str]] = {}


def index_of(repo: Path) -> list[str]:
    """Every file in a checkout, relative to it, so a wrong prefix can be named."""
    if repo not in _INDEX:
        paths: list[str] = []
        for path in repo.rglob("*"):
            if any(part in SKIP for part in path.parts):
                continue
            if path.is_file():
                paths.append(path.relative_to(repo).as_posix())
        _INDEX[repo] = paths
    return _INDEX[repo]


def elsewhere(token: str, anchors: tuple[Path, ...]) -> str | None:
    """Where the file really is, when the page wrote its path with the wrong prefix.

    A page saying `adopt-a-namespace.md` when the file is `runbooks/adopt-a-namespace.md`
    is one folder short, not wrong about the file. Naming the real path turns a
    failed check into an edit.
    """
    path = LINE_CITATION.sub("", token.strip())
    for anchor in anchors:
        for known in index_of(anchor):
            if known.endswith("/" + path):
                return known
    return None


def main() -> int:
    if not REPOS:
        print(
            "No repository could be found, so no claim can be resolved and nothing "
            "below would prove anything. Set `repositories` in map.json — a mapping "
            "of name to path, or `auto` with a `workspace` holding the checkouts."
        )
        return 2
    missing: list[str] = []
    numbered: list[str] = []
    unanchored: list[str] = []
    checked = 0
    for page in config.pages():
        text = page.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            anchors = anchors_for(line)
            for match in TOKEN.finditer(line):
                token = match.group(1).strip()
                without_citation = LINE_CITATION.sub("", token)
                if without_citation != token and is_path_shaped(without_citation):
                    numbered.append("%s:%d: %s" % (config.relative(page), number, token))
                token = without_citation
                if not is_path_shaped(token):
                    continue
                if resolve(token, page, anchors) is not None:
                    checked += 1
                    continue
                # A token naming a repository one level down is a reference to
                # that project, not a path in this workspace.
                if token.rsplit("/", 1)[-1] in REPOS:
                    continue
                if anchors or "/" in token:
                    checked += 1
                    real = elsewhere(token, anchors) if anchors else None
                    if real:
                        missing.append(
                            "%s:%d: %s — the file is at %s"
                            % (config.relative(page), number, token, real)
                        )
                    else:
                        missing.append("%s:%d: %s" % (config.relative(page), number, token))
                else:
                    unanchored.append("%s:%d: %s" % (config.relative(page), number, token))

    for entry in missing:
        print("MISSING " + entry)
    for entry in numbered:
        print("LINE-NUMBER " + entry)
    for entry in unanchored:
        print("UNANCHORED " + entry)
    print(
        "%d path claims checked, %d missing, %d carrying a line number, "
        "%d with no repository on their line"
        % (checked, len(missing), len(numbered), len(unanchored))
    )
    return 1 if (missing or numbered) else 0


if __name__ == "__main__":
    sys.exit(main())
