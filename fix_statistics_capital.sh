#!/bin/bash

# ========================================
# 🔥 КАПИТАЛЬНОЕ ИСПРАВЛЕНИЕ СТАТИСТИКИ
# ========================================
# КОРНЕВАЯ ПРИЧИНА:
#   • /api/stats/medcenter считал donors из users.medical_center_id
#   • НО ДОНОРЫ НЕ ПРИВЯЗАНЫ К МЕДЦЕНТРАМ!!!
#   • Правильно: считать из donation_responses
#
# ИСПРАВЛЕНО:
#   1. app.py: get_medcenter_stats() - donors из donation_responses
#   2. medcenter-dashboard.js: currentStatsperiod = 'all'
#
# РЕЗУЛЬТАТ:
#   ✅ Главная панель: "Уникальных доноров: 4"
#   ✅ Раздел "Статистика": "Запросов крови: 28"
# ========================================

set -e

SERVER_IP="178.172.212.221"

echo -e "\n🔥 КАПИТАЛЬНОЕ ИСПРАВЛЕНИЕ СТАТИСТИКИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Что исправлено:"
echo ""
echo "  ❌ БЫЛО:"
echo "     SELECT COUNT(*) FROM users WHERE medical_center_id = %s"
echo "     ↳ Результат: 0 (доноры не привязаны к медцентрам!)"
echo ""
echo "  ✅ СТАЛО:"
echo "     SELECT COUNT(DISTINCT user_id) FROM donation_responses"
echo "     JOIN blood_requests ON ... WHERE medical_center_id = %s"
echo "     ↳ Результат: 4 (уникальные доноры, откликавшиеся)"
echo ""
echo "📊 Ожидаемые значения:"
echo "  • Главная панель:"
echo "    - Уникальных доноров: 4 ✅"
echo "    - Активных запросов: 0"
echo "    - Ожидают подтверждения: 1"
echo "  • Раздел 'Статистика':"
echo "    - Запросов крови: 28 ✅"
echo "    - Уникальных доноров: 4 ✅"
echo "    - Донаций: 1 ✅"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено пользователем"
    exit 0
fi

echo -e "\n📤 ШАГ 1/4: Загрузка исправленного backend..."
scp website/backend/app.py root@$SERVER_IP:/opt/tvoydonor/website/backend/
echo "✅ app.py загружен"

echo -e "\n📤 ШАГ 2/4: Загрузка исправленного frontend..."
scp website/js/medcenter-dashboard.js root@$SERVER_IP:/opt/tvoydonor/website/js/
echo "✅ medcenter-dashboard.js загружен"

echo -e "\n🔄 ШАГ 3/4: Перезапуск сервисов..."
ssh root@$SERVER_IP "
    # Перезапуск API
    supervisorctl restart tvoydonor-api
    echo \"✅ API перезагружен\"
    
    # Обновление версии frontend (cache busting)
    cd /opt/tvoydonor/website
    TIMESTAMP=\$(date +%s)
    sed -i \"s/window.VERSION = .*/window.VERSION = '\${TIMESTAMP}';/\" js/config.js
    echo \"✅ Версия обновлена: \${TIMESTAMP}\"
    
    # Перезагрузка nginx
    nginx -t && systemctl reload nginx
    echo \"✅ Nginx перезагружен\"
"

echo -e "\n📊 ШАГ 4/4: Проверка логов..."
ssh root@$SERVER_IP "
    echo \"Ждём 2 секунды для прогрева API...\"
    sleep 2
    
    echo \"Проверяем логи на ошибки:\"
    tail -30 /var/log/tvoydonor-api.err.log | grep -i \"error\|exception\" || echo \"✅ Ошибок нет\"
"

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДЕПЛОЙ ЗАВЕРШЁН!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1️⃣  Очистите кэш браузера (Cmd + Shift + R)"
echo ""
echo "2️⃣  ГЛАВНАЯ ПАНЕЛЬ медцентра:"
echo "    Должно показывать:"
echo "     📊 4 Уникальных донора ✅"
echo "     📋 0 Активных запросов"
echo "     ⏳ 1 Ожидает подтверждения"
echo "     🩸 1 Донация за месяц"
echo ""
echo "3️⃣  РАЗДЕЛ 'СТАТИСТИКА':"
echo "    Должно показывать:"
echo "     📋 28 Запросов крови ✅"
echo "     👥 4 Уникальных донора ✅"
echo "     🩸 1 Донация ✅"
echo "     📊 0.5 л Объём крови"
echo ""
echo "4️⃣  ДОНОР ID=1 (Войтехович Вадим):"
echo "    Статистика должна показывать:"
echo "     🩸 1 донация"
echo "     📊 450 мл"
echo "     📅 26.01.2026"
echo ""
echo "5️⃣  ДОНОР ID=3 (Вадимус):"
echo "    • Статистика ПУСТАЯ (НЕ ЗАВЕРШИЛ донацию!)"
echo "    • Чтобы получить статистику:"
echo "      a) Медцентр создаёт новый запрос"
echo "      b) Донор ID=3 откликается"
echo "      c) Медцентр подтверждает (кнопка ✓)"
echo "      d) Медцентр нажимает 'ВЫПОЛНЕН'"
echo "      e) Проверяем статистику донора ID=3"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📖 Подробности в: ROOT_CAUSE_MEDCENTER_STATS.md"
echo ""
