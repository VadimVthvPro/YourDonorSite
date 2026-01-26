#!/bin/bash
# 🔬 МАКСИМАЛЬНО ГЛУБОКОЕ ИССЛЕДОВАНИЕ СТАТИСТИКИ ДОНОРА И МЕДЦЕНТРА

SERVER_IP="178.172.212.221"

echo "════════════════════════════════════════════════════════════════════════"
echo "🔬 ГЛУБОКОЕ ИССЛЕДОВАНИЕ: ВЕСЬ ЦИКЛ ДОНАЦИЙ И СТАТИСТИКИ"
echo "════════════════════════════════════════════════════════════════════════"

ssh root@$SERVER_IP << 'ENDSSH'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 1: ВСЕ ТАБЛИЦЫ БД - ПОЛНЫЕ СХЕМЫ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor << 'EOSQL'
\echo '--- ТАБЛИЦА: users ---'
\d users

\echo ''
\echo '--- ТАБЛИЦА: blood_requests ---'
\d blood_requests

\echo ''
\echo '--- ТАБЛИЦА: donation_responses ---'
\d donation_responses

\echo ''
\echo '--- ТАБЛИЦА: donation_history ---'
\d donation_history

\echo ''
\echo '--- ТАБЛИЦА: medical_centers ---'
\d medical_centers
EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 2: ВСЕ ДОНОРЫ - ПОЛНАЯ ИНФОРМАЦИЯ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    id, email, full_name, phone, blood_type, 
    total_donations, last_donation_date, total_volume_ml,
    city, is_active, created_at
FROM users 
WHERE role = 'donor'
ORDER BY id;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 3: ВСЕ МЕДЦЕНТРЫ - ПОЛНАЯ ИНФОРМАЦИЯ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    id, name, city, address, phone, 
    approval_status, is_active, created_at
FROM medical_centers
ORDER BY id;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 4: ВСЕ ЗАПРОСЫ КРОВИ (blood_requests)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    id, medical_center_id, blood_type, urgency, 
    status, volume_needed, created_at, updated_at,
    patient_name, description
FROM blood_requests 
ORDER BY id DESC 
LIMIT 20;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 5: СТАТИСТИКА blood_requests ПО СТАТУСАМ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    status, 
    COUNT(*) as count,
    COUNT(DISTINCT medical_center_id) as medcenters
FROM blood_requests 
GROUP BY status 
ORDER BY count DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 6: ВСЕ ОТКЛИКИ ДОНОРОВ (donation_responses)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    id, user_id, request_id, medical_center_id,
    status, created_at, updated_at, notes
FROM donation_responses 
ORDER BY id DESC 
LIMIT 20;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 7: СТАТИСТИКА donation_responses ПО СТАТУСАМ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    status, 
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_donors,
    COUNT(DISTINCT medical_center_id) as unique_medcenters
FROM donation_responses 
GROUP BY status 
ORDER BY count DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 8: ВСЯ ИСТОРИЯ ДОНАЦИЙ (donation_history)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    id, donor_id, medical_center_id, blood_type,
    status, volume_ml, donation_date, response_id,
    created_at
FROM donation_history 
ORDER BY id DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 9: СТАТИСТИКА donation_history"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT donor_id) as unique_donors,
    COUNT(DISTINCT medical_center_id) as unique_medcenters,
    COUNT(DISTINCT response_id) as unique_responses,
    MIN(donation_date) as first_donation,
    MAX(donation_date) as last_donation,
    SUM(volume_ml) as total_volume
FROM donation_history;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 10: СВЯЗЬ donation_history ← donation_responses ← blood_requests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    dh.id as history_id,
    dh.donor_id,
    dh.medical_center_id as history_mc_id,
    dh.blood_type as history_blood_type,
    dh.status as history_status,
    dh.volume_ml,
    dh.donation_date,
    dr.id as response_id,
    dr.user_id as response_user_id,
    dr.medical_center_id as response_mc_id,
    dr.status as response_status,
    br.id as request_id,
    br.medical_center_id as request_mc_id,
    br.blood_type as request_blood_type,
    br.status as request_status
FROM donation_history dh
LEFT JOIN donation_responses dr ON dh.response_id = dr.id
LEFT JOIN blood_requests br ON dr.request_id = br.id
ORDER BY dh.id DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 11: 🔍 ПОТЕРЯННЫЕ ДОНАЦИИ (responses БЕЗ записи в history)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    dr.id as response_id,
    dr.user_id as donor_id,
    dr.request_id,
    dr.medical_center_id,
    dr.status as response_status,
    dr.created_at as response_created,
    dr.updated_at as response_updated,
    br.blood_type,
    br.status as request_status,
    dh.id as history_id
FROM donation_responses dr
JOIN blood_requests br ON dr.request_id = br.id
LEFT JOIN donation_history dh ON dr.id = dh.response_id
WHERE dr.status IN ('completed', 'confirmed', 'fulfilled')
ORDER BY dr.id DESC;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 БЛОК 12: 🔍 ПРОВЕРКА users.total_donations vs donation_history"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo -u postgres psql -d your_donor -c "
SELECT 
    u.id as donor_id,
    u.email,
    u.full_name,
    u.blood_type,
    u.total_donations as user_total_donations,
    u.total_volume_ml as user_total_volume,
    u.last_donation_date,
    COUNT(dh.id) as history_count,
    COALESCE(SUM(dh.volume_ml), 0) as history_volume
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.role = 'donor'
GROUP BY u.id, u.email, u.full_name, u.blood_type, u.total_donations, u.total_volume_ml, u.last_donation_date
ORDER BY u.id;
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 13: КОД app.py - ЭНДПОИНТ respond_to_request (донор откликается)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def respond_to_request" /opt/tvoydonor/website/backend/app.py
grep -A 50 "def respond_to_request" /opt/tvoydonor/website/backend/app.py | head -60

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 14: КОД app.py - ЭНДПОИНТ update_response_status (медцентр подтверждает)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def update_response_status" /opt/tvoydonor/website/backend/app.py
grep -A 80 "def update_response_status" /opt/tvoydonor/website/backend/app.py | head -100

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 15: КОД app.py - ЭНДПОИНТ fulfill_request (кнопка ВЫПОЛНЕН)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def fulfill_request" /opt/tvoydonor/website/backend/app.py
grep -A 120 "def fulfill_request" /opt/tvoydonor/website/backend/app.py | head -150

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 16: КОД app.py - ЭНДПОИНТ record_donation (запись донации)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def record_donation" /opt/tvoydonor/website/backend/app.py
grep -A 100 "def record_donation" /opt/tvoydonor/website/backend/app.py | head -120

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 17: КОД app.py - ЭНДПОИНТ get_donor_stats (статистика донора)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def get_donor_stats" /opt/tvoydonor/website/backend/app.py
grep -A 60 "def get_donor_stats" /opt/tvoydonor/website/backend/app.py | head -80

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 18: КОД app.py - ЭНДПОИНТ get_medcenter_stats (статистика медцентра)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def get_medcenter_stats" /opt/tvoydonor/website/backend/app.py
grep -A 100 "def get_medcenter_stats" /opt/tvoydonor/website/backend/app.py | head -120

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 19: КОД app.py - ЭНДПОИНТ get_medical_center_statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "def get_medical_center_statistics" /opt/tvoydonor/website/backend/app.py
grep -A 150 "def get_medical_center_statistics" /opt/tvoydonor/website/backend/app.py | head -180

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 20: FRONTEND donor-dashboard.js - loadDonationStatistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "loadDonationStatistics" /opt/tvoydonor/website/js/donor-dashboard.js | head -5
grep -A 50 "function loadDonationStatistics" /opt/tvoydonor/website/js/donor-dashboard.js | head -60

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 21: FRONTEND medcenter-dashboard.js - loadStatistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "function loadStatistics" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -5
grep -A 80 "function loadStatistics" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -100

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 22: FRONTEND medcenter-dashboard.js - fulfillRequest"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -n "function fulfillRequest" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -5
grep -A 50 "function fulfillRequest" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -60

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 БЛОК 23: ПОСЛЕДНИЕ 100 СТРОК API ЛОГОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -100 /var/log/tvoydonor-api.err.log

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ГЛУБОКОЕ ИССЛЕДОВАНИЕ ЗАВЕРШЕНО"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENDSSH
