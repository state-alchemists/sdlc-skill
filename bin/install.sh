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

# Ordered list for usage display and --tools all.
TOOL_IDS=(
    zrb claude codex opencode cursor windsurf github-copilot
    gemini amazon-q cline codebuddy continue crush factory iflow
    junie kilocode kiro lingma pi qoder qwen roocode
    antigravity bob costrict forgecode kimi trae vibe auggie
)

uninstall=0
dry_run=0
want_tool=()

# Check whether a tool ID is in the want_tool set.
want() {
    local id="$1" x
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
                      Use "all" for every known tool.
  --all               Alias for --tools all
  --uninstall         Remove sdlc-* skills from selected targets
  --dry-run           Print what would happen without changing anything
  -h, --help          This message

With no target flags, install.sh installs to whichever tool directories
already exist on this machine. If none exist, it exits with a hint.
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
        --all)       want_tool=("${TOOL_IDS[@]}") ;;
        --tools)
            shift
            if [[ $# -eq 0 ]]; then
                log "Missing value for --tools"; usage; exit 2
            fi
            if [[ "$1" == "all" ]]; then
                want_tool=("${TOOL_IDS[@]}")
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
if [[ "${#want_tool[@]}" -eq 0 ]]; then
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
# ---------------------------------------------------------------------------
install_to() {
    local target="$1"
    log "Target: ${target}"
    run mkdir -p "${target}"
    for skill in "${skills[@]}"; do
        local name; name="$(basename "${skill}")"
        local dest="${target}/${name}"
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
    for skill in "${skills[@]}"; do
        local name; name="$(basename "${skill}")"
        local dest="${target}/${name}"
        if [[ -e "${dest}" ]]; then
            run rm -rf "${dest}"
            log "  removed ${name}"
        fi
    done
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
        action "$(tool_dir "${id}")"
    fi
done

log "Done."
