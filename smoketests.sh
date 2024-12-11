#!/bin/bash

echo "Running smoke tests..."

export $(cat .env | xargs) # Load environment variables

BASE_URL="http://localhost:5000" # Auth routes use BASE_URL
API_URL="$BASE_URL/api" 

ECHO_JSON=false

# Test user credentials
TEST_USER="testuser"
TEST_PASS="testpass"
NEW_PASS="newpass123"

# Function to check if response is valid JSON
check_json() {
  if [ "$ECHO_JSON" = true ]; then
    echo "Checking JSON response: $1"
  fi

  if [ -z "$1" ]; then
    echo "Empty response received"
    return 1
  fi

  # Check if it's valid JSON
  echo "$1" | jq . >/dev/null 2>&1
  return $?
}

# Function to handle requests and check HTTP status code
make_request() {
  local RESPONSE=$(curl -s -w "\n%{http_code}" "$1" -X "$2" -H "Content-Type: application/json" -d "$3")
  local HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  local BODY=$(echo "$RESPONSE" | head -n-1)

  if [ "$HTTP_CODE" -ne "$4" ]; then
    echo "Request to $1 failed with code $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
  fi

  echo "$BODY"
}

# Cleanup function to delete test user if it exists
cleanup_test_user() {
    echo "Cleaning up previous test data..."
    DELETE_PAYLOAD="{\"username\": \"$TEST_USER\", \"password\": \"$TEST_PASS\"}"
    DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/delete-account" \
        -H "Content-Type: application/json" \
        -d "$DELETE_PAYLOAD")
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Cleanup response: $DELETE_RESPONSE"
    fi
}

# Run cleanup before tests
cleanup_test_user

echo "Starting API smoke tests..."

# 1. Health Check
echo "Testing health-check endpoint..."
HEALTH_RESPONSE=$(make_request "${API_URL}/health" "GET" "" 200)
check_json "$HEALTH_RESPONSE"
echo "Health-check endpoint is up."

# 2. Account Management Tests
echo -e "\nTesting account management endpoints..."

# Create Account
echo "Testing create-account endpoint..."
CREATE_PAYLOAD="{\"username\": \"$TEST_USER\", \"password\": \"$TEST_PASS\"}"
CREATE_RESPONSE=$(make_request "${BASE_URL}/create-account" "POST" "$CREATE_PAYLOAD" 201)
check_json "$CREATE_RESPONSE"
echo "Account creation test passed."

# Login
echo "Testing login endpoint..."
LOGIN_PAYLOAD="{\"username\": \"$TEST_USER\", \"password\": \"$TEST_PASS\"}"
LOGIN_RESPONSE=$(make_request "${BASE_URL}/login" "POST" "$LOGIN_PAYLOAD" 200)
check_json "$LOGIN_RESPONSE"
echo "Login test passed."

# Update Password
echo "Testing update-password endpoint..."
UPDATE_PASS_PAYLOAD="{\"username\": \"$TEST_USER\", \"old_password\": \"$TEST_PASS\", \"new_password\": \"$NEW_PASS\"}"
UPDATE_PASS_RESPONSE=$(make_request "${BASE_URL}/update-password" "PUT" "$UPDATE_PASS_PAYLOAD" 200)
check_json "$UPDATE_PASS_RESPONSE"
echo "Password update test passed."

# Verify Login with New Password
echo "Testing login with new password..."
NEW_LOGIN_PAYLOAD="{\"username\": \"$TEST_USER\", \"password\": \"$NEW_PASS\"}"
NEW_LOGIN_RESPONSE=$(make_request "${BASE_URL}/login" "POST" "$NEW_LOGIN_PAYLOAD" 200)
check_json "$NEW_LOGIN_RESPONSE"
echo "Login with new password test passed."

# 3. Library Management Tests
echo -e "\nTesting library management endpoints..."

# Initial Empty Library Check
echo "Testing get-library endpoint... (should be empty)"
GET_LIBRARY_ENDPOINT="${API_URL}/get-library?username=$TEST_USER"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

if [ "$(echo "$LIB_RESPONSE" | jq '.books | length')" -eq 0 ] && [ "$(echo "$LIB_RESPONSE" | jq '.favorites | length')" -eq 0 ]; then
    echo "Get-library test passed (empty library verified)."
else
    echo "Get-library test failed. Response: $LIB_RESPONSE"
    exit 1
fi

# Add Book
echo "Testing add-book endpoint..."
ADD_BOOK_PAYLOAD="{\"username\": \"$TEST_USER\", \"title\": \"The Great Gatsby\", \"author\": \"F. Scott Fitzgerald\"}"
ADD_BOOK_RESPONSE=$(make_request "${API_URL}/add-book" "POST" "$ADD_BOOK_PAYLOAD" 200)
check_json "$ADD_BOOK_RESPONSE"
BOOK_ID=$(echo "$ADD_BOOK_RESPONSE" | jq -r '.book.id')
if [ -z "$BOOK_ID" ] || [ "$BOOK_ID" = "null" ]; then
    echo "Failed to get book ID from response: $ADD_BOOK_RESPONSE"
    exit 1
fi
echo "Add-book test passed. Book ID: $BOOK_ID"

# Verify Book Added
echo "Testing get-library endpoint... (should have one book)"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

BOOK_COUNT=$(echo "$LIB_RESPONSE" | jq '.books."Want to Read" | length')
if [ "$BOOK_COUNT" -eq 1 ]; then
    echo "Get-library test passed (one book verified)."
else
    echo "Get-library test failed. Expected 1 book, got $BOOK_COUNT. Response: $LIB_RESPONSE"
    exit 1
fi

# Update Book Status
echo "Testing update-status endpoint..."
UPDATE_STATUS_PAYLOAD="{\"username\": \"$TEST_USER\", \"status\": \"Reading\"}"
UPDATE_STATUS_RESPONSE=$(make_request "${API_URL}/update-status/$BOOK_ID" "PUT" "$UPDATE_STATUS_PAYLOAD" 200)
check_json "$UPDATE_STATUS_RESPONSE"
echo "Update status test passed."

# Verify Status Updated (with retry)
echo "Testing get-library endpoint... (book should be in 'Reading' status)"
MAX_RETRIES=3
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
    check_json "$LIB_RESPONSE"
    
    READING_COUNT=$(echo "$LIB_RESPONSE" | jq '.books.Reading | length')
    if [ "$READING_COUNT" -eq 1 ]; then
        echo "Status update verified in library."
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Waiting for status update to propagate (attempt $RETRY_COUNT of $MAX_RETRIES)..."
        sleep 1
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Status update verification failed after $MAX_RETRIES attempts. Response: $LIB_RESPONSE"
    exit 1
fi

# 4. Review Management Tests
echo -e "\nTesting review management endpoints..."

# Add Review
echo "Testing add-review endpoint..."
ADD_REVIEW_PAYLOAD="{\"username\": \"$TEST_USER\", \"title\": \"The Great Gatsby\", \"book_id\": $BOOK_ID, \"review\": \"A masterpiece of American literature.\"}"
ADD_REVIEW_RESPONSE=$(make_request "${API_URL}/add-review" "POST" "$ADD_REVIEW_PAYLOAD" 200)
check_json "$ADD_REVIEW_RESPONSE"
echo "Add review test passed."

# Get Reviews
echo "Testing get-reviews endpoint..."
GET_REVIEWS_ENDPOINT="${API_URL}/get-reviews?username=$TEST_USER"
REVIEWS_RESPONSE=$(make_request "$GET_REVIEWS_ENDPOINT" "GET" "" 200)
check_json "$REVIEWS_RESPONSE"

REVIEW_COUNT=$(echo "$REVIEWS_RESPONSE" | jq '.reviews | length')
if [ "$REVIEW_COUNT" -eq 1 ]; then
    echo "Get-reviews test passed (found 1 review)."
else
    echo "Get-reviews test failed. Expected 1 review, got $REVIEW_COUNT. Response: $REVIEWS_RESPONSE"
    exit 1
fi

# Delete Review
echo "Testing delete-review endpoint..."
DELETE_REVIEW_PAYLOAD="{\"username\": \"$TEST_USER\", \"book_id\": $BOOK_ID}"
DELETE_REVIEW_RESPONSE=$(make_request "${API_URL}/delete-review" "DELETE" "$DELETE_REVIEW_PAYLOAD" 200)
check_json "$DELETE_REVIEW_RESPONSE"
echo "Delete review test passed."

# Verify Review Deleted
echo "Testing get-reviews endpoint... (should be empty)"
REVIEWS_RESPONSE=$(make_request "$GET_REVIEWS_ENDPOINT" "GET" "" 404)
check_json "$REVIEWS_RESPONSE"

if echo "$REVIEWS_RESPONSE" | jq -e '.message | contains("not reviewed")' > /dev/null; then
    echo "Review deletion verified."
else
    echo "Review deletion verification failed. Response: $REVIEWS_RESPONSE"
    exit 1
fi

# 5. Cleanup Tests
echo -e "\nRunning cleanup tests..."

# Delete Book
echo "Testing delete-book endpoint..."
DELETE_BOOK_RESPONSE=$(make_request "${API_URL}/delete-book/$BOOK_ID?username=$TEST_USER" "DELETE" "" 200)
check_json "$DELETE_BOOK_RESPONSE"
echo "Delete-book test passed."

# Verify Library Empty
echo "Testing get-library endpoint... (should be empty again)"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

if [ "$(echo "$LIB_RESPONSE" | jq '.books | length')" -eq 0 ] && [ "$(echo "$LIB_RESPONSE" | jq '.favorites | length')" -eq 0 ]; then
    echo "Final library check passed (empty library verified)."
else
    echo "Final library check failed. Response: $LIB_RESPONSE"
    exit 1
fi

# Delete Account
echo "Testing delete-account endpoint..."
DELETE_ACCOUNT_PAYLOAD="{\"username\": \"$TEST_USER\", \"password\": \"$NEW_PASS\"}"
DELETE_ACCOUNT_RESPONSE=$(make_request "${BASE_URL}/delete-account" "DELETE" "$DELETE_ACCOUNT_PAYLOAD" 200)
check_json "$DELETE_ACCOUNT_RESPONSE"
echo "Delete account test passed."

echo -e "\n✅ All smoke tests completed successfully!"
