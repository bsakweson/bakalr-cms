#!/bin/bash
set -e

echo "🚀 Quick Test Script - Testing only Chromium"
echo "=============================================="

cd frontend

# Run tests with only Chromium, 4 workers
echo "Running Playwright tests (Chromium only)..."
npx playwright test --project=chromium --workers=4

echo ""
echo "✅ Quick test complete!"
