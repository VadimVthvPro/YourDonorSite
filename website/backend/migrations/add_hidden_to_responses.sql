-- Добавление поля hidden для скрытия откликов на фронтенде
ALTER TABLE donation_responses ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN donation_responses.hidden IS 'Скрыт ли отклик на фронтенде (не удалён из БД)';

-- Создаём индекс для быстрой фильтрации
CREATE INDEX IF NOT EXISTS idx_donation_responses_hidden ON donation_responses(hidden);
