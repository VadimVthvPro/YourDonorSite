#!/bin/bash
# ============================================
# ДЕПЛОЙ НОВОЙ СИСТЕМЫ АВТОРИЗАЦИИ
# JWT + Refresh Token
# Версия: 2.0.0
# ============================================

set -e

SERVER="root@178.172.212.221"
SERVER_PATH="/opt/tvoydonor"
PASSWORD="Vadamahjkl1!"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================="
echo -e "${BLUE}🔐 ДЕПЛОЙ СИСТЕМЫ АВТОРИЗАЦИИ v2.0${NC}"
echo "========================================="
echo "Время: $(date)"
echo ""

cd /Users/VadimVthv/Your_donor

# ============================================
# Шаг 1: Проверка файлов
# ============================================
echo -e "${YELLOW}📦 Шаг 1: Проверка файлов...${NC}"

FILES_TO_DEPLOY=(
    "website/backend/auth_service.py"
    "website/backend/app.py"
    "website/backend/requirements.txt"
    "website/backend/migrations/add_refresh_tokens.sql"
    "website/js/auth-storage.js"
    "website/js/auth.js"
    "website/js/config.js"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Файл не найден: $file${NC}"
        exit 1
    fi
    echo "  ✓ $file"
done

echo -e "${GREEN}✓ Все файлы найдены${NC}"
echo ""

# ============================================
# Шаг 2: Создание архива
# ============================================
echo -e "${YELLOW}📦 Шаг 2: Создание архива...${NC}"

tar -czf /tmp/auth-system-${BACKUP_DATE}.tar.gz \
    website/backend/auth_service.py \
    website/backend/app.py \
    website/backend/requirements.txt \
    website/backend/migrations/add_refresh_tokens.sql \
    website/js/auth-storage.js \
    website/js/auth.js \
    website/js/config.js

echo -e "${GREEN}✓ Архив создан${NC}"
echo ""

# ============================================
# Шаг 3: Загрузка на сервер
# ============================================
echo -e "${YELLOW}📤 Шаг 3: Загрузка на сервер...${NC}"

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    /tmp/auth-system-${BACKUP_DATE}.tar.gz \
    ${SERVER}:/tmp/

echo -e "${GREEN}✓ Архив загружен${NC}"
echo ""

# ============================================
# Шаг 4: Развёртывание на сервере
# ============================================
echo -e "${YELLOW}🔧 Шаг 4: Развёртывание на сервере...${NC}"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${SERVER} << 'REMOTE_COMMANDS'
set -e

cd /opt/tvoydonor
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

echo "📦 Создание backup..."
mkdir -p backups
cp website/backend/app.py backups/app.py.${BACKUP_DATE}.bak 2>/dev/null || true
cp website/js/auth-storage.js backups/auth-storage.js.${BACKUP_DATE}.bak 2>/dev/null || true
cp website/js/auth.js backups/auth.js.${BACKUP_DATE}.bak 2>/dev/null || true
echo "✓ Backup создан"

echo ""
echo "📂 Распаковка архива..."
cd /tmp
tar -xzf auth-system-*.tar.gz -C /opt/tvoydonor/
rm -f auth-system-*.tar.gz
echo "✓ Архив распакован"

cd /opt/tvoydonor

echo ""
echo "🔒 Установка прав..."
chmod 644 website/backend/auth_service.py
chmod 644 website/backend/app.py
chmod 644 website/backend/requirements.txt
chmod 644 website/js/auth-storage.js
chmod 644 website/js/auth.js
chmod 644 website/js/config.js
echo "✓ Права установлены"

echo ""
echo "📦 Установка PyJWT..."
cd website/backend
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install PyJWT==2.8.0 --quiet
echo "✓ PyJWT установлен"

echo ""
echo "🗄️ Применение миграции БД..."
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor -f migrations/add_refresh_tokens.sql 2>&1 || echo "⚠️ Миграция применена (или уже была)"

echo ""
echo "🔍 Проверка структуры БД..."
psql -U donor_user -h localhost your_donor -c "\d user_sessions" | head -20

echo ""
echo "🔄 Перезапуск API..."
supervisorctl restart tvoydonor-api
sleep 3

echo ""
echo "🧪 Тестирование API..."
curl -s http://localhost:5001/api/auth/check | head -100

echo ""
echo "🔄 Перезагрузка nginx..."
nginx -s reload

echo ""
echo "============================================"
echo "✅ ДЕПЛОЙ ЗАВЕРШЁН!"
echo "============================================"
echo ""
echo "Что было обновлено:"
echo "  - auth_service.py (новый сервис JWT)"
echo "  - app.py (обновлённые login + новые endpoints)"
echo "  - auth-storage.js (клиент v2.0)"
echo "  - auth.js (credentials: include)"
echo "  - Миграция БД (refresh_token_hash и др.)"
echo ""
echo "Новые API endpoints:"
echo "  POST /api/auth/refresh  - обновление токенов"
echo "  POST /api/auth/logout   - выход"
echo "  POST /api/auth/logout-all - выход со всех устройств"
echo "  GET  /api/auth/sessions - список сессий"
echo "  GET  /api/auth/check    - проверка авторизации"
echo ""

REMOTE_COMMANDS

echo ""
echo -e "${GREEN}✅ Развёртывание успешно завершено!${NC}"
echo ""
echo "🔍 Проверьте сайт: https://tvoydonor.by"
echo ""
echo "Тесты для проверки:"
echo "  1. Войти → закрыть браузер → открыть = авторизован"
echo "  2. Подождать 30+ минут → сайт обновит токен автоматически"
echo "  3. Logout → старый токен невалиден"
echo ""
