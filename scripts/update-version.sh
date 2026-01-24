#!/usr/bin/env bash
set -e

# Version Update Helper Script
# Synchronizes version numbers across client, electron, and server components.
#
# Usage: ./scripts/update-version.sh <version>
# Example: ./scripts/update-version.sh 0.24.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_error() {
    echo -e "${RED}Error:${NC} $1" >&2
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Validate argument exists
if [ -z "$1" ]; then
    print_error "Version argument required"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.24.0"
    exit 1
fi

VERSION="$1"

# Validate semver format (X.Y.Z)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    print_error "Invalid version format: $VERSION"
    echo "Version must be in semver format: X.Y.Z (e.g., 0.24.0)"
    exit 1
fi

echo "Updating version to $VERSION..."
echo

# Update client/package.json
print_info "Updating client/package.json..."
cd "$PROJECT_ROOT/client"
npm version "$VERSION" --no-git-tag-version --allow-same-version > /dev/null
print_success "client/package.json updated"

# Update electron/package.json
print_info "Updating electron/package.json..."
cd "$PROJECT_ROOT/electron"
npm version "$VERSION" --no-git-tag-version --allow-same-version > /dev/null
print_success "electron/package.json updated"

# Update server/pyproject.toml
print_info "Updating server/pyproject.toml..."
cd "$PROJECT_ROOT/server"

# Use portable sed syntax (macOS vs Linux compatibility)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS BSD sed requires empty string for in-place edit
    sed -i '' "s/^version = \"[0-9]*\.[0-9]*\.[0-9]*\"/version = \"$VERSION\"/" pyproject.toml
else
    # GNU sed (Linux)
    sed -i "s/^version = \"[0-9]*\.[0-9]*\.[0-9]*\"/version = \"$VERSION\"/" pyproject.toml
fi
print_success "server/pyproject.toml updated"

echo
echo -e "${GREEN}Version successfully updated to $VERSION${NC}"
echo
echo "Updated files:"
echo "  - client/package.json"
echo "  - electron/package.json"
echo "  - server/pyproject.toml"
