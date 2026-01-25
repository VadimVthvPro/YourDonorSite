#!/bin/bash
echo "========================================="
echo "🔍 ШАГ 1: ПРОВЕРКА БАЗЫ ДАННЫХ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

sudo -u postgres psql -d your_donor << 'EOSQL'

-- 1. Проверка существования таблиц
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '1️⃣ СУЩЕСТВОВАНИЕ ТАБЛИЦ:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    CASE WHEN EXISTS (SELECT FROM pg_tables WHERE tablename = 'donation_history') 
        THEN '✅ donation_history EXISTS' 
        ELSE '❌ donation_history NOT FOUND' 
    END as table_check;

-- 2. Структура donation_history
\echo ''
\echo '2️⃣ СТРУКТУРА donation_history:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\d donation_history

-- 3. Данные в donation_history
\echo ''
\echo '3️⃣ ЗАПИСИ В donation_history:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT COUNT(*) as total_records FROM donation_history;

SELECT * FROM donation_history ORDER BY created_at DESC LIMIT 5;

-- 4. Завершённые donation_responses
\echo ''
\echo '4️⃣ ЗАВЕРШЁННЫЕ donation_responses:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT 
    dr.id,
    dr.user_id,
    u.full_name,
    dr.medical_center_id,
    dr.status,
    dr.actual_donation_date,
    dr.updated_at
FROM donation_responses dr
LEFT JOIN users u ON dr.user_id = u.id
WHERE dr.status = 'completed'
ORDER BY dr.updated_at DESC
LIMIT 5;

-- 5. Статистика в users
\echo ''
\echo '5️⃣ СЧЁТЧИКИ В users:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT 
    id,
    full_name,
    total_donations,
    total_volume_ml,
    last_donation_date
FROM users
WHERE total_donations > 0 OR last_donation_date IS NOT NULL
ORDER BY total_donations DESC;

-- 6. Сравнение users vs donation_history
\echo ''
\echo '6️⃣ СРАВНЕНИЕ users.total_donations VS donation_history:'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT 
    u.id,
    u.full_name,
    u.total_donations as "Счётчик в users",
    COUNT(dh.id) as "Записей в history",
    CASE 
        WHEN u.total_donations = COUNT(dh.id) THEN '✅ Совпадает'
        WHEN u.total_donations > COUNT(dh.id) THEN '⚠️ В users больше'
        ELSE '❌ Не совпадает'
    END as status
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0 OR dh.id IS NOT NULL
GROUP BY u.id, u.full_name, u.total_donations
ORDER BY u.total_donations DESC;

EOSQL

echo ""
echo "=========================================
✅ ПРОВЕРКА БД ЗАВЕРШЕНА
=========================================
"

ENDSSH
