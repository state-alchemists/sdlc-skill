---
name: sdlc-migrate
description: Migrate an existing SDLC project to the current layout and conventions. Consolidates legacy root-level artifacts (docs/, requirements/, rules.md) under .sdlc/, installs the validator and conventions file, re-keys traceability tags, and flags content that needs follow-up. Use when skills report "legacy layout detected" or after upgrading the plugin.
disable-model-invocation: true
user-invocable: true
---
# Skill: sdlc-migrate

> **Execution model**: You (the LLM) execute the **Workflow** sections below — detecting the current layout, planning moves, obtaining approval, and performing the migration. Lines that say "run `/sdlc-<other>`" are **instructions to the user**, not to you. When this skill ends, deliver the Phase Transition message and stop — do not invoke another skill yourself.

Brings a project created with an earlier version of these skills up to the current layout and conventions **without losing git history or hand edits**. It moves artifacts, never rewrites their meaning; content migrations that require judgement (merging old-format specs, rewriting the deprecated EARS dialect) are detected and handed off to the right skill rather than done blindly here.

## What changed across versions (the migrations this skill handles)

| Concern | Legacy | Current |
|---------|--------|---------|
| Steering docs | `docs/product.md`, `docs/tech.md`, `docs/test-strategy.md` | `.sdlc/docs/…` |
| Architecture | `docs/architecture.md` | `.sdlc/docs/architecture.md` |
| ADRs | `docs/adr/ADR-*.md` | `.sdlc/docs/adr/ADR-*.md` |
| Requirements | `requirements/problem-brief.md`, `requirements/entity-dictionary.md` | `.sdlc/requirements/…` |
| Rules | `rules.md` (root) | `.sdlc/rules.md` |
| Specs | `specs/<slug>/spec.md` (or `requirements.md` + `design.md`) | `.sdlc/specs/<slug>/spec.md` |
| Test plans | `tests/<slug>/test-plan.md` | `.sdlc/tests/<slug>/test-plan.md` |
| Reviews | `reviews/<slug>/…` | `.sdlc/reviews/<slug>/…` |
| Validator + conventions | (absent) | `.sdlc/tools/sdlc-validate.py`, `.sdlc/CONVENTIONS.md` |
| Spec format | `requirements.md` + `design.md` per feature | single merged `spec.md` |
| EARS dialect | `ALWAYS SHALL`, `AS … THEN`, `UNLESS … THEN`, `WHERE`=state | canonical: ubiquitous / WHEN / WHILE / WHERE=optional-feature / IF…THEN |
| Traceability tags | `@sdlc REQ-003` (unkeyed) | `@sdlc <KEY>:REQ-003` (feature-keyed) |

## Conventions (read once, apply throughout)

- **Moves are Tier-1 (explicit approval)**: present the complete move plan and get a single affirmative ("yes" / "ok" / "approved") before touching the filesystem. Anything else is a change request.
- **Preserve history**: in a git repo, move with `git mv`. Outside git, `mkdir -p` the destination then `mv`. Never copy-then-leave-original (that creates the split-brain this skill exists to prevent).
- **Never mix layouts**: after migration, no SDLC artifact remains at a legacy root path.
- **Don't rewrite meaning**: this skill relocates files and mechanically re-keys tags. It does NOT merge spec content or rewrite requirements — it detects those needs and routes them to `/sdlc-document` or `/sdlc-quickfix`.
- **Idempotent**: safe to re-run. If the project is already on the current layout, report "nothing to migrate" and offer only the missing scaffolding (validator / conventions).

## Workflow

### Phase 1: Detect Current Layout

List the repo root, `docs/`, `docs/adr/`, `requirements/`, `specs/`, `tests/`, `reviews/`, and `.sdlc/` (each only if present). Build an inventory of every SDLC artifact and where it currently lives. Classify the project:

- **Already current**: artifacts live under `.sdlc/`, `.sdlc/CONVENTIONS.md` and `.sdlc/tools/sdlc-validate.py` exist → skip to Phase 5 (offer only missing scaffolding), or report "nothing to migrate."
- **Legacy paths**: steering docs / requirements / rules at root → full migration.
- **Partial**: some under `.sdlc/`, some at root (e.g. `.sdlc/rules.md` exists but `docs/` and `requirements/` are at root — the common case for projects bootstrapped mid-transition) → migrate only the legacy-located artifacts.

Also detect **content migrations** (reported in Phase 4, not auto-applied):
- **Old-format specs**: any `requirements.md` and/or `design.md` under a feature directory with no `spec.md` → needs `/sdlc-document <slug>` to merge.
- **Deprecated EARS**: grep specs for `ALWAYS SHALL`, `\bAS\b .* THEN`, `\bUNLESS\b`.
- **Unkeyed tags**: grep `src/`/`tests/` for `@sdlc REQ-`, `IMPLEMENTS: REQ-`, `COVERS: REQ-` with no `KEY:` prefix.

### Phase 2: Build the Move Plan

Produce an explicit source → destination table for every file to move. Resolve feature slugs by slugifying existing directory names (lowercase, `[a-z0-9-]`, collapse `-`). For specs that exist as `requirements.md` + `design.md`, plan to move BOTH under `.sdlc/specs/<slug>/` (keeping their names for now — the merge to `spec.md` is a separate `/sdlc-document` step).

Example plan (comparator-style project):

```
docs/product.md           → .sdlc/docs/product.md
docs/tech.md              → .sdlc/docs/tech.md
docs/test-strategy.md     → .sdlc/docs/test-strategy.md
docs/architecture.md      → .sdlc/docs/architecture.md
docs/adr/ADR-001.md … 009 → .sdlc/docs/adr/ADR-*.md
requirements/*.md         → .sdlc/requirements/*.md
(rules.md already at .sdlc/rules.md — no move)
+ install .sdlc/tools/sdlc-validate.py
+ install .sdlc/CONVENTIONS.md
+ update AGENTS.md + README.md cross-references (docs/… → .sdlc/docs/…)
```

Present the full plan. This is the **Tier-1 approval gate** — write nothing until the user says yes.

### Phase 3: Execute Moves

On approval:
1. Create destination directories (`mkdir -p` or let `git mv` create them).
2. Move each file: `git mv <src> <dst>` in a git repo (preserves history and stages the move), else `mv`. Move whole directories where the entire directory relocates (`git mv docs/adr .sdlc/docs/adr`).
3. Remove now-empty legacy directories.
4. **Update cross-references** (Tier-1, part of the same approved operation):
   - `AGENTS.md`: repoint the directory map (`docs/product.md` → `.sdlc/docs/product.md`, etc.) and add the validator row.
   - `README.md`: repoint any documentation links that point at the moved paths.
   - Source/test files: if specs moved, fix `GENERATED FROM SPEC: <oldpath>` header lines to the new `.sdlc/specs/<slug>/spec.md` path. (This is a path rewrite, not a tag re-key — re-keying is Phase 4.)

### Phase 4: Install Scaffolding & Report Residual Content Migrations

1. **Install the validator**: copy the `sdlc-validate.py` bundled alongside this skill to `.sdlc/tools/sdlc-validate.py` (if absent). If the bundled file isn't reachable from your runtime, tell the user and link the repo copy.
2. **Install conventions**: if `.sdlc/CONVENTIONS.md` is absent, write it (use the template in `sdlc-init` Phase 5).
3. **Run the validator** read-only: `python3 .sdlc/tools/sdlc-validate.py` and capture its findings.
4. **Report residual content migrations** the move alone didn't fix, with the exact follow-up command. Offer to do the safe mechanical ones now (with approval); route the judgement ones:
   - **Unkeyed traceability tags** → mechanical re-key: for each feature, read its `spec.md` to find the declared (or default) Feature Key, then rewrite `@sdlc REQ-NNN` → `@sdlc <KEY>:REQ-NNN`, `IMPLEMENTS: REQ-…` → `IMPLEMENTS: <KEY>:REQ-…`, `COVERS: …` likewise. If a feature has no `**Feature Key:**` line, add one (default: uppercased slug) — this is a Tier-1 edit to the spec; present it. Re-run the validator after.
   - **Deprecated EARS dialect** in specs → judgement: do NOT silently rewrite requirement meaning. Recommend `/sdlc-document <slug>` (to re-derive a canonical spec from code) or `/sdlc-quickfix <slug>` (to restate specific requirements). List the offending `REQ-*` lines and the suggested canonical form per the migration map in `.sdlc/CONVENTIONS.md`.
   - **Old-format specs** (`requirements.md` + `design.md`, no `spec.md`) → recommend `/sdlc-document <slug>`, which detects the old format and merges it into `spec.md` (it already has a dedicated path for this).

### Phase 5: Verify

Run `python3 .sdlc/tools/sdlc-validate.py` once more and present the summary. Migration of *paths and scaffolding* is complete when: no SDLC artifact remains at a legacy root, the validator and conventions file are installed, and cross-references resolve. Remaining validator WARN/ERROR about EARS dialect or unkeyed tags are the content follow-ups from Phase 4 — list them with their routing.

## Phase Transition

Once moves are done, scaffolding is installed, and the validator has been run, this skill is done. **Do not invoke another skill yourself.** Tell the user (paraphrase as needed), filling in the residual items:

> Migration complete: artifacts consolidated under `.sdlc/`, validator installed at `.sdlc/tools/sdlc-validate.py`, conventions at `.sdlc/CONVENTIONS.md`. Validator summary: {N errors, M warnings}.
> Residual content migrations (each in a fresh chat):
> - {If old-format specs:} Run `/sdlc-document <slug>` to merge `requirements.md` + `design.md` into `spec.md`.
> - {If deprecated EARS:} Run `/sdlc-document <slug>` or `/sdlc-quickfix <slug>` to restate the listed requirements in canonical EARS.
> - {If validator still flags gaps:} address them, then re-run the validator.
> Otherwise the project is fully on the current layout.

After delivering this message, end your turn.

## Error Recovery

If interrupted mid-move:
- Re-run `/sdlc-migrate` — Phase 1 re-inventories and Phase 2 only plans the moves still pending. The skill is idempotent.
- In a git repo, `git status` shows staged moves; unfinished moves can be completed or `git restore`d. Prefer completing forward over reverting.

## Artefact Trail

| File | Location | Purpose |
|------|----------|---------|
| (moved artifacts) | `{root}/.sdlc/…` | Relocated steering docs, ADRs, requirements, specs, reviews |
| `sdlc-validate.py` | `{root}/.sdlc/tools/sdlc-validate.py` | Installed validator |
| `CONVENTIONS.md` | `{root}/.sdlc/CONVENTIONS.md` | Installed conventions reference |
