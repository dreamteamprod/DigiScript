#!/usr/bin/env bash
# Regenerate docs/images/** from the E2E suite inside the canonical Linux container.
#
#   pnpm run test:e2e:docs:docker      (from client/)
#   scripts/docs-screenshots-docker.sh (from anywhere)
#
# Builds the frontend, runs the full Playwright suite with DOCS_SCREENSHOTS=1 and writes
# changed screenshots straight into the checkout's docs/images. Unchanged images are left
# byte-identical, so `git status` afterwards shows only real visual changes.
# DOCS_UPDATE=all rewrites every image regardless (use after changing how screenshots are taken).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="digiscript-docs-screenshots"

# The container's Playwright must match the version pinned in the lockfile exactly.
PLAYWRIGHT_VERSION="$(sed -n 's/.*@playwright\/test@\([0-9][0-9.]*\).*/\1/p' "${ROOT}/client/pnpm-lock.yaml" | head -1)"
if [ -z "${PLAYWRIGHT_VERSION}" ]; then
  echo "Could not determine the @playwright/test version from client/pnpm-lock.yaml" >&2
  exit 1
fi

echo ">> Building ${IMAGE} (Playwright ${PLAYWRIGHT_VERSION})"
docker build \
  --build-arg "PLAYWRIGHT_VERSION=${PLAYWRIGHT_VERSION}" \
  -f "${ROOT}/client/e2e/docker/Dockerfile" \
  -t "${IMAGE}" \
  "${ROOT}"

echo ">> Running the E2E suite in docs mode"
# node_modules lives in a named volume so the Linux install never touches the host's.
docker run --rm \
  -v "${ROOT}:/work" \
  -v digiscript-docs-node-modules:/work/client/node_modules \
  -v digiscript-docs-pnpm-store:/root/.local/share/pnpm \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  -e "DOCS_UPDATE=${DOCS_UPDATE:-changed}" \
  "${IMAGE}" \
  bash -c '
    set -e
    pnpm install --frozen-lockfile --store-dir /root/.local/share/pnpm/store
    pnpm run build
    status=0
    pnpm run test:e2e:docs || status=$?
    chown -R "${HOST_UID}:${HOST_GID}" /work/docs/images 2>/dev/null || true
    exit $status
  '
