# MAP.md — the contract for whoever changes this map

This file is the machine-facing half of a mental-model map: what a person or a model reads before adding a page, and what the four checkers in `scripts/` enforce. It was installed by `/sdlc-map`. Edit it, but keep the rules — they are the reason the pages can be trusted.

## What this map is for

A reader should be able to **predict** the system, not tour it. Given where a thing enters and what it carries in, they should be able to say what comes out before opening a line of code. Whatever they cannot predict is the gap a page still has.

## Two kinds of page, and neither does the other's job

| Kind | Answers | Shape |
| --- | --- | --- |
| **A map page**, one per system | where the parts are, which seams exist, which trails lead in, what the invariants forbid, what is abandoned | `shape · seams · trails · invariants (the bog) · deadfall` |
| **A story page**, one per entry point | why a step exists, what enters it, what it leaves behind | `Where it enters → What comes in → the hops → What goes out`, then one `What is code, and what is your policy` table |

Both carry the same six sections, in the same order, because a reader who has never opened a page must still know where to look.

## The rules the checkers hold

1. **One page answers one question.** When it outgrows the line cap, it becomes two pages.
2. **The same six sections on every page, in this order:** `In one paragraph` · `How it works` · `Diagram` · `Where it lives` · `What breaks if you change it` · `Unverified`.
3. **Nothing is copied.** A fact lives in one place — an ADR, the repository's own `ARCHITECTURE.md`, or one page here. Everywhere else links to it. A fact kept twice disagrees within a month.
4. **A citation names a file and a name, never a line.** The file a reader opens and the word they grep. A line number is true for one commit and drifts silently.
5. **Depth is a trace from the entry point.** A page is deep when it names the function at each hop it actually opened.
6. **`Unverified` is labelled**, with the command that would settle it. An untraced arrow is dashed, or not at all.
7. **A hop you did not open does not go in the page.** A story written from memory is a guess wearing a diagram.

## The checkers

```
python3 scripts/run_checkers.py           # every checker this map has, in one command — what CI should run
python3 scripts/check_references.py   # every backticked path resolves; no citation carries a line number
python3 scripts/check_symbols.py      # every code-shaped name on a line naming a real file is still in that file
python3 scripts/check_structure.py    # links resolve, pages reachable, the line cap, the six sections, no numbered names, no host paths, register current
python3 scripts/collect_unknowns.py   # rewrite the unknowns register from every Unverified section
```

`run_checkers.py` is the one to put in CI: it runs the four — the register with `--check`, so the build never edits the tree it is judging — then every script `map.json` → `checkers` names, in order. Exit `0` clean, `1` when a checker reported a problem, `2` when a listed checker is missing, which is drift in the list rather than a finding in the map. `run_checkers.py --self-test` runs the listed checkers alone, each with its plant.

None of them writes into the project either. Each script turns off bytecode caching before it imports its siblings, so a run leaves no `__pycache__` beside the checkers — a gate that littered the tree it judges would put its own debris in the next commit.

All four read **`map.json`** at the project root: where the pages live, where the register goes, which sections a page carries, which repositories a claim may resolve inside, and which pages are exempt from the six sections and why. Every setting is documented at the top of `scripts/map_config.py`, and every one has a default, so a project that moves nothing needs no file.

`repositories` is the one setting worth reading twice. `{"": "."}` resolves a claim against this project. `"auto"` reads every git checkout one and two levels under `workspace`, which is how a map covering several repositories resolves `templates/deploy.yml` after naming that repository on the same line.

**The four scripts carry no traceability tags.** They are installed into projects that know nothing of this repository's feature keys, and a tag naming an unknown key is an error in the validator that reads them. That is also why they live in their own `scripts/` folder with no header: they are infrastructure, not a requirement of yours.

**A fifth may exist.** `/sdlc-tend` can write one — at most once a run — for an invariant a page's bog table says nothing enforces. Those are listed in `map.json` → `checkers` and run after the four, in the order given. They belong to this project rather than to this contract, but one rule carries over: a checker that has never been seen failing is a sentence with an exit code. So each keeps its plant in the file and catches it again on `--self-test`, which is what makes the proof survive the next commit.

## Where the checkers are blind

Say this out loud on any page that leans on them:

- A path resolves against any configured repository, so a path that exists in the **wrong** repository passes.
- The symbol check reads a code-shaped name only on a line that also names a real file; a miss is a question, not always a defect.
- **Nothing here checks that a page is true.** A page can be green and wrong, and only a reader opening the code finds out.

## The document that wins on intent

If this project also carries `.sdlc/`, then `architecture.md` at the docs root (`layout.docs_root`, `.sdlc/docs` when unset) owns intent — the decisions, and the shape that was agreed — and a map page owns the present: the shape the code has, the hops a trail crosses, the invariants that hold, the deadfall. Where both exist, architecture.md wins on intent; a map page says only what that document does not, and links the ADR instead of restating it. See `.sdlc/CONVENTIONS.md` § Map pages.

## What comes next

The action block that ends a turn is defined in `.sdlc/CONVENTIONS.md` § Session handoff when the project carries `.sdlc/`, and that shape wins. Otherwise use this one — paste-ready, never a placeholder:

```
Next:
  [ ] python3 scripts/check_structure.py     the map is current
  [ ] /sdlc-map                              map the next entry point
```
