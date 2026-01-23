-- Миграция: Добавление полей для медицинской справки донора
-- Дата: 2026-01-23

-- Добавляем поля для хранения информации о медицинской справке
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS medical_certificate_path VARCHAR(255),
ADD COLUMN IF NOT EXISTS medical_certificate_uploaded_at TIMESTAMP;

-- Создаём индекс для быстрого поиска доноров с загруженными справками
CREATE INDEX IF NOT EXISTS idx_users_medical_certificate 
ON users(medical_certificate_path) 
WHERE medical_certificate_path IS NOT NULL;

-- Комментарии
COMMENT ON COLUMN users.medical_certificate_path IS 'Путь к файлу медицинской справки (относительный)';
COMMENT ON COLUMN users.medical_certificate_uploaded_at IS 'Дата и время загрузки медицинской справки';
