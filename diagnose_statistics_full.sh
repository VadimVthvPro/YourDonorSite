#!/bin/bash

# ========================================
# 🔍 ДИАГНОСТИКА СТАТИСТИКИ
# ========================================
# Выполните ЭТО на сервере:

echo "🔍 ГЛУБОКАЯ ДИАГНОСТИКА СТАТИСТИКИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo -u postgres psql -d your_donor << 'EOSQL'

-- 1. Проверяем donation_history
\echo '=== 1. DONATION_HISTORY ==='
SELECT id, donor_id, medical_center_id, blood_type, volume_ml, status, donation_date, response_id 
FROM donation_history 
ORDER BY id DESC LIMIT 10;

-- 2. Проверяем users (статистика доноров)
\echo ''
\echo '=== 2. USERS (статистика доноров) ==='
SELECT id, full_name, blood_type, total_donations, total_volume_ml, last_donation_date 
FROM users 
WHERE id IN (1, 3, 8, 11)
ORDER BY id;

-- 3. Проверяем donation_responses (completed)
\echo ''
\echo '=== 3. DONATION_RESPONSES (completed) ==='
SELECT id, user_id, request_id, medical_center_id, status 
FROM donation_responses 
WHERE status = 'completed'
ORDER BY id DESC;

-- 4. Проверяем blood_requests (для медцентра 10)
\echo ''
\echo '=== 4. BLOOD_REQUESTS (медцентр 10) ==='
SELECT 
    COUNT(*) as total_requests, 
    SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
    SUM(CASE WHEN status='fulfilled' THEN 1 ELSE 0 END) as fulfilled,
    SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled
FROM blood_requests 
WHERE medical_center_id = 10;

-- 5. Проверяем уникальных доноров (для медцентра 10)
\echo ''
\echo '=== 5. УНИКАЛЬНЫЕ ДОНОРЫ (медцентр 10) ==='
SELECT COUNT(DISTINCT user_id) as unique_donors
FROM donation_responses
WHERE medical_center_id = 10;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo ""
echo "📋 ОЖИДАЕМЫЕ ЗНАЧЕНИЯ:"
echo "  • donation_history: должны быть записи с donor_id, medical_center_id"
echo "  • users: total_donations и total_volume_ml должны быть > 0 для донора ID=1"
echo "  • donation_responses: должны быть записи со status='completed'"
echo "  • blood_requests: total_requests должно быть 28"
echo "  • unique_donors: должно быть 4"
echo ""
