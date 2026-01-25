#!/bin/bash
echo "========================================="
echo "🔍 ПОЛНЫЙ АУДИТ СТАТИСТИКИ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ ПРОВЕРКА ТАБЛИЦ В БД:"
echo "=========================================
"

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Список всех таблиц
SELECT 'Все таблицы в БД:' as info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Проверка donation_history
SELECT '
Таблица donation_history:' as info;
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'donation_history'
) as exists;

-- Проверка donation_responses
SELECT '
Структура donation_responses:' as info;
\d donation_responses

-- Данные donation_responses
SELECT '
Завершённые донации (donation_responses):' as info;
SELECT 
    dr.id,
    dr.user_id,
    u.full_name,
    dr.medical_center_id,
    mc.name as mc_name,
    dr.status,
    dr.actual_donation_date,
    dr.updated_at
FROM donation_responses dr
LEFT JOIN users u ON dr.user_id = u.id
LEFT JOIN medical_centers mc ON dr.medical_center_id = mc.id
WHERE dr.status = 'completed'
ORDER BY dr.updated_at DESC
LIMIT 10;

-- Проверка users
SELECT '
Доноры с total_donations > 0:' as info;
SELECT 
    id,
    full_name,
    total_donations,
    total_volume_ml,
    last_donation_date
FROM users
WHERE total_donations > 0
ORDER BY total_donations DESC;

-- Проверка blood_requests
SELECT '
Запросы крови:' as info;
SELECT 
    br.id,
    br.medical_center_id,
    mc.name as mc_name,
    br.blood_type,
    br.status,
    br.created_at
FROM blood_requests br
LEFT JOIN medical_centers mc ON br.medical_center_id = mc.id
ORDER BY br.created_at DESC
LIMIT 5;

EOSQL

echo ""
echo "2️⃣ ПРОВЕРКА API ЭНДПОИНТОВ:"
echo "=========================================
"

# Проверяем эндпоинты в app.py
echo "Эндпоинты статистики в app.py:"
grep -n "route.*statistics\|route.*donor/profile" /opt/tvoydonor/website/backend/app.py | head -20

echo ""
echo "3️⃣ ПРОВЕРКА ЛОГОВ API:"
echo "=========================================
"

echo "Последние 30 строк логов API:"
tail -30 /var/log/tvoydonor-api.err.log

echo ""
echo "4️⃣ ПРОВЕРКА FRONTEND JS:"
echo "=========================================
"

echo "Проверка donor-dashboard.js (загрузка статистики):"
grep -n "loadDonationStatistics\|donor/statistics" /opt/tvoydonor/website/js/donor-dashboard.js | head -10

echo ""
echo "Проверка medcenter-dashboard.js (загрузка статистики):"
grep -n "loadStatistics\|medcenter/statistics" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -10

echo ""
echo "=========================================
✅ АУДИТ ЗАВЕРШЁН
=========================================
"

ENDSSH
