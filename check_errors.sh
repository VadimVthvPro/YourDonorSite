#!/bin/bash
# Быстрая диагностика ошибок на сервере
# Использование: ssh root@178.172.212.221 "bash -s" < check_errors.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔍 ДИАГНОСТИКА ОШИБОК"
echo "========================================="

echo ""
echo "1️⃣ Проверка таблицы blood_requests:"
psql -U donor_user -h localhost your_donor << 'SQL'
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'blood_requests' AND table_type = 'BASE TABLE'
) as blood_requests_exists;

SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'blood_requests' 
AND column_name IN ('source', 'donor_count', 'expires_at')
ORDER BY column_name;
SQL

echo ""
echo "2️⃣ Последние ошибки Flask API:"
tail -50 /var/log/tvoydonor-api.err.log | grep -B 3 "does not exist\|Error" | tail -30

echo ""
echo "3️⃣ Статус сервисов:"
supervisorctl status

echo ""
echo "4️⃣ Тест API blood-requests:"
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:5001/api/medcenter/10/blood-requests 2>&1 | head -100

echo ""
echo "========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "========================================="
