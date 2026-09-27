# SDLC AI Plugin

## Overview
Seven chat skills that guide an AI coding assistant through spec-driven development, plus a stdlib-only validator that fails the build when requirements stop tracing to code and tests. This repository follows its own method: see `.sdlc/`.

## Essential Commands
```bash
# Install (into detected AI coding tools)
bin/install.sh
# Test — every check CI runs, including the traceability gate over this repo
bin/test.sh
# Lint
black --check skills evals tests    # maintainer tool; not enforced in CI
# Run
N/A — the skills run inside an AI coding tool; there is no service
# Validate SDLC traceability
python3 .sdlc/tools/sdlc-validate.py
```

## Architecture
Markdown skills (`skills/sdlc-*/SKILL.md`) are loaded by the host AI tool. Everything they install into a project exists once, under `skills/sdlc-init/assets/`; this repository's `.sdlc/` links to those files rather than copying them (RULE-004). See `.sdlc/docs/architecture.md`.

| Directory | Purpose |
|-----------|---------|
| `skills/`, `bin/`, `evals/run.py` | Source code |
| `tests/`, `evals/golden/` | Tests and golden eval cases |
| `.sdlc/config.json` | Source/test layout, comment styles, scan overrides |
| `.sdlc/ANNOTATION.md` | Comment syntax and header placement per language |
| `.sdlc/docs/product.md` | Product vision, alternatives and positioning |
| `.sdlc/docs/tech.md` | Tech decisions |
| `.sdlc/docs/test-strategy.md` | Testing approach |
| `.sdlc/CONVENTIONS.md` | Paths, EARS dialect, ID/traceability scheme |
| `.sdlc/templates/` | Templates the sdlc-* skills generate from |
| `.sdlc/rules.md` | Project invariants |
