#!/bin/bash

echo "Running smoke tests..."

export $(cat .env | xargs) # Load environment variables

BASE_URL="http://localhost:5000" # Auth routes use BASE_URL
API_URL="$BASE_URL/api" 

ECHO_JSON=false

while [ "$#" -gt 0 ]; do
  case $1 in
    --echo-json) ECHO_JSON=true ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

# Cleanup function to delete test user if it exists
cleanup_test_user() {
    echo "Cleaning up previous test data..."
    DELETE_PAYLOAD='{"username": "testuser", "password": "testpass"}'
    DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/delete-account" \
        -H "Content-Type: application/json" \
        -d "$DELETE_PAYLOAD")
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Cleanup response: $DELETE_RESPONSE"
    fi
}

# Run cleanup before tests
cleanup_test_user

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

# Test health-check
echo "Testing health-check endpoint..."
HEALTH_ENDPOINT="$API_URL/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_ENDPOINT")
if [ "$RESPONSE" -eq 200 ]; then
  echo "Health-check endpoint is up."
else
  echo "Health-check endpoint failed with code $RESPONSE"
  exit 1
fi

# Test create-account
echo "Testing create-account endpoint..."
CREATE_ACCOUNT_ENDPOINT="$BASE_URL/create-account"
CREATE_PAYLOAD='{ "username": "testuser", "password": "testpass" }'
CREATE_RESPONSE=$(make_request "$CREATE_ACCOUNT_ENDPOINT" "POST" "$CREATE_PAYLOAD" 201)
check_json "$CREATE_RESPONSE"
echo "Account creation test passed."

# Test get-library (should be empty initially)
echo "Testing get-library endpoint... (should be empty)"
GET_LIBRARY_ENDPOINT="$API_URL/get-library?username=testuser"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

if [ "$(echo "$LIB_RESPONSE" | jq '.books | length')" -eq 0 ] && [ "$(echo "$LIB_RESPONSE" | jq '.favorites | length')" -eq 0 ]; then
  echo "Get-library test passed."
else
  echo "Get-library test failed. Response: $LIB_RESPONSE"
  exit 1
fi

# Test add-book
echo "Testing add-book endpoint..."
ADD_BOOK_ENDPOINT="$API_URL/add-book"
ADD_BOOK_PAYLOAD='{ "username": "testuser", "title": "Harry Potter and the Philosophers Stone", "author": "J.K. Rowling" }'
ADD_BOOK_RESPONSE=$(make_request "$ADD_BOOK_ENDPOINT" "POST" "$ADD_BOOK_PAYLOAD" 201)
check_json "$ADD_BOOK_RESPONSE"
echo "Add-book test passed."

# Test get-library (should have one book)
echo "Testing get-library endpoint... (should have one book)"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

if [ "$(echo "$LIB_RESPONSE" | jq '.books."Want to Read" | length')" -eq 1 ] && [ "$(echo "$LIB_RESPONSE" | jq '.favorites | length')" -eq 0 ]; then
  echo "Get-library test passed."
else
  echo "Get-library test failed. Response: $LIB_RESPONSE"
  exit 1
fi

# Test delete-book
echo "Testing delete-book endpoint..."
DELETE_BOOK_ENDPOINT="$API_URL/delete-book/1?username=testuser"
DELETE_RESPONSE=$(make_request "$DELETE_BOOK_ENDPOINT" "DELETE" "" 200)
check_json "$DELETE_RESPONSE"
echo "Delete-book test passed."

# Test get-library (should be empty again)
echo "Testing get-library endpoint... (should be empty again)"
LIB_RESPONSE=$(make_request "$GET_LIBRARY_ENDPOINT" "GET" "" 200)
check_json "$LIB_RESPONSE"

if [ "$(echo "$LIB_RESPONSE" | jq '.books | length')" -eq 0 ] && [ "$(echo "$LIB_RESPONSE" | jq '.favorites | length')" -eq 0 ]; then
  echo "Get-library test passed."
else
  echo "Get-library test failed. Response: $LIB_RESPONSE"
  exit 1
fi

echo "All smoke tests passed."
