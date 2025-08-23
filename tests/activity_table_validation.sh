#!/bin/bash

# Activity Table Validation Script
# This script tests the activity table implementation

# Configuration
API_URL="http://localhost:8888/api/api/activities"  # Changed port to 8888 to match container
TIMEOUT=10

# Function to display test results
display_result() {
    local test_name=$1
    local result=$2
    local message=$3

    if [ "$result" = "PASS" ]; then
        echo "✅ $test_name: $message"
    else
        echo "❌ $test_name: $message"
    fi
}

# Function to wait for API to be ready
wait_for_api() {
    echo "Waiting for API to start..."
    attempts=0
    max_attempts=60  # Increased timeout to 60 seconds

    while true; do
        # Check for startup messages
        if curl -s -m 1 "http://localhost:8888" | grep -q "Uvicorn running on" || \
           curl -s -m 1 "http://localhost:8888" | grep -q "Application startup complete" || \
           curl -s -m 1 "http://localhost:8888" | grep -q "Server is ready"; then
            echo "API started successfully"
            break
        fi

        attempts=$((attempts+1))
        if [ $attempts -ge $max_attempts ]; then
            echo "API failed to start within $max_attempts seconds"
            exit 1
        fi

        sleep 1
    done
}

# Wait for API to be ready
wait_for_api

# Test 1: Basic API response
echo "Running basic API response test..."
response=$(curl -s -m $TIMEOUT "$API_URL" | jq '.')
if [ $? -eq 0 ]; then
    if [[ "$response" == *"activities"* ]] && [[ "$response" == *"total_pages"* ]] && [[ "$response" == *"status"* ]]; then
        display_result "Basic API Response" PASS "API returns expected structure"
    else
        display_result "Basic API Response" FAIL "API response doesn't contain expected fields"
    fi
else
    display_result "Basic API Response" FAIL "API request failed"
fi

# Test 2: Pagination test
echo "Running pagination test..."
page1=$(curl -s -m $TIMEOUT "$API_URL?page=1" | jq '.')
page2=$(curl -s -m $TIMEOUT "$API_URL?page=2" | jq '.')

if [ $? -eq 0 ]; then
    page1_count=$(echo "$page1" | jq '.activities | length')
    page2_count=$(echo "$page2" | jq '.activities | length')

    if [ "$page1_count" -gt 0 ] && [ "$page2_count" -gt 0 ]; then
        display_result "Pagination Test" PASS "Both pages contain activities"
    else
        display_result "Pagination Test" FAIL "One or more pages are empty"
    fi
else
    display_result "Pagination Test" FAIL "API request failed"
fi

# Test 3: Data consistency test
echo "Running data consistency test..."
activity_id=$(echo "$page1" | jq -r '.activities[0].id')
activity_name=$(echo "$page1" | jq -r '.activities[0].name')

details_response=$(curl -s -m $TIMEOUT "$API_URL/$activity_id" | jq '.')
if [ $? -eq 0 ]; then
    details_id=$(echo "$details_response" | jq -r '.id')
    details_name=$(echo "$details_response" | jq -r '.name')

    if [ "$activity_id" = "$details_id" ] && [ "$activity_name" = "$details_name" ]; then
        display_result "Data Consistency Test" PASS "Activity details match API response"
    else
        display_result "Data Consistency Test" FAIL "Activity details don't match API response"
    fi
else
    display_result "Data Consistency Test" FAIL "API request failed"
fi

# Test 4: Error handling test
echo "Running error handling test..."
error_response=$(curl -s -m $TIMEOUT "$API_URL/999999999" | jq '.')
if [ $? -eq 0 ]; then
    if [[ "$error_response" == *"detail"* ]] && [[ "$error_response" == *"not found"* ]]; then
        display_result "Error Handling Test" PASS "API returns expected error for non-existent activity"
    else
        display_result "Error Handling Test" FAIL "API doesn't return expected error for non-existent activity"
    fi
else
    display_result "Error Handling Test" FAIL "API request failed"
fi

echo "All tests completed."
