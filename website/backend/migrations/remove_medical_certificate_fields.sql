-- Миграция: Удаление полей медицинской справки донора
-- Дата: 2026-01-23
-- Причина: Функционал медицинских справок больше не используется

-- Удаляем индекс
DROP INDEX IF EXISTS idx_users_medical_certificate;

-- Удаляем поля
ALTER TABLE users 
DROP COLUMN IF EXISTS medical_certificate_path,
DROP COLUMN IF EXISTS medical_certificate_uploaded_at;
