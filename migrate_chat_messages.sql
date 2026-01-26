-- ============================================
-- Миграция: Обновление схемы chat_messages
-- ============================================
-- Дата: 2026-01-26
-- Цель: Привести схему БД в соответствие с backend/frontend
-- 
-- Проблема: Backend и frontend используют sender_type, message_text, message_type
-- но в БД есть sender_role, message (без message_type)
-- ============================================

\echo '🔄 Начинаем миграцию chat_messages...'

-- Резервная копия (опционально, для отката)
CREATE TABLE IF NOT EXISTS chat_messages_backup AS SELECT * FROM chat_messages;

\echo '✅ Резервная копия создана: chat_messages_backup'

-- 1. Переименовать sender_role → sender_type
\echo '1️⃣ Переименовываем sender_role → sender_type...'
ALTER TABLE chat_messages RENAME COLUMN sender_role TO sender_type;

-- 2. Переименовать message → message_text
\echo '2️⃣ Переименовываем message → message_text...'
ALTER TABLE chat_messages RENAME COLUMN message TO message_text;

-- 3. Добавить колонку message_type (по умолчанию 'text')
\echo '3️⃣ Добавляем колонку message_type...'
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(50) DEFAULT 'text';

-- 4. Обновить message_type для существующих сообщений (если они есть)
-- Пытаемся определить тип по содержимому
\echo '4️⃣ Обновляем message_type для существующих сообщений...'
UPDATE chat_messages 
SET message_type = CASE 
    WHEN message_text LIKE '%Приглашение на донацию%' OR message_text LIKE '%одобрена%' THEN 'invitation'
    WHEN message_text LIKE '%Уведомление%' THEN 'notification'
    ELSE 'text'
END
WHERE message_type = 'text';  -- Только для тех, у кого дефолтное значение

-- 5. Добавить дополнительные колонки для совместимости с современными требованиями
\echo '5️⃣ Добавляем дополнительные колонки...'
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS read_at TIMESTAMP;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- 6. Обновить существующие is_read флаги в read_at timestamps
\echo '6️⃣ Мигрируем is_read → read_at...'
UPDATE chat_messages 
SET read_at = created_at 
WHERE is_read = TRUE AND read_at IS NULL;

-- 7. Создать индекс на message_type для быстрого поиска по типу сообщений
\echo '7️⃣ Создаём индексы...'
CREATE INDEX IF NOT EXISTS idx_chat_message_type ON chat_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_chat_deleted ON chat_messages(deleted_at) WHERE deleted_at IS NOT NULL;

-- 8. Вывод итоговой схемы для проверки
\echo '📊 Финальная схема таблицы chat_messages:'
\d chat_messages

-- 9. Статистика
\echo '📈 Статистика миграции:'
SELECT 
    COUNT(*) as total_messages,
    COUNT(*) FILTER (WHERE message_type = 'text') as text_messages,
    COUNT(*) FILTER (WHERE message_type = 'invitation') as invitations,
    COUNT(*) FILTER (WHERE message_type = 'notification') as notifications,
    COUNT(*) FILTER (WHERE sender_type = 'donor') as from_donors,
    COUNT(*) FILTER (WHERE sender_type = 'medcenter') as from_medcenters,
    COUNT(*) FILTER (WHERE sender_type = 'system') as system_messages
FROM chat_messages;

\echo '✅ Миграция завершена успешно!'
\echo ''
\echo '⚠️  ВАЖНО: Если нужно откатить изменения, выполните:'
\echo '   DROP TABLE chat_messages;'
\echo '   ALTER TABLE chat_messages_backup RENAME TO chat_messages;'
