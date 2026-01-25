#!/bin/bash
# БЕЗОПАСНОЕ РАЗВЁРТЫВАНИЕ НА СЕРВЕР С СОХРАНЕНИЕМ .ENV
# Использование: ./deploy_safe.sh

set -e

SERVER="root@178.172.212.221"
SERVER_PATH="/opt/tvoydonor"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

echo "========================================="
echo "🚀 БЕЗОПАСНОЕ РАЗВЁРТЫВАНИЕ"
echo "========================================="

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}📦 Шаг 1: Создание архива...${NC}"
cd /Users/VadimVthv/Your_donor

# Архивируем только нужные файлы
tar --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='backups' \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='website/backend/.env' \
    -czf /tmp/tvoydonor-deploy-${BACKUP_DATE}.tar.gz \
    website/backend/app.py \
    website/backend/telegram_bot.py \
    website/backend/messaging_api.py \
    website/backend/messaging_api_messages.py \
    website/backend/create_database.sql \
    website/backend/requirements.txt \
    website/js/ \
    website/css/ \
    website/pages/ \
    website/index.html \
    website/medcenter_login.html \
    .gitignore

echo -e "${GREEN}✓ Архив создан: /tmp/tvoydonor-deploy-${BACKUP_DATE}.tar.gz${NC}"

echo -e "${YELLOW}📤 Шаг 2: Загрузка на сервер...${NC}"
scp /tmp/tvoydonor-deploy-${BACKUP_DATE}.tar.gz ${SERVER}:/tmp/

echo -e "${GREEN}✓ Файлы загружены${NC}"

echo -e "${YELLOW}🔧 Шаг 3: Развёртывание на сервере...${NC}"
ssh ${SERVER} << REMOTE_COMMANDS
set -e

echo "========================================="
echo "📁 РАЗВЁРТЫВАНИЕ НА СЕРВЕРЕ"
echo "========================================="

cd ${SERVER_PATH}

# 1. Backup текущей версии
echo "📦 Создание backup..."
mkdir -p backups
tar -czf backups/before-deploy-${BACKUP_DATE}.tar.gz website/ 2>/dev/null || true

# 2. КРИТИЧЕСКИ ВАЖНО: Сохранение .env
echo "🔐 Сохранение .env файла..."
if [ -f website/backend/.env ]; then
    cp website/backend/.env /tmp/.env.backup.${BACKUP_DATE}
    echo "✓ .env сохранён в /tmp/.env.backup.${BACKUP_DATE}"
else
    echo "⚠️  .env файл не найден! Будет создан новый."
fi

# 3. Распаковка новых файлов
echo "📂 Распаковка обновлений..."
tar -xzf /tmp/tvoydonor-deploy-${BACKUP_DATE}.tar.gz

# 4. КРИТИЧЕСКИ ВАЖНО: Восстановление .env
echo "🔐 Восстановление .env файла..."
if [ -f /tmp/.env.backup.${BACKUP_DATE} ]; then
    cp /tmp/.env.backup.${BACKUP_DATE} website/backend/.env
    chmod 600 website/backend/.env
    echo "✓ .env восстановлен"
else
    echo "⚠️  Создание нового .env файла..."
    cat > website/backend/.env << 'ENVEOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_donor
DB_USER=donor_user
DB_PASSWORD=u1oFnZALhyfpbtir08nH
SECRET_KEY=bbaa349e397590f4fb8d5dc41d36f523166f0ca6f09ab40ec3e94a58e4506810
MASTER_PASSWORD=doctor2024
TELEGRAM_BOT_TOKEN=8212814214:AAG29mEQN2EWS1wFvKbDqC8nr6SgN3_VeZ8
SUPER_ADMIN_TELEGRAM_USERNAME=vadimvthv
WEBSITE_URL=https://tvoydonor.by
APP_URL=https://tvoydonor.by
FLASK_DEBUG=false
PORT=5001
ENVEOF
    chmod 600 website/backend/.env
    echo "✓ Новый .env создан"
fi

# 5. Установка прав
echo "🔒 Установка прав доступа..."
chown -R root:root ${SERVER_PATH}
chmod 755 ${SERVER_PATH}

# 6. Обновление Python зависимостей
echo "📚 Обновление зависимостей..."
cd website/backend
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 7. Применение миграций БД
echo "🗄️  Применение миграций БД..."
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

# Переименовываем donation_requests в blood_requests если нужно
psql -U donor_user -h localhost your_donor << 'SQL'
-- Проверяем какая таблица существует
DO \$\$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'donation_requests' AND table_type = 'BASE TABLE') THEN
        -- Удаляем VIEW если есть
        DROP VIEW IF EXISTS blood_requests CASCADE;
        -- Переименовываем таблицу
        ALTER TABLE donation_requests RENAME TO blood_requests;
        RAISE NOTICE 'Таблица donation_requests переименована в blood_requests';
    END IF;
END \$\$;

-- Создаём VIEW для обратной совместимости
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

SQL

echo "✓ Миграции применены"

# 8. Перезапуск сервисов
echo "♻️  Перезапуск сервисов..."
supervisorctl restart all
sleep 3

# 9. Проверка статуса
echo ""
echo "========================================="
echo "📊 СТАТУС СЕРВИСОВ"
echo "========================================="
supervisorctl status

# 10. Тест API
echo ""
echo "========================================="
echo "🧪 ТЕСТ API"
echo "========================================="
curl -s http://localhost:5001/api/regions | head -50 || echo "❌ API не отвечает"

echo ""
echo "========================================="
echo "✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo "🌐 Сайт: https://tvoydonor.by"
echo "📁 Backup: ${SERVER_PATH}/backups/before-deploy-${BACKUP_DATE}.tar.gz"
echo "🔐 .env backup: /tmp/.env.backup.${BACKUP_DATE}"
echo ""
echo "Откройте https://tvoydonor.by и проверьте работу!"

REMOTE_COMMANDS

echo ""
echo -e "${GREEN}✅ Развёртывание успешно завершено!${NC}"
echo ""
echo "🔍 Проверьте сайт: https://tvoydonor.by"

# Удаляем временный архив
rm /tmp/tvoydonor-deploy-${BACKUP_DATE}.tar.gz
