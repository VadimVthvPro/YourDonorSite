-- Добавление полей статистики донаций в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_donations INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_donation_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_volume_ml INT DEFAULT 0;

-- Обновляем существующие записи
UPDATE users SET total_donations = 0 WHERE total_donations IS NULL;
UPDATE users SET total_volume_ml = 0 WHERE total_volume_ml IS NULL;

COMMENT ON COLUMN users.total_donations IS 'Общее количество донаций';
COMMENT ON COLUMN users.last_donation_date IS 'Дата последней донации';
COMMENT ON COLUMN users.total_volume_ml IS 'Общий объём сданной крови (мл)';
