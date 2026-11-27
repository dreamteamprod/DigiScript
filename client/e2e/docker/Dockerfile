# Canonical environment for regenerating the documentation screenshots.
#
# Chromium renders text slightly differently on macOS, Windows and Linux, so docs
# screenshots are only ever generated here to keep the output stable between people.
# Built and run by scripts/docs-screenshots-docker.sh - not used by CI's normal E2E job.
# Build context is the repo root, trimmed to requirements.txt by Dockerfile.dockerignore.
FROM python:3.13-bookworm

ARG NODE_MAJOR=24
ARG PLAYWRIGHT_VERSION

# Node (matching the repo's Node 24.x requirement) and pnpm via corepack.
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && corepack enable \
    && rm -rf /var/lib/apt/lists/*

# Backend dependencies, so global-setup can launch `python3 main.py`.
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Chromium + its system libraries and fonts. The version must match @playwright/test.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@${PLAYWRIGHT_VERSION} install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/client
