# Input: sdlc-tend / stale-citation

## Initial state

A project that was mapped three months ago. It has `MAP.md` and `map.json` at the
root, pages under `_docs/`, and the register at `_docs/unknowns/`. The user runs
`/sdlc-tend` in a fresh chat, naming nothing.

Since the map was written, one module moved: `src/loader.py` became
`src/config/loader.py`. Nothing else changed.

## `map.json` (as shipped)

```json
{
  "pages": ["_docs"],
  "unknowns": "_docs/unknowns",
  "readme": "README.md",
  "checkers": []
}
```

## `_docs/systems/loader.md` (excerpt)

```markdown
# The loader

## In one paragraph

`load_config` reads a path and hands back the parsed contents.

## How it works

The loader is `load_config` in `src/loader.py`. It treats a relative path as
relative to the working directory.

## Where it lives

| What | Repository | Path |
| --- | --- | --- |
| the loader | this project | `src/loader.py` |

## What breaks if you change it

| Change | Which way it breaks | How you would find out |
| --- | --- | --- |
| the return type | every caller that indexes it | the test suite |

## Unverified

- **Nobody has tried a read-only mount.** Settle: run the suite against one.
```

## What the deterministic pass prints

```
$ python3 scripts/check_references.py
MISSING _docs/systems/loader.md: src/loader.py
1 problem

$ python3 scripts/check_symbols.py
0 problems

$ python3 scripts/check_structure.py
0 problems
```

## The user's answer to the Phase 5 question

There is no entry point the map lacks, and no bog row needs a decision this run.
