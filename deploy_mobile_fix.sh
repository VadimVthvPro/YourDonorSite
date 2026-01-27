#!/bin/bash
# ===========================================
# ДЕПЛОЙ МОБИЛЬНЫХ ИСПРАВЛЕНИЙ
# Версия: 2.0
# ===========================================

set -e

SERVER="root@178.172.212.221"
SERVER_PATH="/opt/tvoydonor"
PASSWORD="Vadamahjkl1!"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "📱 ДЕПЛОЙ МОБИЛЬНЫХ ИСПРАВЛЕНИЙ"
echo "========================================="

cd /Users/VadimVthv/Your_donor

# Файлы для деплоя
FILES=(
    "website/css/mobile-fix.css"
    "website/index.html"
    "website/pages/donor-dashboard.html"
    "website/pages/medcenter-dashboard.html"
    "website/pages/auth.html"
    "website/js/messenger.js"
)

echo -e "${YELLOW}📦 Шаг 1: Создание архива...${NC}"
tar -czf /tmp/mobile-fix-${BACKUP_DATE}.tar.gz "${FILES[@]}"
echo -e "${GREEN}✓ Архив создан${NC}"

echo -e "${YELLOW}📤 Шаг 2: Загрузка на сервер...${NC}"
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no /tmp/mobile-fix-${BACKUP_DATE}.tar.gz ${SERVER}:/tmp/
echo -e "${GREEN}✓ Файлы загружены${NC}"

echo -e "${YELLOW}🔧 Шаг 3: Развёртывание...${NC}"
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${SERVER} << REMOTE
set -e

echo "📦 Создание бэкапа..."
mkdir -p ${SERVER_PATH}/backups

# Бэкап текущих файлов
tar -czf ${SERVER_PATH}/backups/before-mobile-fix-${BACKUP_DATE}.tar.gz \
    ${SERVER_PATH}/website/index.html \
    ${SERVER_PATH}/website/pages/donor-dashboard.html \
    ${SERVER_PATH}/website/pages/medcenter-dashboard.html \
    ${SERVER_PATH}/website/pages/auth.html \
    ${SERVER_PATH}/website/js/messenger.js 2>/dev/null || true
echo "✓ Бэкап создан"

echo "📂 Распаковка новых файлов..."
tar -xzf /tmp/mobile-fix-${BACKUP_DATE}.tar.gz -C ${SERVER_PATH}
echo "✓ Файлы распакованы"

echo "🔒 Установка прав..."
chown -R root:root ${SERVER_PATH}/website/css/mobile-fix.css
chown -R root:root ${SERVER_PATH}/website/index.html
chown -R root:root ${SERVER_PATH}/website/pages/*.html
chown -R root:root ${SERVER_PATH}/website/js/messenger.js
chmod 644 ${SERVER_PATH}/website/css/mobile-fix.css
chmod 644 ${SERVER_PATH}/website/index.html
chmod 644 ${SERVER_PATH}/website/pages/*.html
chmod 644 ${SERVER_PATH}/website/js/messenger.js
echo "✓ Права установлены"

echo "🔄 Перезагрузка nginx..."
nginx -s reload
echo "✓ Nginx перезагружен"

# Очистка
rm -f /tmp/mobile-fix-${BACKUP_DATE}.tar.gz

echo ""
echo "========================================="
echo "✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЁН!"
echo "========================================="
echo ""
echo "📱 Изменения:"
echo "  - mobile-fix.css - новый файл с мобильными исправлениями"
echo "  - HTML файлы - подключён mobile-fix.css"
echo "  - messenger.js - исправлена логика мобильного вида"
echo ""
echo "🧪 Проверьте на телефоне:"
echo "  1. Главная страница"
echo "  2. Авторизация"
echo "  3. Личный кабинет донора"
echo "  4. Меню медцентра"
echo "  5. Мессенджер (должен быть вертикальным)"
echo "  6. Поворот телефона (должен скроллиться)"
REMOTE

# Очистка локально
rm -f /tmp/mobile-fix-${BACKUP_DATE}.tar.gz

echo ""
echo -e "${GREEN}✅ Деплой завершён успешно!${NC}"
echo ""
echo "🔗 Проверь на телефоне: https://tvoydonor.by"
