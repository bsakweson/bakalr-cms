#!/bin/bash
#
# Bakalr CMS Seed Script
#
# Seeds the CMS with boutique theme, content types, and sample data.
#
# Usage:
#   ./seed.sh                    # Full seed (interactive password prompt)
#   ./seed.sh --only themes      # Only seed themes
#   ./seed.sh --only content-types
#   ./seed.sh --only locales
#   ./seed.sh --only sample-data
#   ./seed.sh --dry-run          # Preview what would be created
#
# Configuration:
#   SEED_ADMIN_EMAIL    - Admin email (default: bsakweson@gmail.com)
#   SEED_ADMIN_PASSWORD - Admin password (will prompt if not set)
#   SEED_API_URL        - API URL (default: http://localhost:8000/api/v1)
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
: "${SEED_ADMIN_EMAIL:=bsakweson@gmail.com}"
: "${SEED_API_URL:=http://localhost:8000/api/v1}"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Bakalr CMS Seed Runner               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Email:    ${GREEN}${SEED_ADMIN_EMAIL}${NC}"
echo -e "API URL:  ${GREEN}${SEED_API_URL}${NC}"
echo ""

# Check if password is set, otherwise prompt
if [ -z "$SEED_ADMIN_PASSWORD" ]; then
    echo -e "${YELLOW}Enter password for ${SEED_ADMIN_EMAIL}:${NC}"
    read -s SEED_ADMIN_PASSWORD
    export SEED_ADMIN_PASSWORD
    echo ""
fi

# Check if backend is running
echo -e "${BLUE}Checking API availability...${NC}"
if ! curl -s "${SEED_API_URL}/health" > /dev/null 2>&1; then
    # Try without /health endpoint
    if ! curl -s "${SEED_API_URL}/../docs" > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: API may not be running at ${SEED_API_URL}${NC}"
        echo "Make sure the backend is started with: docker-compose up -d"
        echo ""
    fi
fi

# Run the seed script
echo -e "${BLUE}Running seed script...${NC}"
echo ""

cd "$(dirname "$0")"
poetry run python seeds/seed_runner.py "$@"

echo ""
echo -e "${GREEN}Done!${NC}"
