# Rubric: sdlc-init / personal-todo-app

A grader evaluates the output files against the checks below. Score each as PASS / FAIL / PARTIAL; case-level score is the worst per-file score. **All artifacts live under `.sdlc/` except `AGENTS.md`, which is at the repo root.** Deterministic subsets of these checks are encoded in `checks.json` (run via `evals/run.py --actual DIR`).

## .sdlc/docs/product.md

| Check | Pass criteria |
|-------|---------------|
| Problem statement present | Section exists; mentions "scattered notes" or equivalent paraphrase |
| Target users captured | Table includes "Individual" or synonym with goal "capture tasks fast" |
| Success criteria split | Three categories shown: Functional, Non-Functional, Business |
| Functional threshold | Contains "5s" sync target |
| Non-functional threshold | Contains "1.5s" P95 or equivalent |
| Business target | Contains "100" and "3 months" |
| Scope section | Lists at least 3 in-scope items and 2 out-of-scope items |
| Out-of-scope correctness | "collaboration", "mobile native", and "Slack/integrations" appear in out-of-scope |
| Stakeholders captured | Solo dev and end users both present |
| No hallucinated stakeholders | No invented executives, investors, or teams |

## .sdlc/docs/tech.md

| Check | Pass criteria |
|-------|---------------|
| Stack table populated | Rows for Language (Python), Framework (FastAPI), Database (SQLite), UI (HTMX) |
| Constraint: no paid services | Captured in Constraints section |
| Constraint: no JS framework | Captured in Constraints section |
| No hallucinated dependencies | No mention of Redis, Kafka, Postgres, Docker Swarm, etc. that weren't in input |

## .sdlc/docs/test-strategy.md

| Check | Pass criteria |
|-------|---------------|
| Unit + integration with pytest | Both levels present, tool = pytest |
| Test naming convention stated | A `Test Naming Convention` line names a concrete pytest convention |
| Manual smoke gate captured | Mentioned in Quality Goals or CI Gates |
| Traceability gate present | CI Gates table references `sdlc-validate.py` |
| Environments table | Exactly two rows (Dev, Production); no Staging |
| No invented SLOs | No fabricated 99.9% targets that weren't in input |

## AGENTS.md (repo root)

| Check | Pass criteria |
|-------|---------------|
| Essential commands present | Lists install/test/lint/run commands appropriate for FastAPI + pytest |
| Validate command present | Includes `python3 .sdlc/tools/sdlc-validate.py` |
| Directory map present | Points to `.sdlc/docs/product.md`, `.sdlc/docs/tech.md`, `.sdlc/docs/test-strategy.md`, `.sdlc/CONVENTIONS.md` |
| Concise | Total length under ~90 lines |

## .sdlc/rules.md

| Check | Pass criteria |
|-------|---------------|
| File exists | `.sdlc/rules.md` present |
| RULE-999 sentinel present | Override Process section with `RULE-999` |
| Override Log present | An Override Log table exists |
| Rules phrased ALWAYS/NEVER | At least one user rule uses ALWAYS or NEVER phrasing |
| Constraints captured as rules | "no paid services" and "HTMX only / no JS framework" appear as rules or are clearly cross-referenced from tech.md constraints |
| Immutable-ID discipline | Rules are numbered `RULE-NNN`; none recycled |

## .sdlc/CONVENTIONS.md

| Check | Pass criteria |
|-------|---------------|
| File exists | `.sdlc/CONVENTIONS.md` present |
| Canonical EARS table | Lists WHEN / WHILE / WHERE / IF…THEN / ubiquitous; no AS/ALWAYS as canonical |
| ID scheme documented | Describes `Feature Key` and `KEY:REQ-NNN` tag format |

## .sdlc/tools/sdlc-validate.py

| Check | Pass criteria |
|-------|---------------|
| Validator installed | `.sdlc/tools/sdlc-validate.py` present and runnable |

## Cross-file checks

| Check | Pass criteria |
|-------|---------------|
| Consistent product name | "Personal Todo" (or stable paraphrase) used across files |
| No staging environment leaks | "staging" appears in zero files |
| Nothing written outside `.sdlc/` except AGENTS.md | No `docs/`, `requirements/`, or root `rules.md` created |
| Approval prompt observed | Interaction log shows batched (Tier-2) approval before writing |
