#!/usr/bin/env bash
# Installs the current stable Claude Code CLI with the official native installer, verifying the
# release before anything downloaded is executed.
#
# Source: https://code.claude.com/docs/en/setup ("Verify binary integrity"). Anthropic's
# install.sh checks a binary's SHA-256 against manifest.json but not the manifest's GPG
# signature; this script performs the same download, adds the signature check, and then runs the
# verified binary's own `install` subcommand exactly as install.sh does.
set -euo pipefail

readonly CHANNEL="stable"
readonly BASE_URL="https://downloads.claude.ai/claude-code-releases"
readonly KEY_URL="https://downloads.claude.ai/keys/claude-code.asc"
# Fingerprint published in the setup documentation; the key served by KEY_URL must match it.
readonly KEY_FINGERPRINT="31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE"

log() { printf '%s [claude-code] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() {
    log "ERROR: $*"
    exit 1
}
fetch() { curl --proto '=https' --tlsv1.2 -fsSL --retry 3 "$1" -o "$2" || die "download failed: $1"; }
sha256() { sha256sum "$1" | cut -d' ' -f1; }

[[ "$(id -u)" -ne 0 ]] || die "run as the container user, not root"
for cmd in curl gpg jq sha256sum; do
    command -v "${cmd}" >/dev/null || die "required command not found: ${cmd}"
done

case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) platform="linux-x64" ;;
    Linux-aarch64) platform="linux-arm64" ;;
    *) die "unsupported platform: $(uname -s) $(uname -m)" ;;
esac
if ldd /bin/ls 2>&1 | grep -q musl; then
    platform="${platform}-musl"
fi

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
export GNUPGHOME="${work}/gnupg"
mkdir -m 700 "${GNUPGHOME}"

fetch "${BASE_URL}/${CHANNEL}" "${work}/channel"
version="$(tr -d '[:space:]' < "${work}/channel")"
[[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "channel ${CHANNEL} returned an invalid version"
log "channel ${CHANNEL} resolves to ${version} (${platform})"

fetch "${KEY_URL}" "${work}/key.asc"
log "signing key ${KEY_URL} sha256 $(sha256 "${work}/key.asc")"
fingerprints="$(gpg --batch --with-colons --show-keys "${work}/key.asc" | awk -F: '$1 == "fpr" { print $10 }')"
[[ "${fingerprints}" == "${KEY_FINGERPRINT}" ]] \
    || die "signing key fingerprint mismatch: got '${fingerprints}', expected ${KEY_FINGERPRINT}"
gpg --batch --quiet --import "${work}/key.asc"

fetch "${BASE_URL}/${version}/manifest.json" "${work}/manifest.json"
fetch "${BASE_URL}/${version}/manifest.json.sig" "${work}/manifest.json.sig"
log "manifest sha256 $(sha256 "${work}/manifest.json")"
# --status-fd output is parsed instead of the exit code alone so that only a valid signature by
# the pinned primary key is accepted.
gpg --batch --status-fd 3 --verify "${work}/manifest.json.sig" "${work}/manifest.json" \
    3> "${work}/gpg.status" 2>/dev/null || die "manifest signature verification failed"
grep -Eq "^\[GNUPG:\] VALIDSIG .* ${KEY_FINGERPRINT}$" "${work}/gpg.status" \
    || die "manifest is not signed by ${KEY_FINGERPRINT}"
log "manifest signature valid (${KEY_FINGERPRINT})"

[[ "$(jq -r '.version' "${work}/manifest.json")" == "${version}" ]] \
    || die "manifest version does not match ${version}"
expected="$(jq -r --arg p "${platform}" '.platforms[$p].checksum // empty' "${work}/manifest.json")"
[[ "${expected}" =~ ^[a-f0-9]{64}$ ]] || die "no checksum for ${platform} in the manifest"

fetch "${BASE_URL}/${version}/${platform}/claude" "${work}/claude"
actual="$(sha256 "${work}/claude")"
[[ "${actual}" == "${expected}" ]] \
    || die "binary checksum mismatch: got ${actual}, expected ${expected}"
log "binary sha256 ${actual} matches the signed manifest"

chmod +x "${work}/claude"
"${work}/claude" install "${CHANNEL}"

installed="$("${HOME}/.local/bin/claude" --version)"
[[ "${installed}" == "${version} "* ]] || die "installed version '${installed}' is not ${version}"
log "installed ${installed} at ${HOME}/.local/bin/claude"
