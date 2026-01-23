-- ============================================
-- МИГРАЦИЯ: Обновление системы сообщений
-- Преобразование старой структуры в новую
-- Дата: 2026-01-23
-- ============================================

-- Шаг 1: Создаём таблицу conversations (новая)
-- Уже создана из предыдущей миграции

-- Шаг 2: Добавляем новые поля в существующую таблицу messages
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS sender_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS sender_role VARCHAR(20) CHECK (sender_role IN ('donor', 'medical_center', 'system')),
ADD COLUMN IF NOT EXISTS content TEXT,
ADD COLUMN IF NOT EXISTS message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'notification', 'invitation', 'system')),
ADD COLUMN IF NOT EXISTS metadata JSONB,
ADD COLUMN IF NOT EXISTS read_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Шаг 3: Мигрируем данные из старых полей в новые
-- Копируем content из message
UPDATE messages SET content = message WHERE content IS NULL;

-- Определяем sender_id и sender_role
UPDATE messages 
SET 
    sender_id = from_user_id,
    sender_role = 'donor'
WHERE from_user_id IS NOT NULL AND sender_id IS NULL;

UPDATE messages 
SET 
    sender_id = NULL,  -- medical_centers не связаны с users
    sender_role = 'medical_center'
WHERE from_medcenter_id IS NOT NULL AND sender_role IS NULL;

-- Шаг 4: Создаём диалоги на основе существующих сообщений
INSERT INTO conversations (donor_id, medical_center_id, created_at, last_message_at)
SELECT DISTINCT 
    COALESCE(from_user_id, to_user_id) as donor_id,
    COALESCE(from_medcenter_id, to_medcenter_id) as medical_center_id,
    MIN(created_at) as created_at,
    MAX(created_at) as last_message_at
FROM messages
WHERE (from_user_id IS NOT NULL OR to_user_id IS NOT NULL)
  AND (from_medcenter_id IS NOT NULL OR to_medcenter_id IS NOT NULL)
GROUP BY donor_id, medical_center_id
ON CONFLICT (donor_id, medical_center_id) DO NOTHING;

-- Шаг 5: Связываем существующие сообщения с диалогами
UPDATE messages m
SET conversation_id = c.id
FROM conversations c
WHERE conversation_id IS NULL
  AND (
    (m.from_user_id = c.donor_id AND m.to_medcenter_id = c.medical_center_id) OR
    (m.to_user_id = c.donor_id AND m.from_medcenter_id = c.medical_center_id)
  );

-- Шаг 6: Обновляем read_at для прочитанных сообщений
UPDATE messages 
SET read_at = created_at 
WHERE is_read = TRUE AND read_at IS NULL;

-- Шаг 7: Обновляем счётчики непрочитанных в conversations
UPDATE conversations c
SET 
    donor_unread_count = (
        SELECT COUNT(*) 
        FROM messages m 
        WHERE m.conversation_id = c.id 
          AND m.is_read = FALSE 
          AND m.sender_role IN ('medical_center', 'system')
          AND m.deleted_at IS NULL
    ),
    medcenter_unread_count = (
        SELECT COUNT(*) 
        FROM messages m 
        WHERE m.conversation_id = c.id 
          AND m.is_read = FALSE 
          AND m.sender_role = 'donor'
          AND m.deleted_at IS NULL
    ),
    last_message_preview = (
        SELECT LEFT(content, 100)
        FROM messages m
        WHERE m.conversation_id = c.id
          AND m.deleted_at IS NULL
        ORDER BY m.created_at DESC
        LIMIT 1
    );

-- Шаг 8: Создаём недостающие индексы
CREATE INDEX IF NOT EXISTS idx_messages_conversation_new 
ON messages(conversation_id, created_at DESC) 
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_messages_unread_new 
ON messages(conversation_id, is_read) 
WHERE is_read = FALSE AND deleted_at IS NULL;

-- Шаг 9: Удаляем триггер reset_unread, если он уже есть
DROP TRIGGER IF EXISTS trigger_reset_unread ON messages;

-- Шаг 10: Создаём триггер для обновления диалога при новом сообщении
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.conversation_id IS NOT NULL THEN
        UPDATE conversations
        SET 
            last_message_at = NEW.created_at,
            last_message_preview = LEFT(NEW.content, 100),
            updated_at = NOW(),
            donor_unread_count = CASE 
                WHEN NEW.sender_role IN ('medical_center', 'system')
                THEN donor_unread_count + 1 
                ELSE donor_unread_count 
            END,
            medcenter_unread_count = CASE 
                WHEN NEW.sender_role = 'donor' 
                THEN medcenter_unread_count + 1 
                ELSE medcenter_unread_count 
            END
        WHERE id = NEW.conversation_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation ON messages;
CREATE TRIGGER trigger_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    WHEN (NEW.deleted_at IS NULL AND NEW.conversation_id IS NOT NULL)
    EXECUTE FUNCTION update_conversation_on_message();

-- Шаг 11: Создаём триггер для уменьшения счётчика при прочтении
CREATE OR REPLACE FUNCTION reset_unread_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_read = TRUE AND OLD.is_read = FALSE AND NEW.conversation_id IS NOT NULL THEN
        UPDATE conversations
        SET 
            donor_unread_count = CASE 
                WHEN NEW.sender_role IN ('medical_center', 'system')
                THEN GREATEST(donor_unread_count - 1, 0)
                ELSE donor_unread_count
            END,
            medcenter_unread_count = CASE 
                WHEN NEW.sender_role = 'donor'
                THEN GREATEST(medcenter_unread_count - 1, 0)
                ELSE medcenter_unread_count
            END
        WHERE id = NEW.conversation_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_reset_unread
    AFTER UPDATE OF is_read ON messages
    FOR EACH ROW
    EXECUTE FUNCTION reset_unread_count();

-- ============================================
-- Комментарии
-- ============================================

COMMENT ON COLUMN messages.conversation_id IS 'ID диалога, к которому относится сообщение';
COMMENT ON COLUMN messages.sender_id IS 'ID отправителя (из таблицы users). NULL для системных сообщений';
COMMENT ON COLUMN messages.sender_role IS 'Роль отправителя: donor, medical_center, system';
COMMENT ON COLUMN messages.content IS 'Текст сообщения';
COMMENT ON COLUMN messages.message_type IS 'Тип сообщения: text, notification, invitation, system';
COMMENT ON COLUMN messages.metadata IS 'JSON с дополнительными данными (кнопки, дата донации и т.д.)';
COMMENT ON COLUMN messages.deleted_at IS 'Мягкое удаление - сообщение скрыто';

-- ============================================
-- Таблица шаблонов (если ещё не создана)
-- ============================================

CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    variables TEXT[],
    is_predefined BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_predefined CHECK (
        (is_predefined = TRUE AND medical_center_id IS NULL) OR 
        (is_predefined = FALSE AND medical_center_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_templates_medcenter ON message_templates(medical_center_id);

-- Вставка предустановленных шаблонов
INSERT INTO message_templates (name, content, variables, is_predefined) 
SELECT * FROM (VALUES
    ('Приглашение на донацию', 
     'Здравствуйте, {имя}! Приглашаем вас на донацию {дата} в {время}. Пожалуйста, подтвердите участие.',
     ARRAY['{имя}', '{дата}', '{время}']::TEXT[],
     TRUE),
    
    ('Напоминание о донации',
     'Напоминаем о вашей записи на донацию {дата} в {время}. Ждём вас в {центр}!',
     ARRAY['{дата}', '{время}', '{центр}']::TEXT[],
     TRUE),
    
    ('Благодарность после донации',
     'Спасибо за вашу донацию! Вы помогли спасти жизни. Ждём вас снова через 60 дней.',
     ARRAY[]::TEXT[],
     TRUE),
    
    ('Срочный запрос крови',
     'Срочно нужна кровь группы {группа}! Можете ли вы прийти сегодня или завтра? Это очень важно!',
     ARRAY['{группа}']::TEXT[],
     TRUE),
    
    ('Изменение даты донации',
     'Здравствуйте, {имя}! К сожалению, нам нужно перенести вашу донацию. Новая дата: {дата} в {время}. Подтвердите, пожалуйста.',
     ARRAY['{имя}', '{дата}', '{время}']::TEXT[],
     TRUE)
) AS t(name, content, variables, is_predefined)
WHERE NOT EXISTS (
    SELECT 1 FROM message_templates WHERE is_predefined = TRUE
);

COMMENT ON TABLE message_templates IS 'Шаблоны сообщений для медицинских центров';
