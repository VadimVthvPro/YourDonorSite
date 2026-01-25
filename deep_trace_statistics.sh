#!/bin/bash
echo "========================================="
echo "🔍 ГЛУБОКАЯ ТРАССИРОВКА МЕХАНИЗМА"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 1: ПРОВЕРКА ТАБЛИЦЫ donation_history"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Существует ли таблица?
SELECT 
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE tablename = 'donation_history') 
        THEN '✅ СУЩЕСТВУЕТ' 
        ELSE '❌ НЕ НАЙДЕНА' 
    END as "donation_history";

-- Структура
\d donation_history

-- Сколько записей?
SELECT COUNT(*) as "Всего записей" FROM donation_history;

-- Последние записи
SELECT * FROM donation_history ORDER BY created_at DESC LIMIT 3;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 2: ПРОВЕРКА donation_responses"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Все статусы
SELECT status, COUNT(*) as count 
FROM donation_responses 
GROUP BY status;

-- Последние completed
SELECT 
    dr.id,
    dr.user_id,
    u.full_name as donor,
    dr.status,
    dr.actual_donation_date,
    dr.created_at,
    dr.updated_at
FROM donation_responses dr
LEFT JOIN users u ON dr.user_id = u.id
ORDER BY dr.updated_at DESC
LIMIT 5;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 3: ПРОВЕРКА ЛОГИКИ В app.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Функция update_response (начисление донаций):"
echo "Строки 2130-2150:"
sed -n '2130,2150p' /opt/tvoydonor/website/backend/app.py

echo ""
echo "Проверка наличия INSERT в donation_history:"
grep -n "INSERT INTO donation_history" /opt/tvoydonor/website/backend/app.py || echo "❌ НЕ НАЙДЕНО!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 4: ТЕСТИРОВАНИЕ API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Проверка доступности API:"
curl -s http://localhost:5001/api/donor/statistics 2>&1 | head -5

echo ""
echo "Последние ошибки API:"
tail -30 /var/log/tvoydonor-api.err.log | grep -A5 "donation_history\|UndefinedTable\|Exception\|ERROR" || echo "Ошибок не найдено"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ЭТАП 5: ПРОВЕРКА USERS СЧЁТЧИКОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

SELECT 
    id,
    full_name,
    total_donations,
    total_volume_ml,
    last_donation_date
FROM users
WHERE total_donations > 0 OR last_donation_date IS NOT NULL
ORDER BY total_donations DESC;

EOSQL

echo ""
echo "=========================================
✅ ДИАГНОСТИКА ЗАВЕРШЕНА
=========================================
"

ENDSSH
