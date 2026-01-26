#!/bin/bash

# ============================================
# ПРОСТОЙ СКРИПТ: Исправление мессенджера
# ============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER_IP="178.172.212.221"
SERVER_USER="root"
SERVER_PATH="/opt/tvoydonor/website"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔧 ИСПРАВЛЕНИЕ МЕССЕНДЖЕРА          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📤 ШАГ 1/5: Загрузка messenger.js...${NC}"
scp website/js/messenger.js ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/js/
echo -e "${GREEN}✅ messenger.js загружен${NC}"
echo ""

echo -e "${YELLOW}📤 ШАГ 2/5: Загрузка SQL миграции...${NC}"
scp migrate_chat_messages.sql ${SERVER_USER}@${SERVER_IP}:/tmp/
echo -e "${GREEN}✅ SQL миграция загружена${NC}"
echo ""

echo -e "${YELLOW}🗄️  ШАГ 3/5: Применение миграции БД...${NC}"
echo -e "${BLUE}Скопируйте и выполните на сервере:${NC}"
echo ""
echo "sudo -u postgres psql -d your_donor -f /tmp/migrate_chat_messages.sql"
echo ""
echo -e "${YELLOW}После выполнения нажмите Enter...${NC}"
read

echo -e "${YELLOW}🔄 ШАГ 4/5: Обновление версии...${NC}"
TIMESTAMP=$(date +%s)
ssh ${SERVER_USER}@${SERVER_IP} << EOF
    cd ${SERVER_PATH}
    sed -i "s/window.VERSION = .*/window.VERSION = '${TIMESTAMP}';/" js/config.js
    echo "✅ Версия обновлена: ${TIMESTAMP}"
EOF
echo ""

echo -e "${YELLOW}🔄 ШАГ 5/5: Перезапуск сервисов...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
    nginx -t && systemctl reload nginx
    supervisorctl restart tvoydonor-api
    echo "✅ Сервисы перезапущены"
EOF
echo ""

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ ГОТОВО!                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🧪 ТЕСТИРОВАНИЕ:${NC}"
echo "  1. Откройте https://tvoydonor.by"
echo "  2. Очистите кэш: Ctrl+Shift+R"
echo "  3. Залогиньтесь как медцентр"
echo "  4. Подтвердите донора"
echo "  5. Откройте мессенджер"
echo "  6. ✅ Клишированное сообщение должно быть СПРАВА"
echo ""
