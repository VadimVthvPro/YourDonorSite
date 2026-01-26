#!/bin/bash
# 🔧 ПОЛНОЕ РЕШЕНИЕ ПРОБЛЕМ СТАТИСТИКИ

SERVER_IP="178.172.212.221"

echo "════════════════════════════════════════════════════════════════"
echo "🔧 ФИНАЛЬНОЕ РЕШЕНИЕ: МИГРАЦИЯ ДАННЫХ + ИСПРАВЛЕНИЕ СТАТИСТИКИ"
echo "════════════════════════════════════════════════════════════════"

echo ""
echo "📋 ЧТО БУДЕТ СДЕЛАНО:"
echo "  1. Миграция: Создание donation_history для всех confirmed откликов"
echo "  2. Обновление users.total_donations для всех доноров"
echo "  3. Исправление API: добавлен total_requests"
echo "  4. Исправление frontend: показ всех запросов вместо только active"
echo ""

read -p "Продолжить? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 ШАГ 1/5: Загрузка файлов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • SQL миграция..."
scp migrate_missing_donations.sql root@$SERVER_IP:/tmp/
echo "  • app.py..."
scp website/backend/app.py root@$SERVER_IP:/opt/tvoydonor/website/backend/
echo "  • medcenter-dashboard.js..."
scp website/js/medcenter-dashboard.js root@$SERVER_IP:/opt/tvoydonor/website/js/
echo "✅ Файлы загружены"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  ШАГ 2/5: Миграция базы данных"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh root@$SERVER_IP "
    echo '📊 ДО миграции:'
    sudo -u postgres psql -d your_donor -c '
        SELECT COUNT(*) as total FROM donation_history;
        SELECT id, email, total_donations FROM users WHERE id IN (1,3,8,11);
    '
    
    echo ''
    echo '🔄 Выполняем миграцию...'
    sudo -u postgres psql -d your_donor -f /tmp/migrate_missing_donations.sql
    
    echo ''
    echo '📊 ПОСЛЕ миграции:'
    sudo -u postgres psql -d your_donor -c '
        SELECT COUNT(*) as total FROM donation_history;
        SELECT id, email, total_donations, last_donation_date FROM users WHERE id IN (1,3,8,11);
    '
    
    echo '✅ Миграция завершена'
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 ШАГ 3/5: Обновление версии и перезагрузка"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh root@$SERVER_IP "
    cd /opt/tvoydonor/website
    TIMESTAMP=\$(date +%s)
    sed -i \"s/window.VERSION = .*/window.VERSION = '\${TIMESTAMP}';/\" js/config.js
    echo \"✅ Версия: \${TIMESTAMP}\"
    
    nginx -t && systemctl reload nginx
    echo \"✅ Nginx перезагружен\"
    
    supervisorctl restart tvoydonor-api
    echo \"✅ API перезагружен\"
    
    sleep 3
    supervisorctl status tvoydonor-api
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ШАГ 4/5: Проверка API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ожидание 3 секунды..."
sleep 3

ssh root@$SERVER_IP "
    echo '📋 Последние строки логов API:'
    tail -30 /var/log/tvoydonor-api.err.log | grep -v 'INFO' | tail -15 || echo '✅ Нет ошибок'
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 ШАГ 5/5: Финальная проверка данных"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh root@$SERVER_IP "
    sudo -u postgres psql -d your_donor -c '
        SELECT 
            mc_id, 
            total_requests,
            unique_donors,
            total_donations
        FROM (
            SELECT 10 as mc_id
        ) t
        CROSS JOIN LATERAL (
            SELECT COUNT(*) as total_requests FROM blood_requests WHERE medical_center_id = 10
        ) br
        CROSS JOIN LATERAL (
            SELECT COUNT(DISTINCT dr.user_id) as unique_donors 
            FROM donation_responses dr
            JOIN blood_requests req ON dr.request_id = req.id
            WHERE req.medical_center_id = 10
        ) dr
        CROSS JOIN LATERAL (
            SELECT COUNT(*) as total_donations FROM donation_history WHERE medical_center_id = 10
        ) dh;
    '
"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 РЕЗУЛЬТАТЫ:"
echo "  • Мигрированы все confirmed отклики в donation_history"
echo "  • Обновлена статистика доноров (total_donations, total_volume_ml)"
echo "  • Исправлен API: /api/stats/medcenter теперь возвращает total_requests"
echo "  • Исправлен frontend: меню показывает все запросы"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "  1. Зайдите в кабинет медцентра"
echo "  2. Проверьте меню: '📋 X ЗАПРОСОВ КРОВИ' и '👥 X УНИКАЛЬНЫХ ДОНОРОВ'"
echo "  3. Зайдите в кабинет донора (ID=3)"
echo "  4. Проверьте статистику: должно быть несколько донаций"
echo ""
