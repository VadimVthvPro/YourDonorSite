#!/bin/bash
# Добавление недостающей колонки needed_donors
# Использование: ssh root@178.172.212.221 "bash -s" < add_needed_donors.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔧 ДОБАВЛЕНИЕ КОЛОНКИ needed_donors"
echo "========================================="

psql -U donor_user -h localhost your_donor << 'SQL'

-- Добавляем needed_donors
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS needed_donors INTEGER DEFAULT 1;

-- Проверяем
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'blood_requests' 
AND column_name IN ('needed_donors', 'needed_amount')
ORDER BY column_name;

-- Обновляем VIEW
DROP VIEW IF EXISTS donation_requests CASCADE;
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

SQL

echo "✅ Колонка needed_donors добавлена"

# Перезапуск
supervisorctl restart all
sleep 2
supervisorctl status

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo "Обновите браузер и проверьте работу!"
