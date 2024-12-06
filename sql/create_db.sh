#!/bin/bash
set -e

echo "Creating SQLite database..."

# Create the database directory if it doesn't exist
mkdir -p /app/db

# Create or recreate the database
sqlite3 /app/db/library.db < /app/sql/create_tables.sql

echo "Database created successfully!"