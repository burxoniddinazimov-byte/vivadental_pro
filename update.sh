#!/bin/bash

# Скрипт обновления

echo "Обновление VivaDental..."

# Останавливаем приложение
docker-compose -f docker-compose.prod.yml down

# Получаем последние изменения
git pull origin main

# Пересобираем образы
docker-compose -f docker-compose.prod.yml build

# Запускаем миграции
docker-compose -f docker-compose.prod.yml run --rm backend \
    alembic upgrade head

# Запускаем приложение
docker-compose -f docker-compose.prod.yml up -d

echo "Обновление завершено!"