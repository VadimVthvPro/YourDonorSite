-- Миграция: Добавление учёта количества доноров

-- Добавить поля в таблицу blood_requests
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS needed_donors INT DEFAULT NULL;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS current_donors INT DEFAULT 0;
ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS auto_close BOOLEAN DEFAULT FALSE;

-- Комментарии
COMMENT ON COLUMN blood_requests.needed_donors IS 'Количество нужных доноров (NULL = без ограничения)';
COMMENT ON COLUMN blood_requests.current_donors IS 'Текущее количество откликнувшихся';
COMMENT ON COLUMN blood_requests.auto_close IS 'Автоматически закрыть при достижении needed_donors';

-- Обновить существующие записи
UPDATE blood_requests SET needed_donors = NULL, current_donors = 0, auto_close = FALSE WHERE needed_donors IS NULL;
