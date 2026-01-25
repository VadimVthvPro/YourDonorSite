#!/bin/bash
# Исправление таблицы blood_requests на сервере
# Выполните: ssh root@178.172.212.221 "bash -s" < fix_blood_requests_table.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔧 ИСПРАВЛЕНИЕ ТАБЛИЦЫ BLOOD_REQUESTS"
echo "========================================="

# Удаляем VIEW
psql -U donor_user -h localhost your_donor << 'SQL'
DROP VIEW IF EXISTS blood_requests CASCADE;
SQL

echo "✅ VIEW blood_requests удалён"

# Переименовываем donation_requests в blood_requests
psql -U donor_user -h localhost your_donor << 'SQL'
ALTER TABLE donation_requests RENAME TO blood_requests;
SQL

echo "✅ Таблица donation_requests переименована в blood_requests"

# Проверяем структуру
psql -U donor_user -h localhost your_donor << 'SQL'
\dt blood_requests
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'blood_requests' AND column_name IN ('source', 'donor_count', 'expires_at');
SQL

# Перезапуск
supervisorctl restart all
sleep 2
supervisorctl status

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo "Обновите браузер и проверьте работу!"
