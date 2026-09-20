# LANDSCAPE.md — how sdlc-skill compares

Where this project sits among spec-driven development (SDD) tools, what it does that they do not, and where they are ahead. Surveyed September 2026. Sources are linked at the end.

Everything here is about *positioning*. Bugs and internal inconsistencies do not belong in this file — they belong in the issue tracker or in a fix.

---

## The field

| | Artifact model | Notation | Constitution | Steering docs | Change/delta path | Code↔spec traceability | Deterministic gate | Distribution |
|---|---|---|---|---|---|---|---|---|
| **sdlc-skill** | one `spec.md` per feature (requirements + design + test plan) | canonical EARS | `rules.md`, numbered `RULE-*` + override log | `product` / `tech` / `test-strategy` | `/sdlc-quickfix` delta, promoted into the spec | **`IMPLEMENTS:` / `COVERS:` / `@sdlc`, key-namespaced** | **`sdlc-validate.py`, exit 2 on error** | 7 chat skills + installer (user- or project-scoped) |
| **GitHub Spec Kit** | spec dir per feature + `plan.md` / `tasks.md` | prose in structured templates | `/speckit.constitution` → `constitution.md` | — | re-run `/speckit.specify` | — | `/speckit.analyze` — LLM cross-artifact analysis | `specify` CLI, 30+ agents |
| **AWS Kiro** | `requirements.md` + `design.md` + `tasks.md` per spec | **EARS** acceptance criteria | — | `.kiro/steering/{product,tech,structure}.md` | edit the spec | — | — | IDE, credit-metered, file-save hooks |
| **OpenSpec** | one living spec per capability | prose requirements | — | — | **delta specs ADDED/MODIFIED/REMOVED**, merged by `openspec archive` | — | `openspec validate` — structural | CLI, agent-agnostic |
| **BMAD-METHOD** | PRD + architecture + sharded stories | agile personas | — | — | brownfield `document-project` | — | — | npm, agent personas |
| **Agent OS** | standards + specs | prose | standards injection | yes | — | — | — | install script |
| **OpenFastTrace / Doorstop / StrictDoc** | one item per requirement, permanent IDs | formal | — | — | — | **`needs:` / `covers:` across levels, version-suspect links** | **yes — it is the whole product** | CLI / Maven / Gradle |

The first six are agent-facing SDD tools. The last row is the requirements-engineering lineage from safety-critical software; it is in the table because it is where this project's distinctive idea comes from.

---

## What sdlc-skill does that the others do not

**1. It traces requirements into source code, and fails a build on the gap.**
Spec Kit, Kiro, OpenSpec and BMAD all stop at "the spec exists and the agent read it". Here, generated code carries `IMPLEMENTS:` / `COVERS:` / `@sdlc` headers keyed to requirement IDs, and `sdlc-validate.py` parses them back and exits `2` when a requirement has no implementation, a tag points at nothing, or an ID was recycled. That is the OpenFastTrace/Doorstop discipline applied to an LLM workflow, and no other agent-facing tool in the field is doing it.

**2. Its verdicts are deterministic.**
`/sdlc-review` maps validator ERROR, any FAIL check, or an unrecorded rule violation to REQUEST CHANGES — a rule, not an opinion. Spec Kit's `/speckit.analyze` is an LLM pass over the artifacts: useful, advisory, not reproducible twice. A team that does not want a model's judgement in its merge gate can use this one.

**3. Both ends of the traceability chain are checked.**
Downstream: `REQ-*` → code and tests. Upstream: a requirement's `(AC-NNN)` citation is validated against `problem-brief.md`, so an acceptance criterion renumbered or dropped upstream surfaces as an error instead of rotting silently. No other tool in the table validates the story→criterion→requirement half at all.

**4. Feature keys keep per-feature IDs from colliding.**
Every spec declares a globally unique `**Feature Key:**`, and IDs are written `AUTH:REQ-003`. Parallel features can touch the same source file without their `REQ-001`s meaning two things. Kiro's per-spec `requirements.md` has no equivalent; OpenSpec sidesteps the problem by not having per-feature IDs.

**5. The constitution is enforceable, not aspirational.**
`rules.md` holds numbered `RULE-*` invariants with a category, a rationale, an enforcement mechanism, a sentinel rule defining the override process, and an append-only Override Log. Spec Kit's constitution is prose principles. A rule violation without a matching log entry is a review FAIL, by rule.

**6. Templates are project-owned.**
Every document is generated from `.sdlc/templates/`, installed into the project and never overwritten once edited. Changing what the skills produce is editing a file in your repo, not forking the tool. Kiro's steering files shape *behaviour*; these shape the *output shape* directly.

**7. It is the union of three lineages, not a clone of one.**
Kiro's steering docs and EARS, Spec Kit's constitution and per-feature specs, OpenSpec's delta path — plus the validator none of them has.

---

## Where the field is ahead

**1. Task decomposition.** Kiro and Spec Kit both materialise a `tasks.md` with per-task state. `/sdlc-implement` is a single delegation with a retry cap of two and no durable progress artifact, so an interrupted implementation restarts from "list `src/` and `tests/`". The deliberate bet is that one coherent feature is one coding session; the cost is resumability on features that turn out to be bigger than that.

**2. Ambiguity hunting.** Spec Kit ships `/speckit.clarify` to surface underspecified areas before planning. `/sdlc-spec` interviews and then validates structure; the closest thing to ambiguity detection is the five-property completeness check in Phase 3, which is a fixed list.

**3. Cross-artifact consistency.** `/speckit.analyze` reads constitution, spec, plan and tasks together and reports contradictions between them. Here, the validator checks IDs and citations, and the review sub-agent checks one feature against its spec; nothing reads the whole artifact set at once looking for disagreement.

**4. Suspect links.** OpenFastTrace and the newer Git-native requirements tools version requirement IDs and flag a *covered* item whose source changed after coverage was claimed. Tags here are unversioned: reword a requirement and every tag pointing at it still validates clean. `/sdlc-adopt`'s drift report is the manual, per-feature version of that. This is the most valuable idea still on the table.

**5. Automation hooks.** Kiro runs actions on file save. Here, the validator is a CI gate (`/sdlc-init` offers the snippet) and everything else is a human typing a slash command in a fresh session.

**6. Eval maturity.** Three golden cases, deterministic checks only, and grading still needs a human to produce the output to grade. For a product that *is* instructions to a model, the eval suite is the only instrument that can catch a prompt regression, and it cannot yet run unattended.

**7. Packaging.** Competitors ship an installable CLI (`specify init`, `openspec archive`) or an IDE. This ships chat skills plus a bash installer; the workflow's context hygiene — one fresh session per phase — is a protocol the user has to remember rather than something the tool enforces.

---

## Deliberate non-goals

Worth stating, because each one looks like a missing feature until you see the trade:

- **No CLI wrapper.** The skills are the interface; the only shell entry points are the installer and the validator. Adding a CLI would mean maintaining a second surface that does what the chat already does.
- **No LLM-as-judge in the gate.** Everything the gate decides is parseable. Judgement lives in the review sub-agent, whose output is a report a human reads, not an exit code.
- **No runtime approval enforcement.** Approval tiers are instructions the model follows, not policy-gated tool calls. A runtime that policy-gates writes would enforce them for free; none of the 30+ targets does it the same way, so the skills stay runtime-neutral.
- **Specs are snapshots.** Re-sync is deliberate and manual (`/sdlc-quickfix` forward, `/sdlc-adopt` backward). Every tool in the table shares this; none of them has solved automatic spec-code convergence either.

---

## Positioning in one line

The nearest competitor by *intent* is Kiro (EARS + steering docs + spec per feature); by *mechanics* it is OpenSpec (repo-resident, agent-agnostic, delta path). The claim that belongs to this project and no other:

> **Spec-driven development with traceability you can fail a build on.**

That rests entirely on `sdlc-validate.py` and the tag conventions feeding it. Anything that weakens the validator weakens the only sentence worth saying about this project — which is why it is the part with a regression test per shipped bug.

---

## Sources

- [GitHub Spec Kit](https://github.com/github/spec-kit) · [Spec-Driven Development quickstart](https://github.github.com/spec-kit/quickstart.html)
- [Kiro — Specs](https://kiro.dev/docs/specs/) · [Kiro — spec best practices](https://kiro.dev/docs/specs/best-practices/)
- [OpenSpec — concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md) · [OpenSpec — archive command](https://deepwiki.com/Fission-AI/OpenSpec/6.6-archive-command)
- [BMAD-METHOD — working in the brownfield](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/working-in-the-brownfield.md)
- [OpenFastTrace](https://github.com/itsallcode/openfasttrace) · [StrictDoc](https://github.com/strictdoc-project/strictdoc) · [Doorstop](https://github.com/doorstop-dev/doorstop)
- [Spec Kit vs OpenSpec](https://intent-driven.dev/knowledge/spec-kit-vs-openspec/) · [Best SDD tools, 2026](https://www.augmentcode.com/tools/best-spec-driven-development-tools) · [BMAD vs Spec Kit vs OpenSpec](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/)
