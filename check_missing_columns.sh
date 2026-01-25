#!/bin/bash
# Проверка недостающих колонок для /responses эндпоинта
# Использование: ssh root@178.172.212.221 "bash -s" < check_missing_columns.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔍 ПРОВЕРКА НЕДОСТАЮЩИХ КОЛОНОК"
echo "========================================="

echo ""
echo "1️⃣ Проверка колонки 'hidden' в donation_responses:"
psql -U donor_user -h localhost your_donor << 'SQL'
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'donation_responses' 
AND column_name = 'hidden';
SQL

echo ""
echo "2️⃣ Проверка колонки 'total_volume_ml' в users:"
psql -U donor_user -h localhost your_donor << 'SQL'
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'total_volume_ml';
SQL

echo ""
echo "3️⃣ Добавление недостающих колонок:"
psql -U donor_user -h localhost your_donor << 'SQL'

-- Добавляем hidden в donation_responses
ALTER TABLE donation_responses ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;

-- Проверка
\d donation_responses

SQL

echo ""
echo "♻️  Перезапуск сервисов..."
supervisorctl restart all
sleep 2
supervisorctl status

echo ""
echo "========================================="
echo "✅ КОЛОНКИ ДОБАВЛЕНЫ!"
echo "========================================="
