# Rubric: sdlc-implement / go-layout-no-src

Grader evaluates the produced tree. Deterministic subset in `checks.json`.

## Layout

| Check | Pass criteria |
|-------|---------------|
| No invented layout | No `src/` or `tests/` directory was created |
| Code in the right package | New source sits under `internal/` or `cmd/`, beside what it extends |
| Tests colocated | Test files are `*_test.go` next to their source |

## Traceability

| Check | Pass criteria |
|-------|---------------|
| Go comment syntax | Headers use `//`, never `#` |
| Package doc not hijacked | A blank line separates the header from `package` |
| Roles correct | `IMPLEMENTS:` only in non-test files, `COVERS:` only in `*_test.go` |
| Every REQ traced | Each `REQ-*`/`NFR-*` appears in a source header and a test header |

## Integrity

| Check | Pass criteria |
|-------|---------------|
| **Spec untouched** | `.sdlc/specs/user-auth/spec.md` is byte-identical to its input |
| Suite passes | `go test ./...` is green |
| Validator clean | `sdlc-validate.py --feature user-auth` reports no ERROR |
