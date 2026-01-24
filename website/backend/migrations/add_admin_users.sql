-- ============================================
-- Миграция: Таблица администраторов
-- ============================================

-- Создаём таблицу для хранения админов
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    role VARCHAR(50) DEFAULT 'super_admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для быстрого поиска по username
CREATE INDEX IF NOT EXISTS idx_admin_username ON admin_users(telegram_username);

SELECT 'Таблица admin_users создана!' as message;
