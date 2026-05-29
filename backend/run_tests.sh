#!/bin/bash
# Test Runner Script
# 测试运行脚本

set -e

echo "=========================================="
echo "Running 24小时小说 Agent Test Suite"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in backend directory
if [ ! -f "app/main.py" ]; then
    echo -e "${RED}Error: Please run from backend directory${NC}"
    exit 1
fi

# Set test environment
export APP_ENV=test
export APP_API_KEY=test-api-key-for-ci
export APP_SECRET_KEY=test-secret-key-for-ci
export DATABASE_URL=sqlite:///./data/test.db
export LOG_LEVEL=ERROR

echo ""
echo "Step 1: Running Health Check Tests..."
echo "------------------------------------------"
pytest tests/test_health.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Health tests passed${NC}"

echo ""
echo "Step 2: Running Auth Tests..."
echo "------------------------------------------"
pytest tests/test_auth.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Auth tests passed${NC}"

echo ""
echo "Step 3: Running Upload Security Tests..."
echo "------------------------------------------"
pytest tests/test_upload_security.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Upload security tests passed${NC}"

echo ""
echo "Step 4: Running Cascade Delete Tests..."
echo "------------------------------------------"
pytest tests/test_cascade_delete.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Cascade delete tests passed${NC}"

echo ""
echo "Step 5: Running Task Service Tests..."
echo "------------------------------------------"
pytest tests/test_task_service.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Task service tests passed${NC}"

echo ""
echo "Step 6: Running Exception Tests..."
echo "------------------------------------------"
pytest tests/test_exceptions.py -v --tb=short || exit 1
echo -e "${GREEN}✓ Exception tests passed${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "=========================================="
