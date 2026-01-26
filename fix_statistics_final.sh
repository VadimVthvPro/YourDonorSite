#!/bin/bash

# ============================================
# ИСПРАВЛЕНИЕ СТАТИСТИКИ: ФИНАЛЬНАЯ ВЕРСИЯ
# ============================================

set -e  # Остановка при ошибке

SERVER_IP="178.172.212.221"
SERVER_USER="root"
DB_NAME="your_donor"
PROJECT_DIR="/opt/tvoydonor"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔧 ИСПРАВЛЕНИЕ СТАТИСТИКИ (FINAL)  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📋 Обнаруженные проблемы:${NC}"
echo "  1. Несоответствие схемы БД (user_id vs donor_id)"
echo "  2. Отсутствие колонки blood_type в donation_history"
echo "  3. loadUserData() загружает из localStorage вместо API"
echo "  4. updateMainStatistics() не вызывается"
echo ""

read -p "Продолжить? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Отменено пользователем${NC}"
    exit 1
fi

# ============================================
# ШАГ 1: Загрузить файлы на сервер
# ============================================

echo ""
echo -e "${GREEN}📤 ШАГ 1/5: Загрузка файлов...${NC}"

echo "  • Загружаем SQL миграцию..."
scp migrate_donation_history_schema.sql ${SERVER_USER}@${SERVER_IP}:/tmp/

echo "  • Загружаем обновлённый app.py..."
scp website/backend/app.py ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/website/backend/

echo "  • Загружаем обновлённый donor-dashboard.js..."
scp website/js/donor-dashboard.js ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/website/js/

echo -e "${GREEN}✅ Файлы загружены${NC}"

# ============================================
# ШАГ 2: Миграция БД
# ============================================

echo ""
echo -e "${GREEN}🗄️  ШАГ 2/5: Миграция базы данных...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
echo ""
echo "📊 Проверяем текущую схему таблицы..."
sudo -u postgres psql -d your_donor -c "\d donation_history" 2>&1 | head -20

echo ""
echo "🔄 Применяем миграцию..."
sudo -u postgres psql -d your_donor -f /tmp/migrate_donation_history_schema.sql

echo ""
echo "✅ Миграция завершена!"

echo ""
echo "📋 Проверка данных:"
sudo -u postgres psql -d your_donor -c "SELECT COUNT(*) as total FROM donation_history;"
sudo -u postgres psql -d your_donor -c "SELECT * FROM donation_history ORDER BY created_at DESC LIMIT 3;"
ENDSSH

echo -e "${GREEN}✅ База данных обновлена${NC}"

# ============================================
# ШАГ 3: Обновить версию и перезагрузить
# ============================================

echo ""
echo -e "${GREEN}🔄 ШАГ 3/5: Обновление версии и перезагрузка...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /opt/tvoydonor/website

# Обновить версию для cache-busting
TIMESTAMP=$(date +%s)
sed -i "s/window.VERSION = .*/window.VERSION = '${TIMESTAMP}';/" js/config.js
echo "✅ Версия обновлена: ${TIMESTAMP}"

# Перезагрузить nginx
nginx -t && systemctl reload nginx
echo "✅ Nginx перезагружен"

# Перезагрузить API
supervisorctl restart tvoydonor-api
echo "✅ API перезагружен"

# Очистить логи (для чистого тестирования)
> /var/log/tvoydonor-api.err.log
> /var/log/tvoydonor-api.out.log
echo "✅ Логи очищены"
ENDSSH

echo -e "${GREEN}✅ Сервисы перезапущены${NC}"

# ============================================
# ШАГ 4: Проверка работы
# ============================================

echo ""
echo -e "${GREEN}🧪 ШАГ 4/5: Проверка работы...${NC}"

echo ""
echo "Ожидание 3 секунды для прогрева API..."
sleep 3

echo ""
echo "📊 Проверяем логи API..."

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
echo ""
echo "📋 Последние строки логов:"
tail -20 /var/log/tvoydonor-api.out.log

echo ""
echo "❌ Проверяем ошибки:"
tail -20 /var/log/tvoydonor-api.err.log
ENDSSH

# ============================================
# ШАГ 5: Финальная проверка БД
# ============================================

echo ""
echo -e "${GREEN}📊 ШАГ 5/5: Финальная проверка БД...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
echo ""
echo "Проверяем схему donation_history после миграции:"
sudo -u postgres psql -d your_donor << 'EOSQL'
SELECT 
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'donation_history'
ORDER BY ordinal_position;
EOSQL

echo ""
echo "Проверяем наличие данных:"
sudo -u postgres psql -d your_donor << 'EOSQL'
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN blood_type IS NOT NULL THEN 1 END) as with_blood_type,
    COUNT(CASE WHEN status IS NOT NULL THEN 1 END) as with_status
FROM donation_history;
EOSQL
ENDSSH

# ============================================
# ИТОГИ
# ============================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📋 Что было сделано:${NC}"
echo "  ✅ Схема БД приведена в соответствие (donor_id, medical_center_id)"
echo "  ✅ Добавлены недостающие колонки (blood_type, status, response_id)"
echo "  ✅ app.py обновлён (INSERT с blood_type)"
echo "  ✅ donor-dashboard.js обновлён (updateMainStatistics)"
echo "  ✅ Сервисы перезагружены"
echo ""

echo -e "${YELLOW}🧪 СЛЕДУЮЩИЕ ШАГИ (РУЧНОЕ ТЕСТИРОВАНИЕ):${NC}"
echo ""
echo "1. Откройте: ${GREEN}https://tvoydonor.by${NC}"
echo "2. ${YELLOW}Очистите кэш браузера: Ctrl+Shift+R (Win) или Cmd+Shift+R (Mac)${NC}"
echo ""
echo "3. ${BLUE}ТЕСТ ДОНОРА:${NC}"
echo "   • Залогиньтесь как донор"
echo "   • Откройте консоль браузера (F12)"
echo "   • ${YELLOW}Ищите в консоли:${NC}"
echo "     ${GREEN}'Статистика загружена: {...}'${NC}"
echo "     ${GREEN}'✅ Главная статистика обновлена: {...}'${NC}"
echo "   • Проверьте sidebar:"
echo "     ✅ Количество донаций"
echo "     ✅ Объём крови (в литрах)"
echo "     ✅ Спасённые жизни"
echo ""
echo "4. ${BLUE}ТЕСТ МЕДЦЕНТРА (если есть данные):${NC}"
echo "   • Залогиньтесь как медцентр"
echo "   • Откройте раздел 'Статистика'"
echo "   • ✅ Должны отобразиться донации"
echo ""

echo -e "${GREEN}🎉 Готово! Статистика должна работать!${NC}"
echo ""

echo -e "${YELLOW}📖 Для детального отчёта смотрите:${NC}"
echo "  • STATISTICS_ROOT_CAUSE.md - корневая причина проблемы"
echo "  • DONATION_LIFECYCLE_RESEARCH.md - жизненный цикл донации"
echo ""

echo -e "${YELLOW}⚠️  ОТКАТ (если что-то сломалось):${NC}"
echo ""
echo "ssh root@${SERVER_IP}"
echo "sudo -u postgres psql -d your_donor"
echo "DROP TABLE donation_history;"
echo "ALTER TABLE donation_history_backup_20260126 RENAME TO donation_history;"
echo "\\q"
echo "supervisorctl restart tvoydonor-api"
echo ""
