#!/bin/bash
echo "========================================="
echo "🔍 МАСТЕР-ДИАГНОСТИКА СТАТИСТИКИ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 1: ПРОВЕРКА БАЗЫ ДАННЫХ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Проверка donation_history
SELECT 
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE tablename = 'donation_history') 
        THEN '✅ donation_history СУЩЕСТВУЕТ' 
        ELSE '❌ donation_history НЕ НАЙДЕНА' 
    END as status;

SELECT COUNT(*) as "Записей в donation_history" FROM donation_history;

-- Завершённые донации
SELECT COUNT(*) as "Завершённых donation_responses" 
FROM donation_responses 
WHERE status = 'completed';

-- Доноры со счётчиком
SELECT COUNT(*) as "Доноров с total_donations > 0" 
FROM users 
WHERE total_donations > 0;

-- Детальное сравнение
SELECT 
    u.id,
    u.full_name,
    u.total_donations as "users",
    COUNT(dh.id) as "history"
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0
GROUP BY u.id, u.full_name, u.total_donations;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 2: ПРОВЕРКА API ЭНДПОИНТОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Эндпоинты статистики в app.py:"
grep -n "@app.route.*statistics\|@app.route.*stats" /opt/tvoydonor/website/backend/app.py

echo ""
echo "Проверка наличия donation_history в коде:"
grep -c "donation_history" /opt/tvoydonor/website/backend/app.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 3: ТЕСТ API (curl)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "GET /api/stats/medcenter (ожидаем 401 без токена):"
curl -s -w "\nHTTP Code: %{http_code}\n" http://localhost:5001/api/stats/medcenter

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 4: ПРОВЕРКА ЛОГОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Ошибки с donation_history:"
grep -i "donation_history\|UndefinedTable\|relation.*does not exist" /var/log/tvoydonor-api.err.log | tail -10

echo ""
echo "Последние ошибки API:"
tail -20 /var/log/tvoydonor-api.err.log | grep -i "error\|exception\|traceback" || echo "Ошибок не найдено"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 5: ПРОВЕРКА FRONTEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Функция loadDonationStatistics в donor-dashboard.js:"
grep -n "loadDonationStatistics" /opt/tvoydonor/website/js/donor-dashboard.js | head -5

echo ""
echo "Функция loadStatisticsFromAPI в medcenter-dashboard.js:"
grep -n "loadStatisticsFromAPI" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -5

echo ""
echo "=========================================
📊 ДИАГНОСТИКА ЗАВЕРШЕНА
=========================================
"

ENDSSH
