#!/bin/bash

SERVICE_NAME="scout-app"

echo "🛡️  Deploying Scout..."

# 1. Pull latest code
echo "⬇️  Pulling latest code..."
git pull origin master

# Validate compose file
if [ ! -f "docker-compose.yml" ]; then
  echo "❌ docker-compose.yml missing. Create it first."
  exit 1
fi

# 2. Build with --pull to refresh base images (e.g., node:20-alpine)
echo "🏗️  Building image (pulling base images)..."
docker-compose build --pull $SERVICE_NAME

# 3. Restart service
echo "🔄 Restarting $SERVICE_NAME (aggressive cleanup)..."
# Manual cleanup by label to find all "scout" containers, even orphaned ones
docker rm -f $(docker ps -a -q --filter label=com.docker.compose.project=scout) || true
docker-compose up -d $SERVICE_NAME

# 4. Health check
sleep 10
if docker-compose ps $SERVICE_NAME | grep -q "Up"; then
  echo "✅ $SERVICE_NAME healthy."
else
  echo "⚠️  Check logs: docker-compose logs $SERVICE_NAME"
fi

# 5. Cleanup
echo "🧹 Pruning..."
docker image prune -f

echo "✅ Deploy complete!"
