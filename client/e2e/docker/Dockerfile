# Canonical environment for regenerating the documentation screenshots.
#
# Chromium renders text slightly differently on macOS, Windows and Linux, so docs
# screenshots are only ever generated here to keep the output stable between people.
# Built and run by scripts/docs-screenshots-docker.sh - not used by CI's normal E2E job.
# Build context is the repo root, trimmed to requirements.txt by Dockerfile.dockerignore.
FROM python:3.13-bookworm

ARG PLAYWRIGHT_VERSION

# Node (matching the repo's Node 24.x requirement), copied from the official image rather than
# installed by piping a vendor script into a root shell; pnpm via corepack.
# Only node and its bundled modules are taken (the image's other /usr/local entries, such as a
# yarn symlink into /opt, would dangle), then the three launcher symlinks are recreated.
COPY --from=node:24-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -s ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack \
    && corepack enable

# Backend dependencies, so global-setup can launch `python3 main.py`.
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Chromium + its system libraries and fonts. The version must match @playwright/test.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@${PLAYWRIGHT_VERSION} install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/client
