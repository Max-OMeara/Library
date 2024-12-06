FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/db && \
    chmod +x /app/entrypoint.sh && \
    chmod +x /app/sql/create_db.sh

# Create volume for database persistence
VOLUME ["/app/db"]

EXPOSE 5000

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]