# Rubric: sdlc-init / personal-todo-app

A grader evaluates the four output files against the checks below. Score each as PASS / FAIL / PARTIAL; case-level score is the worst per-file score.

## docs/product.md

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

## docs/tech.md

| Check | Pass criteria |
|-------|---------------|
| Stack table populated | Rows for Language (Python), Framework (FastAPI), Database (SQLite), UI (HTMX) |
| Constraint: no paid services | Captured in Constraints section |
| Constraint: no JS framework | Captured in Constraints section |
| No hallucinated dependencies | No mention of Redis, Kafka, Postgres, Docker Swarm, etc. that weren't in input |

## docs/test-strategy.md

| Check | Pass criteria |
|-------|---------------|
| Unit + integration with pytest | Both levels present, tool = pytest |
| Manual smoke gate captured | Mentioned in Quality Goals or CI Gates |
| Environments table | Exactly two rows (Dev, Production); no Staging |
| No invented SLOs | No fabricated 99.9% targets that weren't in input |

## AGENTS.md

| Check | Pass criteria |
|-------|---------------|
| Essential commands present | Lists install/test/lint/run commands appropriate for FastAPI + pytest |
| Directory map present | Points to docs/product.md, docs/tech.md, docs/test-strategy.md |
| Concise | Total length under ~80 lines |

## Cross-file checks

| Check | Pass criteria |
|-------|---------------|
| Consistent product name | "Personal Todo" (or stable paraphrase) used across all four files |
| No staging environment leaks | "staging" appears in zero files |
| Approval prompt observed | Interaction log shows the skill presented each file for approval before writing |
