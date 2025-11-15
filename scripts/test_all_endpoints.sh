#!/bin/bash
# Comprehensive API endpoint testing script

echo "🧪 TESTING ALL FINCLATOR API ENDPOINTS"
echo "======================================================================"
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

# Function to test an endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Test $test_count: $name${NC}"
    echo "URL: $url"
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status_code)"
        pass_count=$((pass_count + 1))
        
        # Show first 200 chars of response
        echo "$body" | head -c 200
        echo ""
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status_code)"
        fail_count=$((fail_count + 1))
        echo "$body" | head -c 200
    fi
    echo ""
    echo "----------------------------------------------------------------------"
    echo ""
}

# Wait for server to start
echo "Waiting for API server to start..."
sleep 3

# Test 1: Health check
test_endpoint "Health Check" "$BASE_URL/health"

# Test 2: Root endpoint
test_endpoint "Root Endpoint" "$BASE_URL/"

# Test 3: Overall signals - BTC SHORT
test_endpoint "Signal: BTC SHORT" "$BASE_URL/signals?asset=BTC&horizon=SHORT"

# Test 4: Overall signals - BTC MEDIUM
test_endpoint "Signal: BTC MEDIUM" "$BASE_URL/signals?asset=BTC&horizon=MEDIUM"

# Test 5: Overall signals - BTC LONG
test_endpoint "Signal: BTC LONG" "$BASE_URL/signals?asset=BTC&horizon=LONG"

# Test 6: Overall signals - GOLD MEDIUM
test_endpoint "Signal: GOLD MEDIUM" "$BASE_URL/signals?asset=GOLD&horizon=MEDIUM"

# Test 7: Overall signals - SPX LONG
test_endpoint "Signal: SPX LONG" "$BASE_URL/signals?asset=SPX&horizon=LONG"

# Test 8: School signals - BTC MEDIUM
test_endpoint "School Signals: BTC MEDIUM" "$BASE_URL/signals/school-signals?asset=BTC&horizon=MEDIUM"

# Test 9: School signals - GOLD MEDIUM
test_endpoint "School Signals: GOLD MEDIUM" "$BASE_URL/signals/school-signals?asset=GOLD&horizon=MEDIUM"

# Test 10: List all influencers
test_endpoint "List Influencers" "$BASE_URL/influencers"

# Test 11: Get specific influencer (Sant Manukyan)
test_endpoint "Get Influencer: Sant Manukyan" "$BASE_URL/influencers/8f3d9c5b-67ef-4dad-8982-dd2eceef2c31"

# Test 12: Invalid asset (should fail)
test_endpoint "Invalid Asset (Expected Fail)" "$BASE_URL/signals?asset=INVALID&horizon=SHORT" 400

# Test 13: Invalid horizon (should fail)
test_endpoint "Invalid Horizon (Expected Fail)" "$BASE_URL/signals?asset=BTC&horizon=INVALID" 400

# Test 14: OpenAPI documentation
test_endpoint "OpenAPI Docs JSON" "$BASE_URL/openapi.json"

# Summary
echo "======================================================================"
echo "TEST SUMMARY"
echo "======================================================================"
echo -e "Total Tests:  $test_count"
echo -e "${GREEN}Passed:       $pass_count${NC}"
echo -e "${RED}Failed:       $fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo "✅ API is ready for production"
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo "❌ Review failures above"
    exit 1
fi

