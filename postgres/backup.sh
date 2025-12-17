#!/bin/bash

# Конфигурация
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
DATABASE="vivadental_prod"

# Создаем директорию для бэкапов
mkdir -p $BACKUP_DIR/$DATE

# Полный бэкап базы данных
echo "Starting full backup of $DATABASE..."
pg_dump -h localhost -U postgres -F c -b -v -f $BACKUP_DIR/$DATE/full_backup.dump $DATABASE

# Бэкап только схемы
echo "Backing up schema..."
pg_dump -h localhost -U postgres -s -f $BACKUP_DIR/$DATE/schema.sql $DATABASE

# Бэкап только данных (без схемы)
echo "Backing up data..."
pg_dump -h localhost -U postgres -a -f $BACKUP_DIR/$DATE/data.sql $DATABASE

# Бэкап важных таблиц отдельно
TABLES="patients appointments invoices payments"
for TABLE in $TABLES; do
    echo "Backing up table: $TABLE..."
    pg_dump -h localhost -U postgres -t $TABLE -f $BACKUP_DIR/$DATE/${TABLE}_backup.sql $DATABASE
done

# Создаем снимок для Point-in-Time Recovery
echo "Creating base backup for PITR..."
pg_basebackup -h localhost -U postgres -D $BACKUP_DIR/$DATE/pg_basebackup -Ft -z -P

# Архивируем бэкапы
echo "Compressing backups..."
tar -czf $BACKUP_DIR/vivadental_backup_$DATE.tar.gz -C $BACKUP_DIR $DATE

# Удаляем временную директорию
rm -rf $BACKUP_DIR/$DATE

# Очищаем старые бэкапы
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "vivadental_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Проверяем целостность последнего бэкапа
if [ -f $BACKUP_DIR/vivadental_backup_$DATE.tar.gz ]; then
    echo "Verifying backup integrity..."
    tar -tzf $BACKUP_DIR/vivadental_backup_$DATE.tar.gz >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Backup completed successfully: vivadental_backup_$DATE.tar.gz"
        
        # Отправляем уведомление
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"text\":\"✅ Database backup completed: $DATE\"}" \
            ${SLACK_WEBHOOK_URL}
    else
        echo "Backup verification failed!"
        
        # Отправляем уведомление об ошибке
        curl -X POST -H "Content-Type: application/json" \
            -d "{\"text\":\"❌ Database backup failed: $DATE\"}" \
            ${SLACK_WEBHOOK_URL}
    fi
fi

# Синхронизируем с удаленным хранилищем (если настроено)
if [ ! -z "$REMOTE_BACKUP_PATH" ]; then
    echo "Syncing with remote storage..."
    rsync -avz --delete $BACKUP_DIR/ $REMOTE_BACKUP_PATH/
fi