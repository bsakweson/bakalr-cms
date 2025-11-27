#!/bin/bash
set -e

echo "🧪 Starting E2E Test Suite with Docker"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo "${YELLOW}🧹 Cleaning up Docker containers and volumes...${NC}"
    docker-compose down -v
    echo "${GREEN}✅ Cleanup complete${NC}"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "${RED}❌ Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Start services
echo "${YELLOW}🐳 Starting Docker services...${NC}"
docker-compose up -d

# Wait for backend to be healthy
echo "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker logs bakalr-backend 2>&1 | grep -q "Application startup complete"; then
        echo "${GREEN}✅ Backend is ready${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "${RED}❌ Backend failed to start${NC}"
    echo "Backend logs:"
    docker logs bakalr-backend --tail 50
    exit 1
fi

# Wait for frontend to be healthy
echo "${YELLOW}⏳ Waiting for frontend to be ready...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo "${GREEN}✅ Frontend is ready${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "${RED}❌ Frontend failed to start${NC}"
    echo "Frontend logs:"
    docker logs bakalr-frontend --tail 50
    exit 1
fi

# Show service status
echo ""
echo "${GREEN}✅ All services are running:${NC}"
docker-compose ps

# Run Playwright tests
echo ""
echo "${YELLOW}🎭 Running Playwright E2E tests...${NC}"
cd frontend

# Install Playwright browsers if needed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "${YELLOW}📦 Installing Playwright browsers...${NC}"
    npx playwright install
fi

# Run tests
if PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e; then
    echo ""
    echo "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "${YELLOW}📊 Test report available at: frontend/playwright-report/index.html${NC}"
    echo "Run 'npm run test:e2e:report' to view the report"
    exit 1
fi
