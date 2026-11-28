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
# --shm-size: Chromium crashes ("Target crashed") with Docker's default 64MB /dev/shm.
docker run --rm --shm-size=1g \
  -v "${ROOT}:/work" \
  -v digiscript-docs-node-modules:/work/client/node_modules \
  -v digiscript-docs-pnpm-store:/root/.local/share/pnpm \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  -e "DOCS_UPDATE=${DOCS_UPDATE:-changed}" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  "${IMAGE}" \
  bash -c '
    set -e
    # The container runs as root on a bind mount: hand everything it wrote back to the host user
    # (images, the frontend build, the copied docs, and the Playwright report folders). Done from
    # an EXIT trap so it also runs when an earlier step fails.
    fix_owner() {
      for path in /work/docs/images /work/server/static /work/client/public/docs \
                  /work/client/test-results /work/client/playwright-report /work/client/junit; do
        if [ -e "$path" ]; then
          chown -R "${HOST_UID}:${HOST_GID}" "$path" || echo "warning: could not chown $path" >&2
        fi
      done
    }
    trap fix_owner EXIT
    pnpm install --frozen-lockfile --store-dir /root/.local/share/pnpm/store
    pnpm run build
    pnpm run test:e2e:docs
  '
