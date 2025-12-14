#!/bin/bash
set -e

DOCS_SOURCE="../docs"
DOCS_DEST="./public/docs"

echo "Copying documentation assets..."

# Remove existing docs
rm -rf "$DOCS_DEST"

# Copy docs directory
cp -r "$DOCS_SOURCE" "$DOCS_DEST"

echo "Documentation assets copied successfully"
