#!/usr/bin/env bash
# Provisions a freshly created dev container. Every step is logged with a UTC timestamp to
# ~/.cache/devcontainer/post-create.log so the setup can be audited after the fact.
set -euo pipefail

readonly LOG_DIR="${HOME}/.cache/devcontainer"
readonly LOG_FILE="${LOG_DIR}/post-create.log"
mkdir -p "${LOG_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

log() { printf '%s [post-create] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
step() {
    log "BEGIN $1"
    "${@:2}"
    log "END   $1"
}
trap 'log "FAILED at line ${LINENO}: ${BASH_COMMAND}"' ERR

cd "$(git rev-parse --show-toplevel)"

log "repository $(git rev-parse HEAD) on $(uname -srm)"
log "nix $(nix --version)"
log "flake.lock sha256 $(sha256sum flake.lock | cut -d' ' -f1)"

# Builds the devShell once so that the first terminal opens without waiting.
step "nix develop (warm)" nix develop --command true

# Taken from the flake's locked nixpkgs so the versions follow flake.lock.
step "direnv and nix-direnv" nix profile add --inputs-from . nixpkgs#direnv nixpkgs#nix-direnv

configure_direnv() {
    mkdir -p "${HOME}/.config/direnv"
    printf 'source %s\n' "${HOME}/.nix-profile/share/nix-direnv/direnvrc" \
        > "${HOME}/.config/direnv/direnvrc"
    # shellcheck disable=SC2016 # Expanded by the interactive shell, not here.
    local hook='eval "$(direnv hook bash)"'
    grep -qxF "${hook}" "${HOME}/.bashrc" || printf '\n%s\n' "${hook}" >> "${HOME}/.bashrc"
    [[ -e .envrc ]] || cp .envrc.sample .envrc
    direnv allow .
}
step "direnv configuration" configure_direnv

step "git hooks (hk install)" nix develop --command hk install
step "git commit template" git config commit.template .gitmessage

step "Claude Code CLI" bash .devcontainer/install-claude-code.sh

log "tool versions:"
nix develop --command bash -c 'rustc --version; cargo --version; hk --version; cargo deny --version'
claude --version
log "provisioning complete"
