#!/usr/bin/env bash
# test.sh — every check CI runs. CI and `zrb skill test` both call this file.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python3}"

step() { printf '\n== %s\n' "$*"; }

step "Compile bundled scripts"
"${PYTHON}" -m compileall -q skills evals tests zrb_init.py

step "Validator regression tests"
"${PYTHON}" tests/test_sdlc_validate.py

step "Eval runner tests"
"${PYTHON}" tests/test_eval_runner.py

step "Prompt invariants"
"${PYTHON}" tests/test_skill_prompts.py

step "Lint eval cases"
"${PYTHON}" evals/run.py

step "Installer tests"
tests/test_install.sh

# This repo follows its own method: every requirement in .sdlc/specs/ must
# trace to code and tests.
step "Traceability gate over this repository"
"${PYTHON}" skills/sdlc-init/assets/tools/sdlc-validate.py --strict

step "All checks passed"
