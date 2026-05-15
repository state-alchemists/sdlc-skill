#!/usr/bin/env bash
# install.sh — Install sdlc-ai skills into zrb and/or Claude Code skill directories.
#
# Default behaviour (no flags): installs into whichever target directories
# already exist on this machine. If neither exists, prints a hint and exits.
#
# Examples:
#   bin/install.sh                    # auto-detect targets
#   bin/install.sh --zrb              # install only to ~/.zrb/skills/
#   bin/install.sh --claude           # install only to ~/.claude/skills/
#   bin/install.sh --all              # install to both, creating dirs as needed
#   bin/install.sh --uninstall --all  # remove sdlc-* skills from both
#   bin/install.sh --dry-run --all    # show what would happen without doing it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_SRC="${REPO_ROOT}/skills"

ZRB_DIR="${HOME}/.zrb/skills"
CLAUDE_DIR="${HOME}/.claude/skills"

want_zrb=0
want_claude=0
explicit=0
uninstall=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Options:
  --zrb         Target ~/.zrb/skills/
  --claude      Target ~/.claude/skills/
  --all         Target both, creating directories if missing
  --uninstall   Remove sdlc-* skills from selected targets (default: leave them)
  --dry-run     Print what would happen without copying or deleting
  -h, --help    This message

With no target flags, install.sh installs to whichever target directory
already exists. If neither exists, it exits with a hint.
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zrb)       want_zrb=1; explicit=1 ;;
        --claude)    want_claude=1; explicit=1 ;;
        --all)       want_zrb=1; want_claude=1; explicit=1 ;;
        --uninstall) uninstall=1 ;;
        --dry-run)   dry_run=1 ;;
        -h|--help)   usage; exit 0 ;;
        *)           log "Unknown option: $1"; usage; exit 2 ;;
    esac
    shift
done

if [[ "${explicit}" -eq 0 ]]; then
    [[ -d "${HOME}/.zrb" ]]    && want_zrb=1
    [[ -d "${HOME}/.claude" ]] && want_claude=1
    if [[ "${want_zrb}" -eq 0 && "${want_claude}" -eq 0 ]]; then
        log "No target directories detected (~/.zrb or ~/.claude). Re-run with --zrb, --claude, or --all."
        exit 1
    fi
fi

if [[ ! -d "${SKILLS_SRC}" ]]; then
    log "Source skills directory not found at ${SKILLS_SRC}"
    exit 1
fi

# Enumerate sdlc-* skill directories (portable: no `mapfile`, which is bash 4+).
skills=()
while IFS= read -r d; do
    skills+=("${d}")
done < <(find "${SKILLS_SRC}" -maxdepth 1 -mindepth 1 -type d -name 'sdlc-*' | sort)
if [[ "${#skills[@]}" -eq 0 ]]; then
    log "No sdlc-* skills found under ${SKILLS_SRC}"
    exit 1
fi

install_to() {
    local target="$1"
    log "Target: ${target}"
    run mkdir -p "${target}"
    for skill in "${skills[@]}"; do
        local name
        name="$(basename "${skill}")"
        local dest="${target}/${name}"
        if [[ -e "${dest}" ]]; then
            run rm -rf "${dest}"
        fi
        run cp -R "${skill}" "${dest}"
        log "  installed ${name}"
    done
}

uninstall_from() {
    local target="$1"
    log "Target: ${target} (uninstall)"
    if [[ ! -d "${target}" ]]; then
        log "  nothing to remove — directory does not exist"
        return
    fi
    for skill in "${skills[@]}"; do
        local name
        name="$(basename "${skill}")"
        local dest="${target}/${name}"
        if [[ -e "${dest}" ]]; then
            run rm -rf "${dest}"
            log "  removed ${name}"
        fi
    done
}

action() {
    local target="$1"
    if [[ "${uninstall}" -eq 1 ]]; then
        uninstall_from "${target}"
    else
        install_to "${target}"
    fi
}

[[ "${want_zrb}"    -eq 1 ]] && action "${ZRB_DIR}"
[[ "${want_claude}" -eq 1 ]] && action "${CLAUDE_DIR}"

log "Done."
