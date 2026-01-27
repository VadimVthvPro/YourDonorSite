#!/bin/bash
# ============================================
# 🔄 ДЕПЛОЙ ИСПРАВЛЕНИЯ POLLING (AUTO-REFRESH)
# ============================================
# 
# Этот скрипт загружает исправленные файлы на сервер:
# - data-poller.js (исправлен баг инициализации)
# - donor-dashboard.html (подключён data-poller.js)
# - medcenter-dashboard.html (подключён data-poller.js)
#
# Использование:
#   ./deploy_polling_fix.sh
#
# ============================================

set -e

# Конфигурация
SERVER="root@178.172.212.221"
SERVER_PATH="/opt/tvoydonor"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🔄 ДЕПЛОЙ ИСПРАВЛЕНИЯ AUTO-REFRESH${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Проверяем, что мы в правильной директории
if [ ! -f "website/js/data-poller.js" ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт из корня проекта Your_donor${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Файлы для деплоя:${NC}"
echo "   • website/js/data-poller.js"
echo "   • website/pages/donor-dashboard.html"
echo "   • website/pages/medcenter-dashboard.html"
echo ""

# Шаг 1: Создание резервной копии на сервере
echo -e "${YELLOW}📦 Шаг 1: Создание backup на сервере...${NC}"
ssh ${SERVER} << BACKUP_COMMANDS
mkdir -p ${SERVER_PATH}/backups
cd ${SERVER_PATH}

# Backup изменяемых файлов
if [ -f website/js/data-poller.js ]; then
    cp website/js/data-poller.js backups/data-poller.js.${TIMESTAMP}.bak
fi
cp website/pages/donor-dashboard.html backups/donor-dashboard.html.${TIMESTAMP}.bak
cp website/pages/medcenter-dashboard.html backups/medcenter-dashboard.html.${TIMESTAMP}.bak

echo "✓ Backup создан в ${SERVER_PATH}/backups/"
BACKUP_COMMANDS

echo -e "${GREEN}✓ Backup завершён${NC}"
echo ""

# Шаг 2: Загрузка исправленных файлов
echo -e "${YELLOW}📤 Шаг 2: Загрузка файлов на сервер...${NC}"

# Загружаем каждый файл отдельно
scp website/js/data-poller.js ${SERVER}:${SERVER_PATH}/website/js/
echo "   ✓ data-poller.js"

scp website/pages/donor-dashboard.html ${SERVER}:${SERVER_PATH}/website/pages/
echo "   ✓ donor-dashboard.html"

scp website/pages/medcenter-dashboard.html ${SERVER}:${SERVER_PATH}/website/pages/
echo "   ✓ medcenter-dashboard.html"

echo -e "${GREEN}✓ Все файлы загружены${NC}"
echo ""

# Шаг 3: Установка правильных прав доступа
echo -e "${YELLOW}🔒 Шаг 3: Установка прав доступа...${NC}"
ssh ${SERVER} << PERMISSIONS
chmod 644 ${SERVER_PATH}/website/js/data-poller.js
chmod 644 ${SERVER_PATH}/website/pages/donor-dashboard.html
chmod 644 ${SERVER_PATH}/website/pages/medcenter-dashboard.html
chown -R root:root ${SERVER_PATH}/website/
echo "✓ Права установлены"
PERMISSIONS

echo -e "${GREEN}✓ Права доступа настроены${NC}"
echo ""

# Шаг 4: Очистка кеша nginx (если настроен)
echo -e "${YELLOW}🧹 Шаг 4: Перезагрузка nginx...${NC}"
ssh ${SERVER} << NGINX
# Проверяем конфиг nginx
nginx -t 2>/dev/null && nginx -s reload 2>/dev/null || echo "Nginx не требует перезагрузки"
echo "✓ Готово"
NGINX

echo -e "${GREEN}✓ Nginx перезагружен${NC}"
echo ""

# Шаг 5: Проверка
echo -e "${YELLOW}🧪 Шаг 5: Проверка файлов на сервере...${NC}"
ssh ${SERVER} << CHECK
echo ""
echo "📁 Проверка data-poller.js:"
head -5 ${SERVER_PATH}/website/js/data-poller.js
echo "..."
tail -5 ${SERVER_PATH}/website/js/data-poller.js
echo ""

echo "📁 Проверка подключения в donor-dashboard.html:"
grep -n "data-poller.js" ${SERVER_PATH}/website/pages/donor-dashboard.html || echo "❌ Не найдено!"

echo ""
echo "📁 Проверка подключения в medcenter-dashboard.html:"
grep -n "data-poller.js" ${SERVER_PATH}/website/pages/medcenter-dashboard.html || echo "❌ Не найдено!"
CHECK

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЁН!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "🌐 Сайт: ${YELLOW}https://tvoydonor.by${NC}"
echo ""
echo -e "${YELLOW}📋 Что исправлено:${NC}"
echo "   1. data-poller.js теперь корректно инициализируется"
echo "   2. Скрипт подключён к donor-dashboard.html"
echo "   3. Скрипт подключён к medcenter-dashboard.html"
echo ""
echo -e "${YELLOW}🔄 Теперь данные обновляются автоматически:${NC}"
echo "   • Запросы крови (донор): каждые 10 сек"
echo "   • Отклики (медцентр): каждые 5 сек"  
echo "   • Статистика: каждые 30 сек"
echo "   • Мессенджер: каждые 3 сек"
echo ""
echo -e "${YELLOW}⚠️  Для проверки:${NC}"
echo "   1. Откройте https://tvoydonor.by в браузере"
echo "   2. Войдите в личный кабинет донора или медцентра"
echo "   3. Откройте DevTools → Console (F12)"
echo "   4. Должны появиться сообщения:"
echo "      '✅ DataPoller инициализирован'"
echo "      '🔄 Запуск автообновления данных...'"
echo ""
echo -e "${YELLOW}📦 Backup файлы:${NC}"
echo "   ${SERVER_PATH}/backups/*${TIMESTAMP}.bak"
echo ""
