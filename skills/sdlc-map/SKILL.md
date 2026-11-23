---
name: sdlc-map
description: Map an unfamiliar codebase so a reader can predict it — one page per system (shape, seams, trails, invariants, deadfall) and one story per entry point — installing four checkers that fail when a page drifts. Writes no page for a hop it has not opened, and leaves every unsettled claim labelled with the command that would settle it.
disable-model-invocation: true
user-invocable: true
---

# Skill: sdlc-map

> **Execution model**: you execute the Workflow below — surveying read-only, asking one question, installing the checkers, walking trails, writing pages, then running the checkers. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

Turns a codebase nobody has mapped into pages a reader can navigate and a checker can hold. This is the **maintain** lane: `/sdlc-init` … `/sdlc-review` describe what will be built, this describes what is already running.

**Use this skill when** someone has to understand code they did not write — a new joiner, an on-call engineer at three in the morning, or you, one hour before changing a file. It needs no spec, no `.sdlc/` directory, and no particular language. It reads the source, not the documents about the source.

## The four gates

These are the whole discipline. Everything else in this file is how to carry them out.

1. **Which arrival?** Ask before writing anything: a *new joiner* (needs the order to read in), someone *on call* (needs a symptom lookup), someone *changing a file* (needs one trail), or someone *deciding what to change* (needs the map and the deadfall). The answer chooses the page, and one page per arrival is usually the whole job. Writing for all four at once produces a book nobody reads.
2. **No page from an unopened hop.** A hop goes in a page only if you opened it and can name the file and the function. A story written from memory, from a README, or from another page is a guess wearing a diagram.
3. **Discovery before documentation.** Phase 1 and Phase 2 produce a landscape and a list of open questions, and stop. Pages are written only for what you walked. A system you could not open stays in the "not yet mapped" table with the reason — that table is a finding, not a gap to hide.
4. **Checkers last, and a failure is a finding.** Run the four scripts at the end and report what they print. Never route around a failure by rewording a page until it passes: a page that only passes because the claim was deleted is worse than the failure.

## Before you start

- **Conventions**: if the project carries `.sdlc/CONVENTIONS.md`, read it, and let `.sdlc/CONVENTIONS.md` § Map pages decide what this map may say about a system that already has an architecture document. If it does not, read `assets/MAP.md` — it is the whole contract, and it is what Phase 3 installs at the project root.
- **Read what the project already wrote.** Its `ARCHITECTURE.md`, its ADRs, its own map — and link to them rather than restating. Restating a decision is how two copies come to disagree.
- **Templates**: `assets/templates/map-page.md` and `assets/templates/story-page.md`. They are not in the `sdlc-init` template set: those are normative documents `/sdlc-init` installs into every project, and these describe what is running, so only this skill installs them.
- **Tier-1 approval** is needed for the install in Phase 3, and for creating any page in a directory the project does not already have. Nothing else here writes outside the document directory.
- **Never touch application code.** This skill reads it and writes pages about it. Refactoring, fixing and annotating are other skills' work.

## Workflow

### Phase 1: Survey (read-only)

Enumerate, without editing anything:

- **Entry points** — executables, `main` functions, CLIs, HTTP routes, queue consumers, scheduled jobs, CI pipelines, lifecycle hooks. These are the trails; everything else is reached from them.
- **Layout** — the top two levels of the source tree, and which of them are load-bearing.
- **Existing enforcement** — lint configs, type checkers, the test runner, assert helpers, dependency-rule plugins. This is where the invariants already live. Do not invent rules: collect what the code enforces.
- **Build and ship** — how it is built, packaged and deployed, and where that is decided.
- **Documents** — what the project already explains well enough to link rather than rewrite.

Output: a candidate list of entry points with the file and symbol of each, and a list of what you could not open.

### Phase 2: One question

Ask the arrival from gate 1, then ask *which* entry point matters to them. Do not offer more than three choices; if you cannot narrow it, the map page alone is the right first deliverable and every story waits.

State the target in one or two sentences and get confirmation before Phase 3.

### Phase 3: Install (Tier-1)

Copy into the project, **never overwriting a file that exists** — ask instead, and say what differs:

| Asset | Destination | Purpose |
|---|---|---|
| `assets/scripts/` | `scripts/` | the four checkers, `map_config.py` and `run_checkers.py`, unmodified, so they behave as they were tested |
| `assets/map.json` | `map.json` at the project root | where this project's pages, register and repositories are |
| `assets/MAP.md` | `MAP.md` at the project root | the contract for whoever changes the map next |
| `assets/templates/*.md` | a `templates/` folder beside the pages | the two page shapes |

Then **read `map.json` back and fix it for this project.** Four settings are the ones that make the checkers true here rather than somewhere else:

- `pages` — ask where the pages should live, and default to `_docs/` at the repository root, linked from `README.md`. Never scatter them: a reader needs one place to start.
- `unknowns` — the register, one folder inside the pages.
- `tiers` — leave empty to file the register by the tree's own folders, or name them to group a project whose folders do not read as tiers.
- `repositories` — `{"": "."}` when a page cites this project; `"auto"` with a `"workspace"` when it cites checkouts beside it.

If the project already has an `AGENTS.md`, add one line pointing at `MAP.md` rather than replacing it.

### Phase 4: Walk one trail

For the chosen entry point, follow it to its output and write the story page from `assets/templates/story-page.md`. At each hop: open the file, find the function, and name both. Where you cannot follow — a private dependency, a missing checkout, a service you cannot call — write the hop as unverified with the command that would settle it, or leave the hop out.

One story per trail. Do not summarise three trails into one page to save writing.

### Phase 5: Draw the map page that owns those trails

One page per system, from `assets/templates/map-page.md`:

- **Shape** — the five or six parts a change touches, and what each owns.
- **Seams** — where the system crosses itself, and the rule about crossing, naming whatever enforces it.
- **Trails** — the entry points, each linking to its story. An entry point with no story is deadfall, not a trail.
- **The bog** — the invariants, each with the mechanism that enforces it and the file and symbol where it lives. An invariant nothing enforces is the most valuable row on the page: write "nothing enforces it" and put it under `Unverified`.
- **Deadfall** — abandoned, deprecated, unreferenced, or in no repository, and how you know.

### Phase 6: Verify

Run, from the project root:

1. `python3 scripts/collect_unknowns.py` — writes the register, so the other checkers have one to check
2. `python3 scripts/check_references.py`
3. `python3 scripts/check_symbols.py`
4. `python3 scripts/check_structure.py` — links, reachability, the six sections, the line cap, and a register that has gone stale

Fix what they report, or label the claim `Unverified` with its settling command. Report the counts either way, including zero. If a checker exits `2`, the workspace is wrong, not the page: say so and stop rather than editing a page to please it.

## Phase Transition

> Mapped `<system or entry point>`: `<n>` pages written, `<n>` hops opened, checkers `<passing / n failures reported>`, and `<n>` claims left unverified.

Then deliver the action block (see `.sdlc/CONVENTIONS.md` § Session handoff when the project has one; otherwise `MAP.md` § What comes next). Paste-ready, resolved, one item unless the work justifies two:

```
Next:
  [ ] python3 scripts/check_structure.py     the map is current
```

Offer a second item only when the work earned it: another entry point to trace, or `/sdlc-tend` when the map is complete and the question becomes keeping it true.

After delivering this message, end your turn.

## Error Recovery

Interrupted mid-walk: the written pages are the record — re-read the last one and resume at the hop it stops at. Installed but nothing written → resume at Phase 4. A checker failing on a page you did not write → fix the page only if you can open the code; otherwise report it and leave it.

## Artefact Trail

| File | Location | Purpose |
|---|---|---|
| map page | the pages folder (`_docs/` by default) | one system: shape, seams, trails, bog, deadfall |
| story page | the pages folder | one entry point traced to its output |
| `map.json` | project root | where the pages, the register and the repositories are |
| `MAP.md` | project root | the contract, and where the checkers are blind |
| `scripts/check_*.py`, `scripts/map_config.py`, `scripts/collect_unknowns.py` | project `scripts/` | the deterministic gate |
| the unknowns register | `map.json` → `unknowns` | generated from every `Unverified` section |
