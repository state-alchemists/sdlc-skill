#!/usr/bin/env python3
"""Report a page that names a symbol the code no longer has.

`check_references.py` catches a file that moved. This catches a name that was
renamed: a page saying the package writer lives in `tasks/package.py` and is
called `digest_list` reads perfectly after the function becomes
`write_digest_list`, and nobody notices until someone opens the file.

A symbol is a backticked token that looks like code — an underscore, a dot, a
trailing `()`, or camelCase — and at least five characters long. Every such
token on a line that also names a real file is looked for in that file's text.

    python3 scripts/check_symbols.py            # report, exit 0
    python3 scripts/check_symbols.py --strict   # exit 1 on any miss

A miss is not always a defect: an environment variable set by a template, or a
name the page is quoting from a decision record, will not be in the file. Read
each one before changing a page.

Which files a claim resolves inside is in `map.json` — see `map_config.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import check_references as refs
import map_config as config

LINE_CITATION = re.compile(r":\d+(-\d+)?$")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(\(\))?$")
EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def looks_like_code(token: str) -> bool:
    """An identifier a reader could type into a grep, not an English word."""
    if len(token) < 5 or not IDENTIFIER.match(token):
        return False
    body = token.rstrip("()")
    if EXTENSION.search(body):
        return False
    if "_" in body or "." in body:
        return True
    return any(c.isupper() for c in body) and any(c.islower() for c in body)


def resolve(token: str, page: Path) -> Path | None:
    """The file a backticked path names, or None when it names no file at all.

    A host path (`/etc/hosts`) and a path written relative to a repository root
    (`./render.py`) are skipped, for the same reason the path check skips them:
    joining them onto a root would either escape it or invent a file.
    """
    path = LINE_CITATION.sub("", token)
    if path.startswith(("/", "./")) or "/" not in path:
        return None
    for base in refs.roots_for(path) + (page.parent,):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    if not refs.REPOS:
        print(
            "No repository could be found, so no name can be checked and nothing "
            "below would prove anything. Set `repositories` in map.json — a mapping "
            "of name to path, or `auto` with a `workspace` holding the checkouts."
        )
        return 2
    misses: list[str] = []
    checked = 0
    for page in config.pages():
        lines = page.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            tokens = [m.group(1).strip() for m in refs.TOKEN.finditer(line)]
            files = {token: resolve(token, page) for token in tokens}
            files = {token: path for token, path in files.items() if path is not None}
            if not files:
                continue
            bodies = {
                token: path.read_text(encoding="utf-8", errors="replace")
                for token, path in files.items()
            }
            for token in tokens:
                if token in files or not looks_like_code(token):
                    continue
                name = token.rstrip("()")
                checked += 1
                if not any(name in body for body in bodies.values()):
                    misses.append(
                        "%s:%d: `%s` is in none of %s"
                        % (
                            config.relative(page),
                            number,
                            token,
                            ", ".join(config.relative(path) for path in files.values()),
                        )
                    )

    for entry in misses:
        print("STALE " + entry)
    print("%d symbols checked, %d not found" % (checked, len(misses)))
    return 1 if (misses and strict) else 0


if __name__ == "__main__":
    sys.exit(main())
