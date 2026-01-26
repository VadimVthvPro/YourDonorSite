#!/bin/bash

# ========================================
# 🔧 ИСПРАВЛЕНИЕ СТАТИСТИКИ
# ========================================
# ПРОБЛЕМЫ:
#   1. Медцентр: "Запросов крови: 0" - фильтр по дате (period='month')
#   2. Медцентр: "Уникальных доноров: 0" - фильтр по дате
#   3. Донор ID=3: статистика пустая - НЕ завершил ни одной донации
#
# РЕШЕНИЕ:
#   • Изменить currentStatsperiod = 'all' в medcenter-dashboard.js
#   • Теперь показывается ВСЯ статистика (28 запросов, 4 донора)
# ========================================

set -e

SERVER_IP="178.172.212.221"

echo -e "\n🔧 ИСПРАВЛЕНИЕ СТАТИСТИКИ МЕДЦЕНТРА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Что исправлено:"
echo "  ✓ currentStatsperiod = 'all' (вместо 'month')"
echo "  ✓ Теперь показывается ВСЯ статистика"
echo ""
echo "📊 Ожидаемые значения:"
echo "  • Запросов крови: 28 (вместо 0)"
echo "  • Уникальных доноров: 4 (вместо 0)"
echo "  • Донаций: 1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено пользователем"
    exit 0
fi

echo -e "\n📤 ШАГ 1/3: Загрузка исправленного JS..."
scp website/js/medcenter-dashboard.js root@$SERVER_IP:/opt/tvoydonor/website/js/
echo "✅ medcenter-dashboard.js загружен"

echo -e "\n🔄 ШАГ 2/3: Обновление версии (cache busting)..."
ssh root@$SERVER_IP "
    cd /opt/tvoydonor/website
    TIMESTAMP=\$(date +%s)
    sed -i \"s/window.VERSION = .*/window.VERSION = '\${TIMESTAMP}';/\" js/config.js
    echo \"✅ Версия обновлена: \${TIMESTAMP}\"
"

echo -e "\n🔄 ШАГ 3/3: Перезагрузка nginx..."
ssh root@$SERVER_IP "
    nginx -t && systemctl reload nginx
    echo \"✅ Nginx перезагружен\"
"

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДЕПЛОЙ ЗАВЕРШЁН!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1️⃣  Очистите кэш браузера (Cmd + Shift + R)"
echo "2️⃣  Зайдите в кабинет медцентра"
echo "3️⃣  Раздел \"Статистика\" должен показывать:"
echo "     • Запросов крови: 28 ✅"
echo "     • Уникальных доноров: 4 ✅"
echo "     • Донаций: 1 ✅"
echo ""
echo "📋 ПРО ДОНОРА ID=3 (Вадимус):"
echo ""
echo "  ❌ Статистика пустая, потому что:"
echo "     • Все отклики в status='confirmed'"
echo "     • НЕТ в status='completed'"
echo ""
echo "  ✅ Чтобы получить статистику:"
echo "     1. Создайте НОВЫЙ запрос (медцентр)"
echo "     2. Откликнитесь (донор ID=3)"
echo "     3. Подтвердите (медцентр - кнопка с галочкой)"
echo "     4. Нажмите \"ВЫПОЛНЕН\" (медцентр)"
echo "     5. Проверьте статистику донора ID=3"
echo ""
echo "📊 ДОНОР ID=1 УЖЕ ИМЕЕТ СТАТИСТИКУ:"
echo "  • total_donations: 1"
echo "  • total_volume_ml: 450 мл"
echo "  • last_donation_date: 2026-01-26"
echo ""
