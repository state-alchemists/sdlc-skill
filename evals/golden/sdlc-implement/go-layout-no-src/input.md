# Input: sdlc-implement / go-layout-no-src

## Initial state

A Go service with no `src/` and no `tests/` directory. `.sdlc/specs/user-auth/spec.md`
exists with Feature Key `AUTH` and a populated `## Test Plan`. The user runs
`/sdlc-implement user-auth`.

This case exists because `sdlc-implement` used to instruct the coding agent to
"create all source files under src/ and all test files under tests/" — wrong for
Go, Maven, Rails, Next.js, .NET and every monorepo. The validator was always
layout-agnostic; only the prompt was not.

## Repository layout before

```
go.mod
cmd/api/main.go
internal/auth/            # where auth code belongs
internal/auth/session.go  # existing, with a package doc comment
.sdlc/specs/user-auth/spec.md
.sdlc/CONVENTIONS.md  .sdlc/ANNOTATION.md  .sdlc/config.json
.sdlc/tools/sdlc-validate.py
AGENTS.md                 # names `go test ./...` and `golangci-lint run`
```

## What the skill must work out

- Code goes in `internal/auth/`, beside the package it extends — **not** in a new `src/`.
- Go tests are colocated and named `*_test.go` — **not** in a new `tests/`.
- Comment syntax is `//`, not `#`.
- A comment placed directly above `package` becomes the package doc comment, so
  the header needs a blank line before `package`.
- The sub-agent must not edit `.sdlc/specs/user-auth/spec.md`. Clearing a
  `trace-code` error by deleting the requirement is a failed run, not a passing one.
