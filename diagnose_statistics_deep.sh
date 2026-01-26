#!/bin/bash

# ============================================
# ГЛУБОКАЯ ДИАГНОСТИКА СТАТИСТИКИ
# ============================================

echo "╔════════════════════════════════════════╗"
echo "║   🔬 ДИАГНОСТИКА СТАТИСТИКИ           ║"
echo "╚════════════════════════════════════════╝"
echo ""

# ============================================
# ШАГ 1: ПРОВЕРКА СХЕМЫ БД
# ============================================

echo "📊 ШАГ 1/6: Проверка схемы donation_history..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'
\echo '=== СХЕМА ТАБЛИЦЫ donation_history ==='
\d donation_history

\echo ''
\echo '=== КОЛИЧЕСТВО ЗАПИСЕЙ ==='
SELECT COUNT(*) as total_records FROM donation_history;

\echo ''
\echo '=== ПОСЛЕДНИЕ 3 ЗАПИСИ ==='
SELECT * FROM donation_history ORDER BY created_at DESC LIMIT 3;

\echo ''
\echo '=== ПРОВЕРКА КОЛОНОК ==='
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'donation_history'
ORDER BY ordinal_position;
EOSQL

echo ""
echo "✅ Шаг 1 завершён"
echo ""

# ============================================
# ШАГ 2: ПРОВЕРКА ДАННЫХ ДОНОРА
# ============================================

echo "📊 ШАГ 2/6: Проверка данных донора..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'
\echo '=== ДАННЫЕ ДОНОРОВ (last_donation_date, total_donations) ==='
SELECT 
    id,
    full_name,
    blood_type,
    last_donation_date,
    total_donations,
    total_volume_ml
FROM users 
WHERE total_donations > 0 OR last_donation_date IS NOT NULL
ORDER BY id DESC
LIMIT 5;

\echo ''
\echo '=== СВЯЗЬ donation_history <-> users ==='
SELECT 
    dh.id as history_id,
    dh.donor_id,
    u.full_name,
    dh.donation_date,
    dh.blood_type,
    dh.medical_center_id
FROM donation_history dh
LEFT JOIN users u ON dh.donor_id = u.id
ORDER BY dh.created_at DESC
LIMIT 5;
EOSQL

echo ""
echo "✅ Шаг 2 завершён"
echo ""

# ============================================
# ШАГ 3: ПРОВЕРКА ОТКЛИКОВ И СТАТУСОВ
# ============================================

echo "📊 ШАГ 3/6: Проверка откликов и статусов..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'
\echo '=== ОТКЛИКИ СО СТАТУСОМ completed ==='
SELECT 
    id,
    request_id,
    user_id,
    medical_center_id,
    status,
    donation_completed,
    actual_donation_date,
    created_at
FROM donation_responses
WHERE status = 'completed'
ORDER BY actual_donation_date DESC
LIMIT 5;

\echo ''
\echo '=== СВЯЗЬ donation_responses -> donation_history ==='
SELECT 
    dr.id as response_id,
    dr.user_id,
    dr.status,
    dr.actual_donation_date,
    dh.id as history_id,
    dh.donation_date
FROM donation_responses dr
LEFT JOIN donation_history dh ON dh.response_id = dr.id
WHERE dr.status = 'completed'
ORDER BY dr.actual_donation_date DESC
LIMIT 5;
EOSQL

echo ""
echo "✅ Шаг 3 завершён"
echo ""

# ============================================
# ШАГ 4: ПРОВЕРКА API
# ============================================

echo "📊 ШАГ 4/6: Проверка API статистики..."
echo ""

echo "Проверяем доступность API..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://tvoydonor.by/api/

echo ""
echo "Проверяем логи API за последние 50 строк..."
tail -50 /var/log/tvoydonor-api.err.log

echo ""
echo "✅ Шаг 4 завершён"
echo ""

# ============================================
# ШАГ 5: ПРОВЕРКА FRONTEND
# ============================================

echo "📊 ШАГ 5/6: Проверка frontend файлов..."
echo ""

echo "Проверяем donor-dashboard.js (вызов loadDonationStatistics)..."
grep -n "loadDonationStatistics" /opt/tvoydonor/website/js/donor-dashboard.js | head -5

echo ""
echo "Проверяем config.js (версия)..."
grep "window.VERSION" /opt/tvoydonor/website/js/config.js

echo ""
echo "✅ Шаг 5 завершён"
echo ""

# ============================================
# ШАГ 6: ТЕСТОВЫЙ ЗАПРОС
# ============================================

echo "📊 ШАГ 6/6: Тестовый SQL запрос (как в app.py)..."
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'
\echo '=== ТЕСТ: Запрос статистики донора (как в app.py) ==='
-- Берём первого донора с донациями
DO $$
DECLARE
    test_user_id INTEGER;
BEGIN
    SELECT id INTO test_user_id FROM users WHERE total_donations > 0 LIMIT 1;
    
    IF test_user_id IS NULL THEN
        RAISE NOTICE 'НЕТ доноров с total_donations > 0';
    ELSE
        RAISE NOTICE 'Тестируем с user_id = %', test_user_id;
        
        -- Запрос как в app.py:654-662
        RAISE NOTICE 'Выполняем SELECT FROM donation_history...';
        PERFORM dh.*, mc.name as medical_center_name
        FROM donation_history dh
        LEFT JOIN medical_centers mc ON dh.medical_center_id = mc.id
        WHERE dh.donor_id = test_user_id
        ORDER BY dh.donation_date DESC
        LIMIT 20;
        
        GET DIAGNOSTICS test_user_id = ROW_COUNT;
        RAISE NOTICE 'Найдено записей: %', test_user_id;
    END IF;
END $$;

\echo ''
\echo '=== ТЕСТ: Запрос статистики медцентра (как в app.py) ==='
DO $$
DECLARE
    test_mc_id INTEGER;
    rec_count INTEGER;
BEGIN
    SELECT id INTO test_mc_id FROM medical_centers LIMIT 1;
    
    IF test_mc_id IS NULL THEN
        RAISE NOTICE 'НЕТ медцентров';
    ELSE
        RAISE NOTICE 'Тестируем с medical_center_id = %', test_mc_id;
        
        -- Запрос как в app.py:3797-3805
        SELECT COUNT(*) INTO rec_count
        FROM donation_history dh
        JOIN users u ON dh.donor_id = u.id
        WHERE dh.medical_center_id = test_mc_id;
        
        RAISE NOTICE 'Найдено донаций: %', rec_count;
    END IF;
END $$;
EOSQL

echo ""
echo "✅ Шаг 6 завершён"
echo ""

# ============================================
# ИТОГИ
# ============================================

echo "╔════════════════════════════════════════╗"
echo "║   📋 ДИАГНОСТИКА ЗАВЕРШЕНА            ║"
echo "╚════════════════════════════════════════╝"
echo ""

echo "Скопируйте ВЕСЬ вывод выше и отправьте мне!"
echo ""
