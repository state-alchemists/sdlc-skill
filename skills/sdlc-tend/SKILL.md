---
name: sdlc-tend
description: Re-tend a map that already exists — re-run its four checkers, read every failure back to the code, and settle each page as true, stale or unowned. Fixes only what the code proves (a moved path, a renamed symbol, a heading out of order); anything it cannot prove becomes an open claim with the command that would settle it, never a deleted paragraph.
disable-model-invocation: true
user-invocable: true
---

# Skill: sdlc-tend

> **Execution model**: you execute the Workflow below — running the checkers, triaging their findings against the source, applying the mechanical fixes, and writing the report. Lines that say "run `/sdlc-<other>`" are instructions **for the user**. Deliver the Phase Transition message, then stop.

A map is written once and read for years, and the code underneath it keeps moving. This is the loop that keeps the two together: the same shape as `/sdlc-review` — a deterministic pass that cannot be argued with, then judgement over what a parser cannot see — applied to the map instead of the code.

**Use this skill** on a project that already carries `MAP.md` and `map.json`. To write the map the first time, run `/sdlc-map`.

## What drifts, and what tends it

| The drift | What it looks like | Who fixes it |
|---|---|---|
| A claim that died | a page cites a path that moved, or a symbol that was renamed | the checker names it; you edit the page |
| The tree stopped being a map | a broken link, a page nobody links, a page over the cap, the six sections out of order | the checker names it; you edit the page |
| A page nobody wrote | an entry point the code has and the map does not | you, with `/sdlc-map` on that one entry point |
| A claim nobody settled | the register grew | you, by settling one claim or writing its command |

## The gates

1. **Evidence before edit.** You change a page only after opening the file or the function it talks about. A fix applied because the checker was loud is a guess with a checker's confidence.
2. **Mechanical is yours, judgement is the user's.** A moved path, a renamed symbol, a heading out of order, a link that needs one folder — fix these and say what you changed. Deleting a paragraph, reordering a table, calling an invariant wrong, or deciding an unverified claim no longer matters — ask. The difference is whether the code proves the new text.
3. **Never delete a claim to make a checker green.** A sentence you cannot prove becomes an open claim — moved to `Unverified`, with a `Settle:` command — which puts it in the register where a reader sees it. Deleting it is the one edit that makes the gate pass and the map worse.
4. **A quiet run is a result.** Report the counts the checkers printed, including zero, and the date. "Nothing drifted" is only credible next to what you ran and when.
5. **Do not rewrite the map.** Re-tending is not re-mapping. If a page needs a new shape, that page is re-written by `/sdlc-map` in its own session; here you keep the map true, and you name the page that has outgrown itself.

## Before you start

- **Conventions**: read `.sdlc/CONVENTIONS.md` if it exists, and in particular § Map pages — it decides what a map page may say about a system that also has an architecture document. Otherwise read `MAP.md` at the project root: it holds the page shapes and where the checkers are blind.
- **Config**: `map.json` names the pages folder, the register and the repositories. Read it before you run anything: a checker pointed at the wrong folder reports a clean tree.
- **Tier**: this is **Tier-2** — one batched approval for the set of page edits, because each edit is small and reversible. A change to `map.json`, or deleting a page, is Tier-1.
- **Never touch application code.** Tend repairs pages about the code. If the code is what is wrong, say so and stop.

## Workflow

### Phase 1: Locate and read the map

Find `MAP.md` and `map.json`. If either is missing, say which and stop — `/sdlc-map` writes them; tend cannot tend what is not there.

Read the map page that owns the area the user named, and list the pages with their dates:

```bash
git log -1 --format='%cs %s' -- <a page>
```

### Phase 2: The deterministic pass

Run all four, from the project root, and keep the output:

1. `python3 scripts/collect_unknowns.py --check` — is the register what its generator makes today?
2. `python3 scripts/check_references.py`
3. `python3 scripts/check_symbols.py`
4. `python3 scripts/check_structure.py`

A checker exiting `2` means it could not resolve anything — a workspace or config problem, not a map problem. Report it and stop rather than editing a page to please it.

### Phase 3: Triage one finding at a time

For each line the checkers printed, open what it names and decide which of four things it is:

| The finding | The question to answer with the code |
|---|---|
| `MISSING <page>: <path>` | Did the file move, get renamed, or get deleted? `git log --follow` answers the first two. |
| `STALE <page>: <symbol>` | Did the function get renamed, or is the page quoting something that was never there? |
| `BROKEN` / `UNREACHABLE` / `SHAPE` / `TOO LONG` | What is the page's own question now — is it two pages, or one page with the wrong heading? |
| `STALE <register>` | Which claim moved? Read the page, not the register. |
| `LINE-NUMBER` | Which name does the page mean? Replace the number with the function or field. |

Write the decision down before you act: *"the file moved to `<path>`"*, *"the function is now `<name>`"*, *"this claim is wrong and cannot be replaced from the code"*. Each one becomes either an edit, an open claim, or a question for the user.

### Phase 4: Apply the mechanical fixes

Edit only the pages the triage proved. For each:

- Replace a moved path with the real one the checker named.
- Replace a renamed symbol with the name in the file, and check the sentence still reads true with the new name.
- Fix a link, or move a page into the folder that makes it reachable.
- Reorder the six sections, or split a page that outgrew the cap — and when you split it, link both halves and say which question each answers.

Then re-run Phase 2. Report the count before and after: a page edited until the checker went quiet, with no understanding of why it complained, is the failure this skill exists to prevent.

### Phase 5: Judge what the checkers cannot

Three questions, answered from the code, not from the pages:

1. **Is there an entry point the map does not have?** Re-run the survey in `/sdlc-map` Phase 1 — the same method, the same places — and diff the result against the `Trails` table of the owning map page. New entry points are the drift that no checker can see, because nothing is broken: the map is merely incomplete.
2. **Is an invariant still enforced?** For each row of the bog, open what the row names as its enforcement. A row that says `nothing enforces it` and is still there after two tends is a decision nobody has made — put it to the user as a question, in one line.
3. **Is the deadfall still dead?** A file listed as abandoned that is imported again belongs back in the shape, not in the deadfall.

Each answer becomes a page edit, an open claim, or a named next step. Do not invent a fourth kind.

### Phase 6: Report, and leave the register honest

Write the report as a short message, not a file — the map's own pages and the register are the durable record:

```
Tended <project> on <date>
  checkers      <what each printed>
  fixed         <n> pages: <one line each>
  opened        <n> claims, each with its Settle command
  unowned       <the entry points with no page>
  needs you     <the decisions only the user can make>
```

Regenerate the register as the last act, so the pages and the index agree:

```bash
python3 scripts/collect_unknowns.py
```

## Phase Transition

> Tended `<project>` on `<date>`: `<n>` findings, `<n>` fixed from the code, `<n>` claims opened, `<n>` entry points still unowned.

Then deliver the action block (see `.sdlc/CONVENTIONS.md` § Session handoff when the project has one; otherwise `MAP.md` § What comes next). Paste-ready, and at most two items:

```
Next:
  [ ] /sdlc-map                              <the entry point with no page>
```

Offer `[ ] settle <one claim> — <its command>` as the second item only when a claim you opened is worth closing now. Do not list the register.

After delivering this message, end your turn.

## Error Recovery

Interrupted mid-tend: the pages on disk are the record. Re-run Phase 2 — the checkers are idempotent — and skip any finding you already fixed. If `map.json` names a folder that does not exist, stop: you are in the wrong project root, or the map was installed elsewhere.

## Artefact Trail

| File | Location | Purpose |
|---|---|---|
| the pages it edited | the pages folder named by `map.json` | the claims brought back to the code |
| the unknowns register | `map.json` → `unknowns` | regenerated, so it counts what the pages now say |
| `map.json` | project root | read, and changed only with approval |
| `scripts/check_*.py` | project `scripts/` | the deterministic pass; never edited to pass itself |
