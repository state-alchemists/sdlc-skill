# Rubric: sdlc-tend / unenforced-invariant

Grader evaluates the tree after one `/sdlc-tend` run. Deterministic subset in
`checks.json`.

## The checker

| Check | Pass criteria |
|-------|---------------|
| One, not five | Exactly one checker is written this run |
| Readable pattern | It fails on `import sqlite3` under `src/`, and passes on `src/app.py` importing `src.db.session` |
| Settings, not literals | It asks `map_config` for the project root and paths |
| The plant is kept | `PLANT` names the forbidden import; it is not planted, watched, and deleted |
| Proved both ways | `--self-test` catches the plant, and the plain run on the untouched tree prints clean |
| Stdlib only | No import outside the standard library, so it runs where the four run |

## The map

| Check | Pass criteria |
|-------|---------------|
| Listed once | `map.json` → `checkers` names the script, and nothing else changed in that file |
| Row replaced | The bog row names the script instead of `nothing enforces it` |
| History kept | The `Unverified` entry that carried the claim is settled, not deleted |

## The report

| Check | Pass criteria |
|-------|---------------|
| Findings, not applause | The checker is reported as a change to CI that the user approves, not as a job done |
| One pasteable line | The action item is `python3 scripts/run_checkers.py` |
| Counts | What ran, what it printed, and the date |

## What fails the run

- Writing more than one checker.
- A checker that has never been seen red.
- Editing application code to make the invariant true instead of making it enforced.
- Deleting the bog row rather than replacing it.
