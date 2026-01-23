-- Миграция: Исправление sender_role для автоматических сообщений
-- Дата: 2026-01-24
-- Описание: Клешированные сообщения от медцентра (одобрение/отклонение) 
--           должны иметь sender_role = 'medical_center', а не 'system',
--           чтобы отображаться справа в мессенджере медцентра

BEGIN;

-- Обновляем sender_role для сообщений типа 'notification' и 'invitation' с sender_role = 'system'
-- Эти сообщения идут от медцентра к донору
UPDATE messages
SET sender_role = 'medical_center'
WHERE sender_role = 'system'
  AND message_type IN ('notification', 'invitation')
  AND conversation_id IN (SELECT id FROM conversations);

-- Логирование
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE '✅ Обновлено сообщений: %', updated_count;
END $$;

COMMIT;

-- Проверка результата
SELECT 
    sender_role, 
    message_type, 
    COUNT(*) as count
FROM messages
WHERE message_type IN ('notification', 'invitation', 'system')
GROUP BY sender_role, message_type
ORDER BY sender_role, message_type;
