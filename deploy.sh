#!/bin/bash

# Define the service name from docker-compose.yml
SERVICE_NAME="scout-app"

echo "🛡️  Deploying Scout..."

# 1. Pull the latest changes from git
echo "⬇️  Pulling latest code..."
git pull origin master

# 2. Build the new image (in case requirements changed)
echo "🏗️  Building Docker image..."
docker-compose build $SERVICE_NAME

# 3. Restart ONLY the Scout service
# This ensures other containers on the server are untouched
echo "🔄 Restarting Service: $SERVICE_NAME..."
docker-compose up -d --no-deps $SERVICE_NAME

# 4. Optional: Prune old images to save space
echo "🧹 Pruning old images..."
docker image prune -f

echo "✅ Scout Deployed Successfully!"
