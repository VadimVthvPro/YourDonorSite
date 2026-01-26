#!/bin/bash

# ======================================================
# 🔍 ДИАГНОСТИКА: Почему донации не записываются?
# ======================================================

SERVER_IP="178.172.212.221"

echo -e "\n🔍 ДИАГНОСТИКА МЕХАНИЗМА ЗАВЕРШЕНИЯ ЗАПРОСОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 ШАГ 1/5: Проверяем версию medcenter-dashboard.js..."
ssh root@$SERVER_IP << 'EOSSH1'
echo "Ищем правильную функцию в onclick кнопки:"
grep -n "onclick.*Request.*Fulfilled\|onclick.*fulfillRequest" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -5
echo ""
echo "Проверяем наличие функции fulfillRequest:"
grep -n "^async function fulfillRequest" /opt/tvoydonor/website/js/medcenter-dashboard.js | head -3
EOSSH1

echo ""
echo "📊 ШАГ 2/5: Проверяем БД - donation_history..."
ssh root@$SERVER_IP << 'EOSSH2'
sudo -u postgres psql -d your_donor << 'EOSQL'
SELECT COUNT(*) as total_donations FROM donation_history;
SELECT * FROM donation_history ORDER BY id DESC LIMIT 3;
\q
EOSQL
EOSSH2

echo ""
echo "👥 ШАГ 3/5: Проверяем отклики (должны быть 'confirmed')..."
ssh root@$SERVER_IP << 'EOSSH3'
sudo -u postgres psql -d your_donor << 'EOSQL'
SELECT 
    dr.id, 
    dr.request_id,
    dr.user_id,
    u.full_name,
    dr.status,
    br.status as request_status
FROM donation_responses dr
LEFT JOIN users u ON dr.user_id = u.id
LEFT JOIN blood_requests br ON dr.request_id = br.id
WHERE dr.status = 'confirmed'
ORDER BY dr.id DESC
LIMIT 10;
\q
EOSQL
EOSSH3

echo ""
echo "📋 ШАГ 4/5: Проверяем статус запросов..."
ssh root@$SERVER_IP << 'EOSSH4'
sudo -u postgres psql -d your_donor << 'EOSQL'
SELECT 
    id,
    blood_type,
    urgency,
    status,
    created_at,
    fulfilled_at
FROM blood_requests
WHERE status IN ('active', 'fulfilled')
ORDER BY id DESC
LIMIT 10;
\q
EOSQL
EOSSH4

echo ""
echo "🔍 ШАГ 5/5: Ищем ошибки в логах API..."
ssh root@$SERVER_IP << 'EOSSH5'
echo "Последние строки с ошибками:"
tail -100 /var/log/tvoydonor-api.err.log | grep -i "error\|exception\|traceback" -A 3 | tail -20 || echo "Ошибок не найдено"
echo ""
echo "Последние запросы к /api/blood-requests/ (PUT):"
tail -100 /var/log/tvoydonor-api.err.log | grep "PUT.*blood-requests" || echo "Запросов PUT к blood-requests не найдено"
echo ""
echo "Последние запросы к /api/medical-center/donations (POST):"
tail -100 /var/log/tvoydonor-api.err.log | grep "POST.*donations" || echo "Запросов POST к donations не найдено"
EOSSH5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔬 АНАЛИЗ РЕЗУЛЬТАТОВ:"
echo ""
echo "1️⃣  Если в onclick стоит 'markRequestFulfilled' - файл НЕ ЗАГРУЗИЛСЯ!"
echo "    ➜ Нужно загрузить заново"
echo ""
echo "2️⃣  Если donation_history ПУСТАЯ, но есть confirmed отклики:"
echo "    ➜ Кнопка 'Выполнен' НЕ НАЖИМАЛАСЬ или НЕ РАБОТАЕТ"
echo ""
echo "3️⃣  Если в логах НЕТ запросов к /api/medical-center/donations:"
echo "    ➜ Frontend НЕ вызывает функцию или есть ошибка JS"
echo ""
echo "4️⃣  Если в логах ЕСТЬ ошибки:"
echo "    ➜ Backend падает при записи донации"
echo ""
