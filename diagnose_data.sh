#!/bin/bash
# 🔬 ДИАГНОСТИКА: ПРОВЕРКА ДАННЫХ В БД

echo "════════════════════════════════════════════════════"
echo "🔬 ДИАГНОСТИКА СТАТИСТИКИ - ПРОВЕРКА ДАННЫХ В БД"
echo "════════════════════════════════════════════════════"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 1. ЗАПРОСЫ КРОВИ (blood_requests)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL1'
SELECT 
    medical_center_id,
    status,
    COUNT(*) as count
FROM blood_requests
GROUP BY medical_center_id, status
ORDER BY medical_center_id, status;
SQL1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 2. ОТКЛИКИ ДОНОРОВ (donation_responses)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL2'
SELECT 
    medical_center_id,
    status,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_donors
FROM donation_responses
GROUP BY medical_center_id, status
ORDER BY medical_center_id, status;
SQL2

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 3. ИСТОРИЯ ДОНАЦИЙ (donation_history)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL3'
SELECT 
    medical_center_id,
    COUNT(*) as total_donations,
    COUNT(DISTINCT donor_id) as unique_donors,
    SUM(volume_ml) as total_volume_ml
FROM donation_history
GROUP BY medical_center_id
ORDER BY medical_center_id;
SQL3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 4. СТАТИСТИКА ДОНОРОВ (users)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL4'
SELECT 
    id,
    email,
    full_name,
    blood_type,
    total_donations,
    last_donation_date,
    total_volume_ml
FROM users
WHERE role = 'donor'
ORDER BY id;
SQL4

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 5. ПОТЕРЯННЫЕ ДОНАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL5'
SELECT 
    dr.id as response_id,
    dr.user_id as donor_id,
    dr.request_id,
    dr.medical_center_id,
    dr.status as response_status,
    dr.created_at as response_date,
    br.blood_type,
    dh.id as history_id
FROM donation_responses dr
LEFT JOIN donation_history dh ON dr.id = dh.response_id
JOIN blood_requests br ON dr.request_id = br.id
WHERE dr.status IN ('completed', 'confirmed')
ORDER BY dr.id DESC;
SQL5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 6. ПОСЛЕДНИЕ ЗАПИСИ В donation_history"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'SQL6'
SELECT 
    id,
    donor_id,
    medical_center_id,
    blood_type,
    status,
    volume_ml,
    donation_date,
    response_id,
    created_at
FROM donation_history
ORDER BY id DESC
LIMIT 20;
SQL6

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
