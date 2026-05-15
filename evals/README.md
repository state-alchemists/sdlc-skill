# Evals

Per-skill golden examples for measuring whether a skill change improves or regresses output quality. Without a measurement harness, prompt tweaks that improve one case while regressing three go unnoticed — this directory is the foothold for catching that.

## Status

**Skeleton.** The harness runner is not implemented yet — these are static golden examples for manual or scripted evaluation. The structure is committed so that:

1. New skill PRs can include a regression example.
2. A future runner (LLM-driven judge, or rule-based grader) has a deterministic input/expected layout to consume.

## Layout

```
evals/
  README.md                 # this file
  golden/                   # one subdirectory per skill
    sdlc-init/
      <case-name>/
        input.md            # user-side instructions / interview answers
        expected/           # files the skill should produce
          docs/product.md
          docs/tech.md
          ...
        rubric.md           # what counts as PASS / FAIL / PARTIAL
    sdlc-spec/
      <case-name>/
        ...
```

Each case is **self-contained**: an `input.md` describing what was said to the skill, an `expected/` tree mirroring the project layout the skill should produce, and a `rubric.md` that names the specific properties a grader should check.

## Authoring a case

1. Pick a skill and a representative scenario (e.g. for `sdlc-spec`: "add an email verification step to an existing auth feature").
2. Write `input.md` as a transcript of inputs the skill would receive — file contents it reads, plus any user replies during interview.
3. Run the skill in a real chat session. Save the output files into `expected/`.
4. Read each file and replace anything that depends on the run (timestamps, generated IDs) with placeholders like `{{TIMESTAMP}}`. Note these in `rubric.md`.
5. Write `rubric.md` as a checklist a grader can evaluate against any new output:
   - Required IDs present (e.g. "every REQ-* in input is in output")
   - Required sections present
   - Forbidden content absent (e.g. "no hallucinated entity names")
   - Numeric thresholds (e.g. "≥ 1 EARS keyword per requirement")

## Running

When the runner lands, expected invocation will be:

```bash
evals/run.sh                          # all skills, all cases
evals/run.sh --skill sdlc-spec        # one skill
evals/run.sh --case sdlc-spec/email-verify  # one case
```

Output: a markdown report with PASS/FAIL/PARTIAL per case, scored against the rubric.

## Why this matters

Without evals:
- A prompt tweak that improves one case but regresses three goes unnoticed.
- New contributors can't tell whether their skill changes help or hurt.
- The plugin has no story for "is this skill actually any good?"

Two cases per skill is the minimum useful set: one happy path and one edge case.
