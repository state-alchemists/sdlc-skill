# Feature Spec: Installer

**Feature Key:** INST

`bin/install.sh` — copies the skills into each AI coding tool's skills directory.

## Requirements

- `REQ-001` (AC-013): WHEN a tool is selected, the installer SHALL copy every shipped `sdlc-*` skill into that tool's documented skills directory.
- `REQ-002` (AC-013): WHEN no target is given, the installer SHALL install only for tools whose home directory already exists, and exit non-zero when none exists.
- `REQ-003` (AC-013): WHEN installing into a target, the installer SHALL remove the skills this repository used to ship from it.
- `REQ-004` (AC-013): The installer SHALL never remove a skill directory that this repository does not ship and never shipped.
- `REQ-005` (AC-013): WHEN run without `--keep-legacy`, the installer SHALL remove this repository's skills from superseded skills directories.
- `REQ-006` (AC-013): WHEN run with `--uninstall`, the installer SHALL remove this repository's skills from the selected targets.
- `REQ-007` (AC-013): WHILE `--dry-run` is set, the installer SHALL print each action without changing the file system.
- `REQ-008` (AC-013): IF an unknown tool ID is given, THEN the installer SHALL exit with 2 without installing anything.

## Non-Functional Requirements

| ID | Requirement | Target | Validated By |
|----|-------------|--------|--------------|
| NFR-002 | Runs on bash 3.2+ | macOS default shell | code review against RULE-002 |

## NFRs Validated Outside Code
- `NFR-002`: runs on bash 3.2+ — validated by review against RULE-002; CI runs a newer bash, so no executable check reaches it yet.

## API Surface

| Method | Path | Request | Response | Auth |
|--------|------|---------|----------|------|
| CLI | `bin/install.sh` | `[--tools ID,...\|all] [--zrb] [--claude] [--all] [--dir PATH]... [--uninstall] [--keep-legacy] [--dry-run]` | `[install.sh] Target: <dir>` then one line per skill installed, removed or kept | none |

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| Unknown option or tool ID, missing flag value | exit 2 | `[install.sh] Unknown …` and usage |
| No tool home detected, no target given | exit 1 | hint to pass `--tools` |

## Correctness

- **Idempotency:** re-running replaces each shipped skill in place; a second run leaves the same tree as the first.

## Entities

None — the installer handles directories, not domain entities.

## Test Plan

*Test naming convention: one `pass "<behaviour>"` block per case in `tests/test_install.sh`, each against a throwaway `$HOME`.*

### Unit Tests
N/A — the installer is tested as a whole, below.

### Integration Tests
| ID | Req | Test Name | Setup | Assertion |
|----|-----|-----------|-------|-----------|
| IT-001 | REQ-001 | targets the documented skills directories | `--dry-run --tools all` | every documented path is a target; Copilot/Cursor legacy paths are not |
| IT-002 | REQ-002 | auto-detects only tool homes that exist | `$HOME/.claude` only; then none | installs to Claude only; exits non-zero with none |
| IT-003 | REQ-003, REQ-004, REQ-006 | upgrades over a previous version, then uninstalls only ours | retired, unrelated and user `sdlc-*` skills present | retired removed; others kept; uninstall removes only ours |
| IT-004 | REQ-004, REQ-005 | sweeps superseded directories, honours --keep-legacy | old `~/.opencode/skills` copy | swept; kept with `--keep-legacy`; user skills untouched |
| IT-005 | REQ-007 | dry-run changes nothing | `--dry-run --tools claude` | `$HOME/.claude` not created |
| IT-006 | REQ-008 | unknown tool id exits 2 and installs nothing | `--tools claude,nosuch` | exit 2, nothing created |

### End-to-End Tests
N/A — a real install is the integration test above.

### Property-Based Tests
N/A — no property-testing framework configured.

### Design Property Coverage
| Property | Covered By | Notes |
|----------|------------|-------|
| Idempotency | IT-004 | the `--keep-legacy` block installs twice |

### Test Data Strategy
- **Fixtures**: skill directories created with `mkdir -p` under a temporary `$HOME`.
- **Synthetic data**: fake retired (`sdlc-requirements`), unrelated (`my-own-skill`) and user (`sdlc-deploy`) skills.
- **Cleanup**: each case runs in a subshell with its own `mktemp -d` home.
