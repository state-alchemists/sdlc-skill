# Problem Brief: SDLC AI Plugin

## Problem Statement
AI-generated code can be sloppy, and the developer directing it often cannot articulate the requirements or choose the stack. Without a record of what was decided, who approved it, and which code serves which need, nobody can take responsibility for the result. See `.sdlc/docs/product.md`.

## User Stories
- `US-001`: As a **developer directing an AI assistant**, I want **every requirement traced to the code and tests that implement it** so that **I can take accountability for AI-generated artifacts as if they were my own**.
- `US-002`: As a **developer**, I want **to review and approve architecture, requirements, specs and implementation before they are written** so that **the AI never decides for me silently**.
- `US-003`: As a **developer on a new or existing codebase**, I want **one workflow that fits greenfield and brownfield projects of any layout** so that **I can adopt it without restructuring my project**.
- `US-004`: As a **developer or an AI agent**, I want **generated documents that are consistently shaped and precise** so that **both humans and agents can read and act on them**.
- `US-005`: As a **maintainer of this framework**, I want **every template, convention and script to exist once and be verified automatically** so that **the framework stays easy to change**.
- `US-006`: As a **developer**, I want **to install the skills into the AI coding tools I already use** so that **I do not have to switch tools**.

## Acceptance Criteria
*Each AC has a stable ID. `sdlc-spec` cites the AC each `REQ-*` derives from, so renumbering breaks traceability.*

- [x] `AC-001` (US-001): WHEN a requirement has no implementing source file or no covering test file, the validator exits with an error.
- [x] `AC-002` (US-001): A tag pointing at an undefined requirement, a recycled ID, or a duplicate Feature Key fails validation.
- [x] `AC-003` (US-001): A requirement citing an acceptance criterion the brief does not define fails validation, and an AC no requirement cites is reported.
- [x] `AC-004` (US-001): A tag counts only inside a real comment, in the right kind of file — source for `IMPLEMENTS:`, test for `COVERS:`.
- [x] `AC-005` (US-002): A skill writes only after an explicit affirmative, and a coding sub-agent cannot change the spec it is measured against.
- [x] `AC-006` (US-002): A review run in the session that wrote the code cannot return APPROVE.
- [x] `AC-007` (US-003): Tests are recognised in Python, Go, Maven, Jest, RSpec, .NET, Cypress and Terraform layouts with no configuration, and any other layout can be declared in `.sdlc/config.json`.
- [x] `AC-008` (US-003): A legacy layout is detected by file content, never by directory name, and its setup finishes at `/sdlc-adopt`.
- [x] `AC-009` (US-004): A requirement that is not canonical uppercase EARS, or uses an unverifiable word, is reported.
- [x] `AC-010` (US-004): Every generated document is filled from a project-owned template that a re-run never overwrites, and every template diagram parses as Mermaid.
- [x] `AC-011` (US-005): Every shipped rule is stated in one file, and every skill reads the conventions from it.
- [x] `AC-012` (US-005): Golden eval cases are linted structurally, and graded deterministically against a skill's output.
- [x] `AC-013` (US-006): The installer installs into each supported tool's documented skills directory, removes skills it used to ship, and never removes a skill it does not own.

## Non-Functional Requirements
*The upstream source of `NFR-*` IDs, derived from product.md Success Criteria. `sdlc-spec` cites these IDs; it does not invent NFRs from nowhere.*

- `NFR-001`: The validator and the eval runner run on Python 3.8 or later using only the standard library.
- `NFR-002`: The installer runs on bash 3.2 or later.

## Dependencies
| Dependency | Type | Status |
|------------|------|--------|
| An AI coding tool that loads `SKILL.md` files | Runtime | Available (zrb, Claude Code, Codex, Gemini, Copilot, OpenCode, …) |
| Python 3.8+ in the target project's CI | Runtime | Assumed |

## Open Questions
1. Should approvals be recorded on disk (Status / Approved-by in spec, brief and ADR templates) so AC-005 is auditable after the fact, not only enforced in chat?
2. Should the validator flag a requirement whose text changed after its tags were written (suspect links)?
