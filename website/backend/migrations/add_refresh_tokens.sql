-- ============================================
-- Миграция: Добавление поддержки Refresh Token
-- Версия: 2.0.0
-- Дата: 2026-01-27
-- ============================================

-- 1. Добавляем новые столбцы в user_sessions
-- (если они ещё не существуют)

-- Проверяем и добавляем refresh_token_hash
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_sessions' AND column_name = 'refresh_token_hash'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN refresh_token_hash VARCHAR(64);
        CREATE INDEX idx_sess_refresh_hash ON user_sessions(refresh_token_hash);
    END IF;
END $$;

-- Добавляем device_info
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_sessions' AND column_name = 'device_info'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN device_info VARCHAR(255);
    END IF;
END $$;

-- Добавляем ip_address
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_sessions' AND column_name = 'ip_address'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN ip_address VARCHAR(45);
    END IF;
END $$;

-- Добавляем platform
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_sessions' AND column_name = 'platform'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN platform VARCHAR(20) DEFAULT 'web';
    END IF;
END $$;

-- Добавляем last_used_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_sessions' AND column_name = 'last_used_at'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- 2. Миграция существующих сессий
-- Старые session_token перемещаем в refresh_token_hash (хэшируем)
UPDATE user_sessions 
SET refresh_token_hash = encode(sha256(session_token::bytea), 'hex'),
    last_used_at = COALESCE(last_used_at, created_at)
WHERE refresh_token_hash IS NULL 
  AND session_token IS NOT NULL;

-- 3. Обновляем expires_at для активных сессий на 30 дней
UPDATE user_sessions 
SET expires_at = NOW() + INTERVAL '30 days'
WHERE is_active = TRUE 
  AND expires_at < NOW() + INTERVAL '30 days';

-- 4. Создаём индексы для производительности
CREATE INDEX IF NOT EXISTS idx_sess_user_active ON user_sessions(user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sess_mc_active ON user_sessions(medical_center_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sess_expires ON user_sessions(expires_at);

-- 5. Очистка старых неактивных сессий
DELETE FROM user_sessions 
WHERE is_active = FALSE 
   OR expires_at < NOW() - INTERVAL '7 days';

-- 6. Вывод статистики
DO $$ 
DECLARE
    total_sessions INTEGER;
    active_sessions INTEGER;
    donor_sessions INTEGER;
    mc_sessions INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_sessions FROM user_sessions;
    SELECT COUNT(*) INTO active_sessions FROM user_sessions WHERE is_active = TRUE AND expires_at > NOW();
    SELECT COUNT(*) INTO donor_sessions FROM user_sessions WHERE user_type = 'donor' AND is_active = TRUE;
    SELECT COUNT(*) INTO mc_sessions FROM user_sessions WHERE user_type = 'medcenter' AND is_active = TRUE;
    
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Миграция Refresh Token завершена!';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Всего сессий: %', total_sessions;
    RAISE NOTICE 'Активных сессий: %', active_sessions;
    RAISE NOTICE '  - Доноры: %', donor_sessions;
    RAISE NOTICE '  - Медцентры: %', mc_sessions;
    RAISE NOTICE '============================================';
END $$;
