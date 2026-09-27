# Evals

Per-skill golden examples plus a deterministic runner for measuring whether a skill change improves or regresses output quality. Without a measurement harness, a prompt tweak that improves one case while regressing three goes unnoticed — this directory catches that.

Anthropic's skill-authoring guidance recommends **≥3 evaluation scenarios per skill**, authored before extensive documentation, and a **no-skill baseline** to measure against. There is no built-in runner, so the plugin ships its own (`run.py`).

## Status

**Runner: implemented (rule-based).** `run.py` grades the deterministic `checks.json` assertions in each case — enough to run in CI with no LLM. Fuzzy, semantic rubric items (tone, completeness, "no hallucinated stakeholders") remain human-graded against `rubric.md`. LLM-as-judge grading is not implemented.

## Layout

```
evals/
  README.md                 # this file
  run.py                    # rule-based runner
  golden/                   # one subdirectory per skill
    sdlc-init/
      personal-todo-app/
        input.md            # user-side instructions / interview answers
        rubric.md           # human-readable PASS / FAIL / PARTIAL criteria
        checks.json         # machine-checkable assertions (optional)
        expected/           # reference output tree (optional)
    sdlc-spec/email-verification/             # canonical EARS, folded test plan, PBT, outside-code NFR
    sdlc-implement/go-layout-no-src/          # colocated Go tests, no src/ + tests/ assumption
    sdlc-quickfix/login-error-message/        # small delta, promote-by-default
    sdlc-adopt/legacy-layout-migration/       # relocation + setup completion
```

All graded paths use the canonical layout: artifacts under `.sdlc/` (steering docs `.sdlc/docs/`, requirements `.sdlc/requirements/`, specs `.sdlc/specs/<slug>/spec.md` (test plan included as its `## Test Plan` section), rules `.sdlc/rules.md`, templates `.sdlc/templates/`, validator `.sdlc/tools/sdlc-validate.py`), with `AGENTS.md` at the repo root.

## checks.json schema

```json
{
  "case": "sdlc-spec/email-verification",
  "checks": [
    {"id": "SPEC-1", "description": "spec exists", "type": "file_exists",
     "target_file": ".sdlc/specs/email-verification/spec.md", "severity": "error"},
    {"id": "SPEC-4", "description": "no deprecated EARS", "type": "absent_regex",
     "target_file": ".sdlc/specs/email-verification/spec.md", "pattern": "ALWAYS\\s+SHALL", "severity": "error"},
    {"id": "SPEC-7", "description": "at least 3 requirements", "type": "min_matches",
     "target_file": ".sdlc/specs/email-verification/spec.md", "pattern": "REQ-\\d+", "min_count": 3, "severity": "error"}
  ]
}
```

| Field | Meaning |
|-------|---------|
| `type` | see below |
| `target_file` | path relative to the `--actual` output directory |
| `pattern` | regex (for the four regex types) |
| `min_count` / `max_count` | integer threshold (for `min_matches` / `max_matches`) |
| `severity` | `error` (default; FAIL → case FAILs) or `warning` (FAIL → case PARTIAL) |

| Type | Passes when |
|------|-------------|
| `file_exists` / `file_absent` | `target_file` exists / does not exist |
| `contains_regex` | `target_file` exists and `pattern` is found |
| `absent_regex` | `target_file` exists and `pattern` is not found (a missing file fails — use `file_absent` for absence) |
| `min_matches` / `max_matches` | `target_file` has at least `min_count` / at most `max_count` matches |

Unknown keys, bad severities and invalid regexes are lint errors.

## Running

```bash
python3 evals/run.py --list                                # list all cases
python3 evals/run.py                                        # lint: validate case structure + checks.json
python3 evals/run.py --actual /path/to/output              # grade ALL cases against produced output
python3 evals/run.py --skill sdlc-spec --actual DIR        # one skill
python3 evals/run.py --case sdlc-spec/email-verification --actual DIR  # one case
```

`--actual DIR` is the project directory a skill run produced (its `.sdlc/` tree). The runner resolves each `target_file` under it. Exit 0 = all graded cases PASS (or lint clean); exit 1 = a FAIL or structural problem.

**Baseline comparison**: run the same case twice — once with the skill installed, once without — into two output dirs, then `run.py --actual` each. A skill that doesn't beat the no-skill baseline isn't earning its context budget.

## Authoring a case

1. Pick a skill and a representative scenario (one happy path + one edge case minimum; aim for ≥3 per skill).
2. Write `input.md` as the inputs the skill receives — files it reads plus interview replies.
3. Run the skill in a real session; save output into `expected/` (or describe it in `rubric.md` with `{{PLACEHOLDER}}`s for nondeterministic bits like timestamps and generated IDs).
4. Write `rubric.md` as the full checklist: required IDs/sections present, forbidden content absent (e.g. deprecated EARS dialect, hallucinated entities), numeric thresholds.
5. Encode the deterministic subset in `checks.json` so `run.py` grades it in CI. Good deterministic checks: `file_exists` for each artifact at its `.sdlc/` path, `absent_regex` for the deprecated EARS dialect (`ALWAYS\s+SHALL|\bUNLESS\b|\bAS\b.+\bTHEN\b`), `contains_regex` for `Feature Key`, `min_matches` for REQ IDs.

