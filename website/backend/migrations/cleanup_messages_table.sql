-- ============================================
-- МИГРАЦИЯ: Очистка старых колонок в messages
-- Удаление устаревших полей после миграции
-- Дата: 2026-01-23
-- ============================================

-- Шаг 0: Заполняем обязательные поля для старых записей
-- Если sender_role NULL - ставим 'system'
UPDATE messages SET sender_role = 'system' WHERE sender_role IS NULL;

-- Если conversation_id NULL - удаляем старые сообщения без диалога
DELETE FROM messages WHERE conversation_id IS NULL;

-- Если content NULL - копируем из message
UPDATE messages SET content = COALESCE(content, message, 'Сообщение без текста');

-- Шаг 1: Убираем NOT NULL constraint со старых колонок
ALTER TABLE messages ALTER COLUMN message DROP NOT NULL;
ALTER TABLE messages ALTER COLUMN subject DROP NOT NULL;

-- Шаг 2: Удаляем старые колонки (если они не используются)
DO $$ 
BEGIN
    -- Удаляем старые колонки
    ALTER TABLE messages DROP COLUMN IF EXISTS from_user_id;
    ALTER TABLE messages DROP COLUMN IF EXISTS to_user_id;
    ALTER TABLE messages DROP COLUMN IF EXISTS from_medcenter_id;
    ALTER TABLE messages DROP COLUMN IF EXISTS to_medcenter_id;
    ALTER TABLE messages DROP COLUMN IF EXISTS message;
    ALTER TABLE messages DROP COLUMN IF EXISTS subject;
END $$;

-- Шаг 3: Устанавливаем NOT NULL для новых обязательных колонок
ALTER TABLE messages ALTER COLUMN content SET NOT NULL;
ALTER TABLE messages ALTER COLUMN sender_role SET NOT NULL;
ALTER TABLE messages ALTER COLUMN conversation_id SET NOT NULL;
ALTER TABLE messages ALTER COLUMN created_at SET NOT NULL;

-- Шаг 4: Устанавливаем значения по умолчанию
ALTER TABLE messages ALTER COLUMN is_read SET DEFAULT FALSE;
ALTER TABLE messages ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE messages ALTER COLUMN message_type SET DEFAULT 'text';

COMMENT ON TABLE messages IS 'Система сообщений - новая схема без старых полей';
