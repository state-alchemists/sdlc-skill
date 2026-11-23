# Input: sdlc-tend / unenforced-invariant

## Initial state

A mapped project, `MAP.md` and `map.json` at the root, pages under `_docs/`.
This is the second `/sdlc-tend` run on the same tree.

`_docs/systems/storage.md` carries a bog table with one row that has survived
two runs:

```markdown
| The invariant | What enforces it |
| --- | --- |
| No module under `src/` imports `sqlite3` directly; every query goes through `src/db/session.py`. | nothing enforces it |
```

The user asked for the third answer: write the checker.

## Naming convention (this project)

`scripts/check_<what>.py`. For this invariant the name is
`scripts/check_no_direct_sqlite.py`.

## `map.json` (as shipped)

```json
{
  "pages": ["_docs"],
  "unknowns": "_docs/unknowns",
  "readme": "README.md",
  "checkers": []
}
```

## What the deterministic pass prints

```
$ python3 scripts/run_checkers.py
== collect_unknowns.py --check
0 problems
== check_references.py
0 problems
== check_symbols.py
0 problems
== check_structure.py
0 problems

4 checker(s), 0 failed

$ python3 scripts/run_checkers.py --self-test
No map checkers were listed; nothing to run.
```

## The tree the checker must read

```
src/db/session.py        # the only file that may import sqlite3
src/app.py               # imports src.db.session
scripts/map_config.py    # the settings reader every checker uses
```
