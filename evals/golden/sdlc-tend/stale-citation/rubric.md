# Rubric: sdlc-tend / stale-citation

Grader evaluates the tree after one `/sdlc-tend` run. Deterministic subset in
`checks.json`.

## The page

| Check | Pass criteria |
|-------|---------------|
| Path corrected | `src/loader.py` is replaced by `src/config/loader.py`, in the prose and in the Where-it-lives table |
| Evidence first | The replacement is the path the code has, not a guess from the checker's line |
| Nothing deleted | The read-only-mount claim is still on the page, under `Unverified`, with its `Settle:` command |
| The page survives | A fix never means emptying a page or deleting it |
| Sentence still true | "It treats a relative path as relative to the working directory" still describes `load_config` after the move |

## The register

| Check | Pass criteria |
|-------|---------------|
| Regenerated last | `_docs/unknowns/systems.md` exists and is what `collect_unknowns.py` would write |
| Counted once | The read-only-mount claim appears once, not twice |

## The report

| Check | Pass criteria |
|-------|---------------|
| Counts, including zero | Names what ran and what each printed, and the date |
| Fixed, not silent | Says which page changed and why, in one line |
| No fourth kind | Each answer is an edit, an open claim, or a named next step |

## What fails the run

- Editing `map.json` to silence a finding.
- Touching `src/` — the loader moved, and that is not tend's to fix.
- Deleting the unproven claim to make the checker quiet.
- Rewriting the page into a new shape; re-mapping is `/sdlc-map`'s job.
