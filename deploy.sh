#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен"
        exit 1
    fi
    
    print_info "Docker и Docker Compose проверены"
}

# Создание .env файла
create_env() {
    if [ ! -f .env ]; then
        print_warning ".env файл не найден, создаю шаблон..."
        
        cat > .env << EOF
# База данных
DB_USER=vivadental
DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
DB_NAME=vivadental_db

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Backend
SECRET_KEY=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)
ENVIRONMENT=production
LOG_LEVEL=info

# CORS
CORS_ORIGINS=http://localhost:80,http://localhost:3000

# Email (опционально)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-password

# Платежная система (опционально)
# YOOKASSA_SHOP_ID=your_shop_id
# YOOKASSA_SECRET_KEY=your_secret_key
EOF
        
        print_info ".env файл создан"
    else
        print_info ".env файл уже существует"
    fi
}

# Сборка образов
build_images() {
    print_info "Сборка Docker образов..."
    
    docker-compose -f docker-compose.prod.yml build
    
    if [ $? -eq 0 ]; then
        print_info "Образы успешно собраны"
    else
        print_error "Ошибка при сборке образов"
        exit 1
    fi
}

# Запуск миграций
run_migrations() {
    print_info "Запуск миграций базы данных..."
    
    docker-compose -f docker-compose.prod.yml run --rm backend \
        alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_info "Миграции успешно выполнены"
    else
        print_error "Ошибка при выполнении миграций"
        exit 1
    fi
}

# Создание суперпользователя
create_superuser() {
    print_info "Создание суперпользователя..."
    
    read -p "Email администратора: " admin_email
    read -sp "Пароль администратора: " admin_password
    echo
    
    docker-compose -f docker-compose.prod.yml run --rm backend \
        python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
try:
    if not db.query(User).filter(User.email == '${admin_email}').first():
        user = User(
            email='${admin_email}',
            hashed_password=get_password_hash('${admin_password}'),
            full_name='Администратор',
            role='admin',
            is_active=True
        )
        db.add(user)
        db.commit()
        print('Суперпользователь создан')
    else:
        print('Пользователь уже существует')
except Exception as e:
    print(f'Ошибка: {e}')
finally:
    db.close()
    "
}

# Запуск приложения
start_application() {
    print_info "Запуск приложения..."
    
    docker-compose -f docker-compose.prod.yml up -d
    
    if [ $? -eq 0 ]; then
        print_info "Приложение успешно запущено"
        
        # Показываем статус
        sleep 5
        docker-compose -f docker-compose.prod.yml ps
    else
        print_error "Ошибка при запуске приложения"
        exit 1
    fi
}

# Проверка здоровья
check_health() {
    print_info "Проверка здоровья сервисов..."
    
    for service in backend frontend postgres redis; do
        if docker-compose -f docker-compose.prod.yml ps $service | grep -q "Up"; then
            print_info "$service: ✅"
        else
            print_error "$service: ❌"
        fi
    done
}

# Основной скрипт
main() {
    print_info "=== Начало деплоя VivaDental ==="
    
    # Проверка зависимостей
    check_docker
    
    # Создание .env
    create_env
    
    # Сборка образов
    build_images
    
    # Запуск миграций
    run_migrations
    
    # Создание суперпользователя
    create_superuser
    
    # Запуск приложения
    start_application
    
    # Проверка здоровья
    check_health
    
    print_info "=== Деплой завершен ==="
    print_info "Приложение доступно по адресу: http://localhost"
    print_info "Для просмотра логов: docker-compose -f docker-compose.prod.yml logs -f"
}

# Запуск
main "$@"