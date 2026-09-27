#!/usr/bin/env bash
# SPEC: .sdlc/specs/installer/spec.md
# COVERS: INST:REQ-001, INST:REQ-002, INST:REQ-003, INST:REQ-004, INST:REQ-005, INST:REQ-006, INST:REQ-007, INST:REQ-008, INST:IT-001, INST:IT-002, INST:IT-003, INST:IT-004, INST:IT-005, INST:IT-006
# Installer tests. Each block runs against a throwaway $HOME.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

cases=0
fail() { echo "FAIL: $*"; exit 1; }
pass() { cases=$((cases + 1)); echo "PASS  $*"; }

# Pins the skills directories checked against each tool's own docs, and
# Cursor's absence (it loads skills per project). Matched against the Target
# lines alone: a superseded path is named too, as somewhere to sweep.
targets="$(bin/install.sh --dry-run --tools all | sed -n 's/^\[install.sh\] Target: //p')"
for path in .claude/skills .zrb/skills .agents/skills .codex/skills \
            .gemini/skills .copilot/skills .config/opencode/skills; do
    echo "${targets}" | grep -q "${path}" || fail "missing target: ${path}"
done
! echo "${targets}" | grep -qE '\.github/skills|\.cursor/skills' || fail "stale target listed"
pass "targets the documented skills directories"

(
    export HOME="$(mktemp -d)"
    mkdir -p "$HOME/.claude"
    bin/install.sh > /dev/null
    test -d "$HOME/.claude/skills/sdlc-plan" || fail "auto-detect skipped an existing tool home"
    test ! -d "$HOME/.codex" || fail "auto-detect installed to a tool that is not present"
    rm -rf "$HOME/.claude"
    ! bin/install.sh > /dev/null 2>&1 || fail "no tool homes should exit non-zero"
)
pass "auto-detects only tool homes that exist"

(
    export HOME="$(mktemp -d)"
    bin/install.sh --dry-run --tools claude > /dev/null
    test ! -e "$HOME/.claude" || fail "--dry-run changed the file system"
)
pass "dry-run changes nothing"

(
    export HOME="$(mktemp -d)"
    status=0
    bin/install.sh --tools claude,nosuch > /dev/null 2>&1 || status=$?
    test "${status}" -eq 2 || fail "unknown tool id exited ${status}, not 2"
    test ! -e "$HOME/.claude" || fail "unknown tool id still installed something"
)
pass "unknown tool id exits 2 and installs nothing"

# An upgrade must not leave a second copy of every skill at the path the
# previous version installed to.
(
    export HOME="$(mktemp -d)"
    mkdir -p "$HOME/.opencode/skills/"{sdlc-plan,sdlc-requirements,my-own-skill,sdlc-deploy}
    bin/install.sh --tools opencode > /dev/null
    test -d "$HOME/.config/opencode/skills/sdlc-plan"
    test ! -d "$HOME/.opencode/skills/sdlc-plan" || fail "stale copy left at superseded path"
    test ! -d "$HOME/.opencode/skills/sdlc-requirements" || fail "merged-away skill left at superseded path"
    test -d "$HOME/.opencode/skills/my-own-skill" || fail "sweep removed a skill that is not ours"
    test -d "$HOME/.opencode/skills/sdlc-deploy" || fail "sweep removed a user's own sdlc-* skill"
    mkdir -p "$HOME/.opencode/skills/sdlc-plan"
    bin/install.sh --tools opencode --keep-legacy > /dev/null
    test -d "$HOME/.opencode/skills/sdlc-plan" || fail "--keep-legacy still swept the superseded path"
)
pass "sweeps superseded directories, honours --keep-legacy"

(
    export HOME="$(mktemp -d)"
    mkdir -p "$HOME/.claude/skills/"{sdlc-requirements,unrelated-skill,sdlc-deploy}
    bin/install.sh --tools claude > /dev/null
    test ! -d "$HOME/.claude/skills/sdlc-requirements" || fail "merged-away skill left behind"
    test -d "$HOME/.claude/skills/sdlc-plan"
    test -f "$HOME/.claude/skills/sdlc-init/assets/tools/sdlc-validate.py"
    test -d "$HOME/.claude/skills/unrelated-skill" || fail "a non-sdlc skill was removed"
    test -d "$HOME/.claude/skills/sdlc-deploy" || fail "a user's own sdlc-* skill was removed"
    bin/install.sh --uninstall --tools claude > /dev/null
    test ! -d "$HOME/.claude/skills/sdlc-plan" || fail "uninstall left a shipped skill"
    test -d "$HOME/.claude/skills/unrelated-skill"
    test -d "$HOME/.claude/skills/sdlc-deploy" || fail "uninstall removed a skill that is not ours"
)
pass "upgrades over a previous version, then uninstalls only ours"

echo
echo "${cases} case(s), 0 failed"
