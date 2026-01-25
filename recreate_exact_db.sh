#!/bin/bash
# ПОЛНОЕ ВОССОЗДАНИЕ СТРУКТУРЫ БД С ЛОКАЛЬНОГО СЕРВЕРА
# Использование: ssh root@178.172.212.221 "bash -s" < recreate_exact_db.sh

set -e
export PGPASSWORD='u1oFnZALhyfpbtir08nH'

echo "========================================="
echo "🔥 ПОЛНОЕ ВОССОЗДАНИЕ СТРУКТУРЫ БД"
echo "========================================="

psql -U donor_user -h localhost your_donor << 'SQL'

-- ============================================
-- УДАЛЯЕМ ВСЕ ЛИШНИЕ КОЛОНКИ И ПЕРЕСОЗДАЁМ ТАБЛИЦУ BLOOD_REQUESTS
-- ============================================

-- Сохраняем данные
CREATE TEMP TABLE blood_requests_backup AS SELECT * FROM blood_requests;

-- Удаляем старую таблицу
DROP TABLE IF EXISTS blood_requests CASCADE;

-- Создаём ТОЧНО как на локальном
CREATE TABLE blood_requests (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id),
    blood_type VARCHAR(5) NOT NULL,
    urgency VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(20) DEFAULT 'active',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    fulfilled_at TIMESTAMP,
    needed_donors INTEGER,
    current_donors INTEGER DEFAULT 0,
    auto_close BOOLEAN DEFAULT FALSE,
    source VARCHAR(20) DEFAULT 'manual'
);

CREATE INDEX idx_blood_requests_mc ON blood_requests(medical_center_id);
CREATE INDEX idx_blood_requests_source ON blood_requests(source);
CREATE INDEX idx_blood_requests_status ON blood_requests(status);

-- Восстанавливаем данные (только существующие колонки)
INSERT INTO blood_requests (
    id, medical_center_id, blood_type, urgency, status, 
    description, created_at, updated_at, expires_at, 
    fulfilled_at, needed_donors, current_donors, source
)
SELECT 
    id, medical_center_id, blood_type, 
    COALESCE(urgency, 'normal'),
    COALESCE(status, 'active'),
    description, created_at, updated_at, expires_at,
    NULL, -- fulfilled_at
    COALESCE(needed_amount, 1), -- needed_donors
    COALESCE(donor_count, 0), -- current_donors
    COALESCE(source, 'manual')
FROM blood_requests_backup;

-- Обновляем sequence
SELECT setval('blood_requests_id_seq', COALESCE((SELECT MAX(id) FROM blood_requests), 1));

-- ============================================
-- ОБНОВЛЯЕМ ТАБЛИЦУ USERS - ДОБАВЛЯЕМ ТОЛЬКО НУЖНЫЕ КОЛОНКИ
-- ============================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_volume_ml INTEGER DEFAULT 0;

-- Удаляем лишние колонки если есть
ALTER TABLE users DROP COLUMN IF EXISTS donated_count;
ALTER TABLE users DROP COLUMN IF EXISTS last_response_date;

-- ============================================
-- ПЕРЕСОЗДАЁМ DONATION_RESPONSES
-- ============================================
ALTER TABLE donation_responses DROP CONSTRAINT IF EXISTS donation_responses_request_id_fkey;
ALTER TABLE donation_responses 
ADD CONSTRAINT donation_responses_request_id_fkey 
FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE;

-- ============================================
-- СОЗДАЁМ VIEW ДЛЯ СОВМЕСТИМОСТИ
-- ============================================
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

-- ============================================
-- ПРОВЕРКА
-- ============================================
SELECT '✅ BLOOD_REQUESTS структура:' as info;
\d blood_requests

SELECT '✅ USERS дополнительные колонки:' as info;
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('password_hash', 'total_volume_ml');

SELECT '✅ ВСЁ ВОССОЗДАНО!' as status;

SQL

echo ""
echo "♻️  Перезапуск сервисов..."
supervisorctl restart all
sleep 3
supervisorctl status

echo ""
echo "========================================="
echo "✅ СТРУКТУРА БД ПОЛНОСТЬЮ ВОССОЗДАНА!"
echo "========================================="
echo ""
echo "🌐 Откройте https://tvoydonor.by"
echo "🔄 ЖЁСТКО обновите страницу (Ctrl+Shift+R или Cmd+Shift+R)"
echo "✅ ВСЁ ДОЛЖНО РАБОТАТЬ!"
echo ""
