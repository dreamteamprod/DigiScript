

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REPO_ROOT=$(git rev-parse --show-toplevel)

echo -e "${YELLOW}Setting up pre-commit hook...${NC}"
ln -sf "$REPO_ROOT/hooks/pre-commit" "$REPO_ROOT/.git/hooks/pre-commit"

echo -e "${GREEN}Git hooks setup complete!${NC}"
