#!/bin/bash

set -e

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}

echo "🚀 Deploying VivaDental to $ENVIRONMENT environment..."

# Load environment variables
source .env.$ENVIRONMENT

# Pull latest images
echo "📦 Pulling Docker images..."
docker-compose -f docker-compose.$ENVIRONMENT.yml pull

# Backup database
echo "💾 Backing up database..."
./scripts/backup_db.sh $ENVIRONMENT

# Run database migrations
echo "🔄 Running migrations..."
docker-compose -f docker-compose.$ENVIRONMENT.yml run --rm backend \
  alembic upgrade head

# Deploy services
echo "🚀 Deploying services..."
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d --remove-orphans

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Run health checks
echo "🏥 Running health checks..."
curl -f https://${DOMAIN}/api/health || exit 1

# Run smoke tests
echo "🧪 Running smoke tests..."
docker-compose -f docker-compose.$ENVIRONMENT.yml run --rm backend \
  pytest tests/smoke_tests.py -v

# Cleanup old images
echo "🧹 Cleaning up old images..."
docker image prune -f

# Send deployment notification
echo "📢 Sending deployment notification..."
curl -X POST -H "Content-Type: application/json" \
  -d "{\"text\":\"✅ VivaDental deployed to $ENVIRONMENT\nVersion: $VERSION\nTime: $(date)\"}" \
  $SLACK_WEBHOOK_URL

echo "🎉 Deployment completed successfully!"