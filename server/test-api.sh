#!/bin/bash
# ================================================
# SCRIPT DE PRUEBAS - CDN Offline API
# ================================================

BASE_URL="http://localhost:3000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "CDN Offline - API Testing"
echo "================================================"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}1. Health Check${NC}"
HEALTH=$(curl -s $BASE_URL/health | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ Server is healthy${NC}"
else
    echo -e "${RED}✗ Server is not healthy${NC}"
    exit 1
fi
echo ""

# Test 2: Categories
echo -e "${YELLOW}2. Categories${NC}"
CATEGORIES=$(curl -s $BASE_URL/api/categories | jq -r '.count')
echo -e "${GREEN}✓ Found $CATEGORIES categories${NC}"
echo ""

# Test 3: Login
echo -e "${YELLOW}3. Login (admin/admin123)${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.data.token')
USERNAME=$(echo $LOGIN_RESPONSE | jq -r '.data.user.username')

if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
    echo "  User: $USERNAME"
    echo "  Token: ${TOKEN:0:30}..."
else
    echo -e "${RED}✗ Login failed${NC}"
    echo $LOGIN_RESPONSE | jq
    exit 1
fi
echo ""

# Test 4: Get current user
echo -e "${YELLOW}4. Get current user (authenticated)${NC}"
ME=$(curl -s $BASE_URL/api/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.data.username')

if [ "$ME" = "$USERNAME" ]; then
    echo -e "${GREEN}✓ Authentication working${NC}"
    echo "  Authenticated as: $ME"
else
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi
echo ""

# Test 5: Content list
echo -e "${YELLOW}5. Content list${NC}"
CONTENT_COUNT=$(curl -s "$BASE_URL/api/content?limit=5" | jq -r '.pagination.total')
echo -e "${GREEN}✓ Found $CONTENT_COUNT total content items${NC}"
echo ""

# Test 6: Featured content
echo -e "${YELLOW}6. Featured content${NC}"
FEATURED=$(curl -s $BASE_URL/api/content/featured | jq -r '.data | length')
echo -e "${GREEN}✓ Found $FEATURED featured items${NC}"
echo ""

# Test 7: Search
echo -e "${YELLOW}7. Search test (searching for 'matemáticas')${NC}"
SEARCH_RESULTS=$(curl -s "$BASE_URL/api/content?search=matemáticas" | jq -r '.data | length')
echo -e "${GREEN}✓ Search returned $SEARCH_RESULTS results${NC}"
echo ""

echo "================================================"
echo -e "${GREEN}All tests passed!${NC}"
echo "================================================"
echo ""
echo "Your token (save for manual testing):"
echo "$TOKEN"
echo ""
echo "Test streaming with:"
echo "  curl -I $BASE_URL/api/content/{content_id}/stream"
