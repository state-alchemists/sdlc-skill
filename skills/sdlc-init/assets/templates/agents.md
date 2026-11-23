# {{PROJECT_NAME}}

## Overview
{{1-2 sentence summary}}

## Essential Commands
```bash
# Install
{{cmd}}
# Test
{{cmd}}
# Lint
{{cmd}}
# Run
{{cmd}}
# Validate SDLC traceability
python3 .sdlc/tools/sdlc-validate.py
```

## Architecture
{{Description}}

| Directory | Purpose |
|-----------|---------|
| {{source root(s)}} | Source code |
| {{test root(s)}} | Tests |
| `.sdlc/config.json` | Source/test layout, comment styles, scan overrides |
| `.sdlc/ANNOTATION.md` | Comment syntax and header placement per language |
| `{{docs root}}/product.md` | Product vision |
| `{{docs root}}/tech.md` | Tech decisions |
| `{{docs root}}/test-strategy.md` | Testing approach |
| `.sdlc/CONVENTIONS.md` | Paths, EARS dialect, ID/traceability scheme |
| `.sdlc/templates/` | Templates the sdlc-* skills generate from |
| `.sdlc/rules.md` | Project invariants |
