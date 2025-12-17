#!/bin/bash

set -e

ENVIRONMENT=${1:-production}
BACKUP_DIR="/backups/$ENVIRONMENT"
DATE=$(date +%Y%m%d_%H%M%S)

echo "💾 Starting database backup for $ENVIRONMENT..."

# Load environment variables
source .env.$ENVIRONMENT

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup PostgreSQL
echo "📦 Backing up PostgreSQL..."
docker-compose -f docker-compose.$ENVIRONMENT.yml exec -T postgres \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/$DATE/database.sql

# Backup Redis (если нужно)
echo "🔴 Backing up Redis..."
docker-compose -f docker-compose.$ENVIRONMENT.yml exec -T redis \
  redis-cli SAVE
docker-compose -f docker-compose.$ENVIRONMENT.yml cp redis:/data/dump.rdb $BACKUP_DIR/$DATE/redis.rdb

# Backup media files
echo "📁 Backing up media files..."
tar -czf $BACKUP_DIR/$DATE/media.tar.gz -C ./backend/media .

# Create backup archive
echo "📦 Creating backup archive..."
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz -C $BACKUP_DIR $DATE

# Upload to remote storage (если настроено)
if [ ! -z "$REMOTE_BACKUP_PATH" ]; then
    echo "☁️ Uploading to remote storage..."
    rclone copy $BACKUP_DIR/backup_$DATE.tar.gz $REMOTE_BACKUP_PATH/$ENVIRONMENT/
fi

# Cleanup old backups (keep 30 days)
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete
rm -rf $BACKUP_DIR/$DATE

echo "✅ Backup completed: backup_$DATE.tar.gz"