#!/usr/bin/env bash
# install.sh — Install sdlc-skill skills into AI coding tool skill directories.
#
# Default behaviour (no flags): installs into whichever tool directories
# already exist on this machine. If none exist, prints a hint and exits.
#
# Examples:
#   bin/install.sh                              # auto-detect installed tools
#   bin/install.sh --zrb                        # zrb only (convenience)
#   bin/install.sh --claude                     # Claude Code only (convenience)
#   bin/install.sh --tools codex,opencode       # specific tools (creates dirs)
#   bin/install.sh --tools all                  # all known tools
#   bin/install.sh --all                        # alias for --tools all
#   bin/install.sh --dir .claude/skills         # a project-scoped directory
#   bin/install.sh --uninstall --tools all      # remove sdlc-* from all tools
#   bin/install.sh --dry-run --tools cursor     # preview without changing anything

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_SRC="${REPO_ROOT}/skills"

# ---------------------------------------------------------------------------
# Tool registry — maps tool IDs to their skills directory under $HOME.
# Uses a case function rather than associative arrays (bash 3.2 compat).
# Source: OpenSpec docs/supported-tools.md (skill directory patterns).
# ---------------------------------------------------------------------------
tool_dir() {
    case "$1" in
        zrb)            echo "${HOME}/.zrb/skills" ;;
        claude)         echo "${HOME}/.claude/skills" ;;
        codex)          echo "${HOME}/.codex/skills" ;;
        opencode)       echo "${HOME}/.opencode/skills" ;;
        cursor)         echo "${HOME}/.cursor/skills" ;;
        windsurf)       echo "${HOME}/.windsurf/skills" ;;
        github-copilot) echo "${HOME}/.github/skills" ;;
        gemini)         echo "${HOME}/.gemini/skills" ;;
        amazon-q)       echo "${HOME}/.amazonq/skills" ;;
        cline)          echo "${HOME}/.cline/skills" ;;
        codebuddy)      echo "${HOME}/.codebuddy/skills" ;;
        continue)       echo "${HOME}/.continue/skills" ;;
        crush)          echo "${HOME}/.crush/skills" ;;
        factory)        echo "${HOME}/.factory/skills" ;;
        iflow)          echo "${HOME}/.iflow/skills" ;;
        junie)          echo "${HOME}/.junie/skills" ;;
        kilocode)       echo "${HOME}/.kilocode/skills" ;;
        kiro)           echo "${HOME}/.kiro/skills" ;;
        lingma)         echo "${HOME}/.lingma/skills" ;;
        pi)             echo "${HOME}/.pi/skills" ;;
        qoder)          echo "${HOME}/.qoder/skills" ;;
        qwen)           echo "${HOME}/.qwen/skills" ;;
        roocode)        echo "${HOME}/.roo/skills" ;;
        antigravity)    echo "${HOME}/.agent/skills" ;;
        bob)            echo "${HOME}/.bob/skills" ;;
        costrict)       echo "${HOME}/.cospec/skills" ;;
        forgecode)      echo "${HOME}/.forge/skills" ;;
        kimi)           echo "${HOME}/.kimi/skills" ;;
        trae)           echo "${HOME}/.trae/skills" ;;
        vibe)           echo "${HOME}/.vibe/skills" ;;
        auggie)         echo "${HOME}/.augment/skills" ;;
        *)              return 1 ;;
    esac
}

known_tool() { tool_dir "$1" > /dev/null 2>&1; }

# Tools confirmed to load a directory of SKILL.md files from <dotdir>/skills/.
# These are what "--tools all" and auto-detection target.
VERIFIED_TOOL_IDS=(zrb claude)

# Everything else this script knows a path for. The list came from OpenSpec's
# supported-tools table, which enumerates tools whose *rules/instruction* files
# OpenSpec writes -- not tools that implement the SKILL.md format. Those are
# different things: Cursor reads .cursor/rules/*.mdc, Windsurf .windsurf/rules/,
# Gemini CLI GEMINI.md. Writing a SKILL.md into <dotdir>/skills/ for those is
# inert. They stay reachable by explicit --tools <id>, with a warning, but they
# are no longer swept up by "all", which used to create ~/.bob, ~/.qoder and
# friends for software the user had never installed.
UNVERIFIED_TOOL_IDS=(
    codex opencode cursor windsurf github-copilot
    gemini amazon-q cline codebuddy continue crush factory iflow
    junie kilocode kiro lingma pi qoder qwen roocode
    antigravity bob costrict forgecode kimi trae vibe auggie
)

# Ordered list for usage display and auto-detection.
TOOL_IDS=("${VERIFIED_TOOL_IDS[@]}" "${UNVERIFIED_TOOL_IDS[@]}")

# Warn once per explicitly named unverified tool.
warn_if_unverified() {
    local id="$1" x
    for x in "${VERIFIED_TOOL_IDS[@]}"; do
        [[ "$x" == "$id" ]] && return 0
    done
    log "Warning: '${id}' is not known to load SKILL.md files from its skills/"
    log "         directory. Installing anyway because you asked for it."
}

# Skills this repo used to ship. They are removed on upgrade because they still
# answer their old slash command against paths that no longer exist. Every other
# sdlc-* directory is left alone: the namespace is shared with whatever the user
# wrote themselves, and deleting someone's own sdlc-deploy is not an upgrade.
RETIRED_SKILLS=(sdlc-requirements sdlc-architect sdlc-document sdlc-migrate)

uninstall=0
dry_run=0
want_tool=()
want_dir=()

# Check whether a tool ID is in the want_tool set.
want() {
    local id="$1" x
    # `${a[@]}` on an empty array is an unbound-variable error under bash 3.2.
    [[ "${#want_tool[@]}" -gt 0 ]] || return 1
    for x in "${want_tool[@]}"; do
        [[ "$x" == "$id" ]] && return 0
    done
    return 1
}

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Options:
  --zrb               Target ~/.zrb/skills/
  --claude            Target ~/.claude/skills/
  --tools <id,...>    Target specific tools by ID (comma-separated).
                      Use "all" for every VERIFIED tool (zrb, claude).
  --all               Alias for --tools all
  --dir <path>        Target an arbitrary skills directory, e.g. a
                      project-scoped .claude/skills/ (repeatable)
  --uninstall         Remove this repo's sdlc-* skills from selected targets
  --dry-run           Print what would happen without changing anything
  -h, --help          This message

With no target flags, install.sh installs to whichever tool directories
already exist on this machine. If none exist, it exits with a hint.

"all" means every tool confirmed to load a directory of SKILL.md files:
zrb and Claude Code. Other IDs are still accepted explicitly, with a
warning -- most of them read a rules or instructions file rather than a
skills directory, so a SKILL.md dropped there does nothing. For anything
else, --dir <path> is the honest answer.

Only the skills this repo ships, plus ones it used to ship, are ever
removed. An sdlc-* skill of your own in the same directory is left alone.
EOF
}

log() { printf '[install.sh] %s\n' "$*"; }

run() {
    if [[ "${dry_run}" -eq 1 ]]; then
        printf '[dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --zrb)       want_tool+=("zrb") ;;
        --claude)    want_tool+=("claude") ;;
        --all)       want_tool=("${VERIFIED_TOOL_IDS[@]}") ;;
        --tools)
            shift
            if [[ $# -eq 0 ]]; then
                log "Missing value for --tools"; usage; exit 2
            fi
            if [[ "$1" == "all" ]]; then
                want_tool=("${VERIFIED_TOOL_IDS[@]}")
            else
                IFS=',' read -ra ids <<< "$1"
                for id in "${ids[@]}"; do
                    # trim whitespace
                    id="${id#"${id%%[![:space:]]*}"}"
                    id="${id%"${id##*[![:space:]]}"}"
                    if ! known_tool "${id}"; then
                        log "Unknown tool ID: ${id}"; exit 2
                    fi
                    want_tool+=("${id}")
                done
            fi
            ;;
        --dir)
            shift
            if [[ $# -eq 0 ]]; then
                log "Missing value for --dir"; usage; exit 2
            fi
            want_dir+=("$1")
            ;;
        --uninstall) uninstall=1 ;;
        --dry-run)   dry_run=1 ;;
        -h|--help)   usage; exit 0 ;;
        *)           log "Unknown option: $1"; usage; exit 2 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Auto-detect: if no tool flags given, target tools whose home dir exists.
# ---------------------------------------------------------------------------
if [[ "${#want_tool[@]}" -eq 0 && "${#want_dir[@]}" -eq 0 ]]; then
    detected=0
    for id in "${TOOL_IDS[@]}"; do
        local_dir="$(tool_dir "${id}")"
        parent_dir="$(dirname "${local_dir}")"
        if [[ -d "${parent_dir}" ]]; then
            want_tool+=("${id}")
            detected=1
        fi
    done
    if [[ "${detected}" -eq 0 ]]; then
        log "No tool home directories detected."
        log "Re-run with --tools <id,...> or --all to install to specific tools."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Source validation
# ---------------------------------------------------------------------------
if [[ ! -d "${SKILLS_SRC}" ]]; then
    log "Source skills directory not found at ${SKILLS_SRC}"; exit 1
fi

skills=()
while IFS= read -r d; do
    skills+=("${d}")
done < <(find "${SKILLS_SRC}" -maxdepth 1 -mindepth 1 -type d -name 'sdlc-*' | sort)
if [[ "${#skills[@]}" -eq 0 ]]; then
    log "No sdlc-* skills found under ${SKILLS_SRC}"; exit 1
fi

# ---------------------------------------------------------------------------
# Install / uninstall functions
#
# Both operate on the sdlc-* NAMESPACE inside the target directory, not on the
# names this repo happens to ship today. A skill that was merged or renamed
# between versions (sdlc-requirements, sdlc-architect, sdlc-document,
# sdlc-migrate) must be removed on upgrade, or it lingers and keeps answering
# its old slash command against paths that no longer exist.
# ---------------------------------------------------------------------------

# Print every sdlc-* skill directory currently installed in a target.
installed_skills_in() {
    local target="$1"
    [[ -d "${target}" ]] || return 0
    find "${target}" -maxdepth 1 -mindepth 1 -type d -name 'sdlc-*' | sort
}

# True when this repo still ships a skill by that name.
is_shipped() {
    local name="$1" skill
    for skill in "${skills[@]}"; do
        [[ "$(basename "${skill}")" == "${name}" ]] && return 0
    done
    return 1
}

# True when this repo used to ship a skill by that name.
is_retired() {
    local name="$1" retired
    for retired in "${RETIRED_SKILLS[@]}"; do
        [[ "${retired}" == "${name}" ]] && return 0
    done
    return 1
}

install_to() {
    local target="$1"
    log "Target: ${target}"
    run mkdir -p "${target}"

    local dest name
    while IFS= read -r dest; do
        [[ -n "${dest}" ]] || continue
        name="$(basename "${dest}")"
        if is_shipped "${name}"; then
            continue
        elif is_retired "${name}"; then
            run rm -rf "${dest}"
            log "  removed ${name} (no longer shipped)"
        else
            log "  kept ${name} (not ours — left untouched)"
        fi
    done < <(installed_skills_in "${target}")

    for skill in "${skills[@]}"; do
        name="$(basename "${skill}")"
        dest="${target}/${name}"
        if [[ -e "${dest}" ]]; then run rm -rf "${dest}"; fi
        run cp -R "${skill}" "${dest}"
        log "  installed ${name}"
    done
}

uninstall_from() {
    local target="$1"
    log "Target: ${target} (uninstall)"
    if [[ ! -d "${target}" ]]; then
        log "  nothing to remove — directory does not exist"; return
    fi

    local dest name removed=0
    while IFS= read -r dest; do
        [[ -n "${dest}" ]] || continue
        name="$(basename "${dest}")"
        if ! is_shipped "${name}" && ! is_retired "${name}"; then
            log "  kept ${name} (not ours — left untouched)"
            continue
        fi
        run rm -rf "${dest}"
        log "  removed ${name}"
        removed=1
    done < <(installed_skills_in "${target}")
    [[ "${removed}" -eq 1 ]] || log "  nothing to remove"
}

action() {
    local target="$1"
    if [[ "${uninstall}" -eq 1 ]]; then uninstall_from "${target}"
    else install_to "${target}"
    fi
}

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
for id in "${TOOL_IDS[@]}"; do
    if want "${id}"; then
        warn_if_unverified "${id}"
        action "$(tool_dir "${id}")"
    fi
done

for dir in "${want_dir[@]+"${want_dir[@]}"}"; do
    action "${dir}"
done

log "Done."
