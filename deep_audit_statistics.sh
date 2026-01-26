#!/bin/bash

# ========================================
# 🔬 ГЛУБОКИЙ АУДИТ СТАТИСТИКИ
# ========================================

echo "🔬 КАПИТАЛЬНЫЙ АУДИТ СИСТЕМЫ СТАТИСТИКИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ssh root@178.172.212.221 << 'EOSSH'

sudo -u postgres psql -d your_donor << 'EOSQL'

\echo '=== 1. DONATION_HISTORY (ВСЕ ЗАПИСИ) ==='
SELECT * FROM donation_history ORDER BY id;

\echo ''
\echo '=== 2. DONATION_RESPONSES (ВСЕ confirmed и completed) ==='
SELECT id, user_id, request_id, medical_center_id, status, created_at
FROM donation_responses
WHERE status IN ('confirmed', 'completed')
ORDER BY id;

\echo ''
\echo '=== 3. USERS (ВСЕ ДОНОРЫ) ==='
SELECT id, full_name, blood_type, total_donations, total_volume_ml, last_donation_date
FROM users
WHERE id IN (1, 3, 8, 11)
ORDER BY id;

\echo ''
\echo '=== 4. BLOOD_REQUESTS (детальная статистика) ==='
SELECT 
    id,
    medical_center_id,
    blood_type,
    urgency,
    status,
    created_at,
    fulfilled_at
FROM blood_requests
WHERE medical_center_id = 10
ORDER BY id DESC
LIMIT 30;

\echo ''
\echo '=== 5. ПРОВЕРКА: Какие отклики ДОЛЖНЫ были стать донациями? ==='
SELECT 
    dr.id as response_id,
    dr.user_id,
    u.full_name,
    dr.request_id,
    br.blood_type,
    dr.status as response_status,
    br.status as request_status,
    dr.created_at
FROM donation_responses dr
LEFT JOIN users u ON dr.user_id = u.id
LEFT JOIN blood_requests br ON dr.request_id = br.id
WHERE dr.medical_center_id = 10
  AND dr.status = 'confirmed'
  AND br.status = 'fulfilled'
ORDER BY dr.id;

\echo ''
\echo '=== 6. КРИТИЧЕСКИЙ АНАЛИЗ: Почему donation_history пустая для ID=3? ==='
\echo 'Запросы с fulfilled статусом:'
SELECT id, status, fulfilled_at FROM blood_requests WHERE status = 'fulfilled' AND medical_center_id = 10 LIMIT 10;

\echo ''
\echo 'Confirmed отклики на fulfilled запросы:'
SELECT 
    dr.id,
    dr.user_id,
    dr.request_id,
    dr.status,
    br.status as req_status
FROM donation_responses dr
JOIN blood_requests br ON dr.request_id = br.id
WHERE dr.status = 'confirmed' 
  AND br.status = 'fulfilled'
  AND dr.medical_center_id = 10;

\echo ''
\echo '=== 7. ПРОВЕРКА ЛОГОВ API: Были ли попытки записать донации? ==='
\q

EOSQL

echo ""
echo "📋 ПРОВЕРКА ЛОГОВ API..."
echo "Ищем POST запросы к /api/medical-center/donations:"
grep "POST.*donations" /var/log/tvoydonor-api.err.log | tail -20

echo ""
echo "Ищем ошибки при записи донаций:"
grep -A 5 "donation_history\|INSERT INTO donation" /var/log/tvoydonor-api.err.log | tail -50

echo ""
echo "Ищем PUT запросы к /api/blood-requests (завершение):"
grep "PUT.*blood-requests" /var/log/tvoydonor-api.err.log | tail -20

EOSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ АУДИТ ЗАВЕРШЁН"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
