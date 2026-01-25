#!/bin/bash
# ПОЛНОЕ ИСПРАВЛЕНИЕ ВСЕХ КОЛОНОК РАЗОМ
# Использование: ssh root@178.172.212.221 "bash -s" < fix_all_columns_now.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔧 ПОЛНОЕ ИСПРАВЛЕНИЕ ВСЕХ КОЛОНОК"
echo "========================================="

psql -U donor_user -h localhost your_donor << 'SQL'

-- ============================================
-- BLOOD_REQUESTS - ВСЕ НЕДОСТАЮЩИЕ КОЛОНКИ
-- ============================================
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'web';
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS donor_count INTEGER DEFAULT 0;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS needed_donors INTEGER DEFAULT 1;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS fulfilled_at TIMESTAMP;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS current_donors INTEGER DEFAULT 0;

-- ============================================
-- USERS - ВСЕ НЕДОСТАЮЩИЕ КОЛОНКИ
-- ============================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS donated_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_response_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_volume_ml INTEGER DEFAULT 0;

-- ============================================
-- MESSAGES - ВСЕ НЕДОСТАЮЩИЕ КОЛОНКИ
-- ============================================
ALTER TABLE messages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- ============================================
-- DONATION_HISTORY - ВСЕ НЕДОСТАЮЩИЕ КОЛОНКИ
-- ============================================
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS donor_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS medical_center_id INTEGER REFERENCES medical_centers(id);
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10);

-- Копируем данные
UPDATE donation_history SET donor_id = user_id WHERE donor_id IS NULL;
UPDATE donation_history SET medical_center_id = blood_center_id WHERE medical_center_id IS NULL;

-- ============================================
-- CONVERSATIONS - ВСЕ НЕДОСТАЮЩИЕ КОЛОНКИ
-- ============================================
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS donor_unread_count INTEGER DEFAULT 0;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS medcenter_unread_count INTEGER DEFAULT 0;

-- ============================================
-- ОБНОВЛЕНИЕ VIEW
-- ============================================
DROP VIEW IF EXISTS donation_requests CASCADE;
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

-- ============================================
-- ПРОВЕРКА РЕЗУЛЬТАТА
-- ============================================
SELECT 'BLOOD_REQUESTS колонки:' as info;
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'blood_requests' 
AND column_name IN ('source', 'donor_count', 'expires_at', 'needed_donors', 'fulfilled_at', 'current_donors')
ORDER BY column_name;

SELECT 'USERS колонки:' as info;
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('password_hash', 'donated_count', 'last_response_date', 'total_volume_ml')
ORDER BY column_name;

SELECT '✅ ВСЕ КОЛОНКИ ДОБАВЛЕНЫ!' as status;

SQL

echo "✅ Все колонки успешно добавлены!"

# Перезапуск сервисов
echo ""
echo "♻️  Перезапуск сервисов..."
supervisorctl restart all
sleep 3

echo ""
echo "📊 Статус сервисов:"
supervisorctl status

echo ""
echo "========================================="
echo "✅ ПОЛНОЕ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo ""
echo "🌐 Откройте https://tvoydonor.by"
echo "🔄 Обновите страницу (Ctrl+R)"
echo "✅ Попробуйте создать запрос крови"
echo ""
