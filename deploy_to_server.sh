#!/bin/bash
# Скрипт для развёртывания обновлений на сервер
# Использование: ./deploy_to_server.sh

set -e

SERVER="root@178.172.212.221"
SERVER_PATH="/opt/tvoydonor"

echo "========================================="
echo "🚀 РАЗВЁРТЫВАНИЕ НА СЕРВЕР"
echo "========================================="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Шаг 1: Архивация проекта...${NC}"
cd /Users/VadimVthv/Your_donor
tar --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='backups' \
    --exclude='.git' \
    -czf /tmp/tvoydonor-deploy.tar.gz \
    website/ \
    .gitignore

echo -e "${GREEN}✓ Архив создан${NC}"

echo -e "${YELLOW}Шаг 2: Загрузка на сервер...${NC}"
scp /tmp/tvoydonor-deploy.tar.gz ${SERVER}:/tmp/

echo -e "${GREEN}✓ Файлы загружены${NC}"

echo -e "${YELLOW}Шаг 3: Развёртывание на сервере...${NC}"
ssh ${SERVER} << 'REMOTE_COMMANDS'
set -e

cd /opt/tvoydonor

# Создаём backup текущей версии
echo "📦 Создание backup..."
tar -czf backups/before-deploy-$(date +%Y%m%d-%H%M%S).tar.gz website/ || true

# Сохраняем .env файл
echo "💾 Сохранение .env..."
cp website/backend/.env /tmp/.env.backup

# Распаковываем новую версию
echo "📂 Распаковка новых файлов..."
tar -xzf /tmp/tvoydonor-deploy.tar.gz

# Восстанавливаем .env
echo "🔐 Восстановление .env..."
cp /tmp/.env.backup website/backend/.env
chmod 600 website/backend/.env

# Устанавливаем права
echo "🔒 Установка прав доступа..."
chown -R root:root /opt/tvoydonor
chmod 755 /opt/tvoydonor

# Обновляем Python зависимости
echo "📚 Обновление зависимостей..."
cd website/backend
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Перезапускаем сервисы
echo "♻️  Перезапуск сервисов..."
supervisorctl restart all
sleep 2

# Проверяем статус
echo ""
echo "========================================="
echo "📊 СТАТУС СЕРВИСОВ"
echo "========================================="
supervisorctl status

# Проверяем API
echo ""
echo "========================================="
echo "🧪 ПРОВЕРКА API"
echo "========================================="
curl -s http://localhost:5001/api/regions | python3 -m json.tool | head -20 || echo "❌ API не отвечает"

echo ""
echo "========================================="
echo "✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo "🌐 Сайт: https://tvoydonor.by"
echo "📁 Backup: /opt/tvoydonor/backups/"
echo ""

REMOTE_COMMANDS

echo -e "${GREEN}✅ Развёртывание успешно завершено!${NC}"
echo ""
echo "🔍 Проверьте сайт: https://tvoydonor.by"

# Удаляем временный архив
rm /tmp/tvoydonor-deploy.tar.gz
