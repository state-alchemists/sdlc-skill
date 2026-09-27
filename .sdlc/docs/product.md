# SDLC AI Plugin — Product Overview

## Problem Statement
AI-generated code can be sloppy. The people directing it often cannot articulate or define requirements, and while some can choose the right stack, many cannot. The result is code nobody can vouch for: no one reviewed the decisions, and nothing links a line of code back to the need it serves.

This plugin keeps the developer in the decision loop — architecture, requirements, specs, documentation and implementation are each proposed, reviewed and approved — and makes every requirement traceable to the code and tests that implement it, so a developer can take responsibility for AI-generated artifacts as if they were their own.

## Target Users
| User Role | Primary Goal |
|-----------|-------------|
| Developer directing an AI coding assistant | Ship AI-written code they can review, vouch for, and trace to a requirement |
| Developer who cannot fully specify requirements or choose a stack | Be interviewed into a precise spec, with choices explained, rather than having the AI guess |
| Developer adopting an existing (brownfield) codebase | Bring existing code under the same traceability without restructuring it |
| Maintainer of this framework | Change a template, convention or script in one place and have every skill follow |

## Success Criteria
- **Functional**: every active requirement is traced to at least one source file and one test file, and the validator fails the build when it is not; the same workflow runs on greenfield and brownfield projects.
- **Non-Functional**: the generated documents are readable by humans and AI alike, filled from project-owned templates; the validator and eval runner need only Python 3.8+ and its standard library.
- **Business**: a developer can answer "which requirement does this code serve, and who approved it?" from the repository alone; the framework stays cheap to maintain — each shipped file exists once.

## Scope
### In Scope
- Seven chat skills covering setup, planning, specification, implementation, review, quick fixes and brownfield adoption.
- A deterministic validator that enforces traceability, ID hygiene and EARS shape.
- An installer for the AI coding tools that load `SKILL.md` files, and a rule-based eval runner.

### Out of Scope
*Each item states the trade that makes it a non-goal, so it is not mistaken for a missing feature.*
- **A CLI wrapper** — the skills are the interface; a CLI would be a second surface doing what the chat already does.
- **LLM judgement in the gate** — everything the gate decides must be parseable and reproducible. Judgement lives in the review sub-agent, whose output is a report a human reads, not an exit code.
- **Runtime approval enforcement** — approval tiers are instructions the model follows. A runtime that policy-gates writes would enforce them for free; none of the 30+ targets does it the same way, so the skills stay runtime-neutral.
- **Automatic spec–code convergence** — specs are snapshots; re-sync is deliberate (`/sdlc-quickfix` forward, `/sdlc-adopt` backward). No tool below has solved convergence either.

## Alternatives & Positioning
*Surveyed 2026-09. Every row carries a source below.*

| Alternative | What it does | Where it is ahead of us | Why choose us instead |
|-------------|--------------|-------------------------|-----------------------|
| Status quo — prompting an assistant directly | Code straight from chat, no artifacts | Zero setup, fastest for throwaway work | Nothing records what was decided or approved, and nothing links code to a need |
| GitHub Spec Kit | Spec dir per feature + `plan.md`/`tasks.md`; `specify` CLI; prose constitution; `/speckit.analyze` LLM cross-artifact check; `implement → converge` loop | Task decomposition with per-task state; `/speckit.clarify` ambiguity hunting; whole-artifact-set consistency analysis; installable CLI | Traceability into source is enforced by a deterministic gate, not an LLM pass; the constitution is numbered, enforceable rules with an override log |
| Spec Kit V-Model extension | REQ/SYS/ARCH/MOD tiers, each paired with a test artifact; coverage matrix; `validate-requirement-coverage.sh` CI gate; targets IEC 62304 / ISO 26262 / DO-178C | Formal multi-tier requirements and a safety-standards focus; the same "AI drafts, scripts verify" split | The link lives in the code at `file:line`, not in a matrix to regenerate; one stdlib file instead of 14 commands plus YAML over a Spec Kit install |
| AWS Kiro | `requirements.md` + `design.md` + `tasks.md` per spec; EARS acceptance criteria; steering docs | IDE integration; actions on file save; task state | Agent-agnostic and repo-resident; Feature Keys stop per-feature IDs colliding; a gate that fails the build |
| OpenSpec | One living spec per capability; ADDED/MODIFIED/REMOVED delta specs merged by `openspec archive`; `openspec validate` (structural) | Mature delta workflow; installable CLI | Code↔spec traceability; per-feature IDs with keys; the delta path is promoted into the spec by default |
| BMAD-METHOD | PRD + architecture + sharded stories via agent personas; brownfield `document-project` | Persona-driven planning depth | Deterministic traceability and verdicts; lighter method (7 skills) |
| Agent OS | Standards + specs injected into agents | Standards injection across projects | Enforceable rules and a validator |
| OpenFastTrace / Doorstop / StrictDoc | One item per requirement with permanent IDs; `needs:`/`covers:` across levels; version-suspect links | **Suspect links** — flag coverage whose source changed after it was claimed; the most valuable idea we lack | Built for an LLM workflow: interviews, templates, delegation, review; tags are written by the agent as it codes |

**Where the field has caught up.** Deterministic enforcement is now a pattern, not a novelty — the V-Model extension enforces bidirectional requirement↔test coverage, and a `SpecAssay` extension and a `trace-manifest.json` gate have been proposed to Spec Kit proper. A Spec Kit fork's 720-line gate was superseded after its own PR recorded 59 findings nobody would action: a noisy gate is a gate teams switch off. Keep the validator's share of actual checks (22% of 1,755 lines) from shrinking.

**What only this combination does.** It unites three lineages — Kiro's steering docs and EARS, Spec Kit's constitution and per-feature specs, OpenSpec's delta path — and adds what none of the core tools has: both ends of the chain are checked (requirement → code and tests downstream; requirement → acceptance criterion upstream, so an AC renumbered in the brief surfaces as an error), and every document comes from a project-owned template, so changing the output shape is editing a file in your repo, not forking the tool (Kiro's steering files shape behaviour; these shape the output directly).

**Positioning in one line:** traceability that lives in the code, not in a matrix beside it — `IMPLEMENTS:`/`COVERS:` sit in the files that implement and test a requirement, so the validator reads the same artifact a reviewer does. The nearest competitor by intent is Kiro, by mechanics OpenSpec, and by the gate the V-Model extension. That claim rests entirely on `sdlc-validate.py`, which is why it carries a regression test per shipped bug.

**Sources:** [Spec Kit](https://github.com/github/spec-kit) · [SDD quickstart](https://github.github.com/spec-kit/quickstart.html) · [V-Model extension](https://github.com/leocamello/spec-kit-v-model) · [V-Model overview](https://deepwiki.com/leocamello/spec-kit-v-model) · [SpecAssay proposal, spec-kit#4649](https://github.com/github/spec-kit/issues/4649) · [Superseded traceability gate, internal-speckit-template#14](https://github.com/Sierra-Code-Co/internal-speckit-template/pull/14) · [Kiro specs](https://kiro.dev/docs/specs/) · [Kiro best practices](https://kiro.dev/docs/specs/best-practices/) · [OpenSpec concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md) · [OpenSpec archive](https://deepwiki.com/Fission-AI/OpenSpec/6.6-archive-command) · [BMAD brownfield](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/working-in-the-brownfield.md) · [OpenFastTrace](https://github.com/itsallcode/openfasttrace) · [StrictDoc](https://github.com/strictdoc-project/strictdoc) · [Doorstop](https://github.com/doorstop-dev/doorstop) · [Spec Kit vs OpenSpec](https://intent-driven.dev/knowledge/spec-kit-vs-openspec/) · [Best SDD tools, 2026](https://www.augmentcode.com/tools/best-spec-driven-development-tools) · [BMAD vs Spec Kit vs OpenSpec](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/)

## Key Stakeholders
| Stakeholder | Interest |
|-------------|----------|
| Developers | Using the skills to direct AI coding assistants, and maintaining the framework itself |
