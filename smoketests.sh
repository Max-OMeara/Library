#!/bin/bash

echo "Running smoke tests..."

export $(cat .env | xargs) # Load environment variables

BASE_URL="http://localhost:5000/api"

ECHO_JSON=false

while [ "$#" -gt 0 ]; do
  case $1 in
    --echo-json) ECHO_JSON=true ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

# Test if the server responds
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health-check")
if [ "$RESPONSE" -eq 200 ]; then
  echo "Health-check endpoint is up."
else
  echo "Health-check endpoint failed with code $RESPONSE"
  exit 1
fi

# Test create-account
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/create-account" \
  -H "Content-Type: application/json" \
  -d '{ "username": "testuser", "password": "testpass" }' \
  -w "%{http_code}")
if [ "$CREATE_RESPONSE" -eq 201 ]; then
  echo "Account creation test passed."
else
  echo "Account creation test failed with code $CREATE_RESPONSE"
  exit 1
fi

# Test get-my-library (should be empty initially)
LIB_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/get-my-library")
if [ "$LIB_RESPONSE" -eq 200 ]; then
  echo "Get-my-library test passed."
else
  echo "Get-my-library test failed with code $LIB_RESPONSE"
  exit 1
fi

# Test login
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{ "username": "testuser", "password": "testpass" }' \
  -w "%{http_code}")

if [ "$LOGIN_RESPONSE" -eq 200 ]; then
  echo "Login test passed."
else
  echo "Login test failed with code $LOGIN_RESPONSE"
  exit 1
fi

# Test add-to-library
ADD_RESPONSE=$(curl -s -X POST "$BASE_URL/add-to-library" \
  -H "Content-Type: application/json" \
  -d '{ "title": "testtitle", "author": "testauthor" }' \
  -w "%{http_code}")

if [ "$ADD_RESPONSE" -eq 201 ]; then
  echo "Add-to-library test passed."
else
  echo "Add-to-library test failed with code $ADD_RESPONSE"
  exit 1
fi

# Test get-my-library (should have one book)
LIB_RESPONSE=$(curl -s "$BASE_URL/get-my-library")
if [ "$ECHO_JSON" = true ]; then
  echo "Get-my-library response: $LIB_RESPONSE"
fi

if [ "$(echo "$LIB_RESPONSE" | jq '. | length')" -eq 1 ]; then
  echo "Get-my-library test passed."
else
  echo "Get-my-library test failed."
  exit 1
fi

# Test remove-from-library
REMOVE_RESPONSE=$(curl -s -X POST "$BASE_URL/remove-from-library" \
  -H "Content-Type: application/json" \
  -d '{ "title": "testtitle", "author": "testauthor" }' \
  -w "%{http_code}")

if [ "$REMOVE_RESPONSE" -eq 200 ]; then
  echo "Remove-from-library test passed."
else
  echo "Remove-from-library test failed with code $REMOVE_RESPONSE"
  exit 1
fi

# Test get-my-library (should be empty again)
LIB_RESPONSE=$(curl -s "$BASE_URL/get-my-library")
if [ "$ECHO_JSON" = true ]; then
  echo "Get-my-library response: $LIB_RESPONSE"
fi

if [ "$(echo "$LIB_RESPONSE" | jq '. | length')" -eq 0 ]; then
  echo "Get-my-library test passed."
else
  echo "Get-my-library test failed."
  exit 1
fi


echo "All smoke tests passed."