-- ============================================
-- СИСТЕМА СООБЩЕНИЙ: Полная схема БД
-- Дата: 2026-01-23
-- ============================================

-- Таблица диалогов между донорами и медцентрами
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP,
    last_message_preview VARCHAR(100),
    donor_unread_count INTEGER DEFAULT 0,
    medcenter_unread_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    
    -- Один диалог между донором и медцентром
    UNIQUE(donor_id, medical_center_id)
);

-- Индексы для быстрого поиска
CREATE INDEX idx_conversations_donor ON conversations(donor_id, status, last_message_at DESC);
CREATE INDEX idx_conversations_medcenter ON conversations(medical_center_id, status, last_message_at DESC);
CREATE INDEX idx_conversations_unread_donor ON conversations(donor_id) WHERE donor_unread_count > 0;
CREATE INDEX idx_conversations_unread_medcenter ON conversations(medical_center_id) WHERE medcenter_unread_count > 0;

-- Комментарии
COMMENT ON TABLE conversations IS 'Диалоги между донорами и медицинскими центрами';
COMMENT ON COLUMN conversations.last_message_preview IS 'Превью последнего сообщения для списка диалогов';
COMMENT ON COLUMN conversations.donor_unread_count IS 'Количество непрочитанных сообщений для донора';
COMMENT ON COLUMN conversations.medcenter_unread_count IS 'Количество непрочитанных сообщений для медцентра';

-- ============================================

-- Таблица сообщений
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    sender_role VARCHAR(20) NOT NULL CHECK (sender_role IN ('donor', 'medical_center', 'system')),
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'notification', 'invitation', 'system')),
    metadata JSONB, -- Дополнительные данные: кнопки, ссылки, дата донации и т.д.
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    edited_at TIMESTAMP,
    deleted_at TIMESTAMP, -- Soft delete
    
    -- Проверка: системные сообщения не имеют sender_id
    CONSTRAINT check_system_sender CHECK (
        (sender_role = 'system' AND sender_id IS NULL) OR 
        (sender_role != 'system' AND sender_id IS NOT NULL)
    )
);

-- Индексы для быстрой работы
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_unread ON messages(conversation_id, is_read) WHERE is_read = FALSE AND deleted_at IS NULL;
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- Комментарии
COMMENT ON TABLE messages IS 'Сообщения в диалогах';
COMMENT ON COLUMN messages.sender_role IS 'Роль отправителя: donor, medical_center, system';
COMMENT ON COLUMN messages.message_type IS 'Тип: text (обычное), notification (уведомление), invitation (приглашение), system (системное)';
COMMENT ON COLUMN messages.metadata IS 'JSON с доп. данными: кнопки, дата донации, причина отказа и т.д.';
COMMENT ON COLUMN messages.deleted_at IS 'Мягкое удаление - сообщение скрыто, но не удалено из БД';

-- ============================================

-- Таблица шаблонов сообщений (для медцентров)
CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    variables TEXT[], -- Массив переменных: {имя}, {дата}, {время} и т.д.
    is_predefined BOOLEAN DEFAULT FALSE, -- Предустановленный системный шаблон
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Если шаблон общий (для всех медцентров), medical_center_id = NULL
    CONSTRAINT check_predefined CHECK (
        (is_predefined = TRUE AND medical_center_id IS NULL) OR 
        (is_predefined = FALSE AND medical_center_id IS NOT NULL)
    )
);

CREATE INDEX idx_templates_medcenter ON message_templates(medical_center_id);

COMMENT ON TABLE message_templates IS 'Шаблоны сообщений для медицинских центров';
COMMENT ON COLUMN message_templates.is_predefined IS 'TRUE для системных шаблонов, доступных всем';
COMMENT ON COLUMN message_templates.variables IS 'Список переменных для подстановки';

-- ============================================

-- Вставка предустановленных шаблонов
INSERT INTO message_templates (name, content, variables, is_predefined) VALUES
('Приглашение на донацию', 
 'Здравствуйте, {имя}! Приглашаем вас на донацию {дата} в {время}. Пожалуйста, подтвердите участие.',
 ARRAY['{имя}', '{дата}', '{время}'],
 TRUE),

('Напоминание о донации',
 'Напоминаем о вашей записи на донацию {дата} в {время}. Ждём вас в {центр}!',
 ARRAY['{дата}', '{время}', '{центр}'],
 TRUE),

('Благодарность после донации',
 'Спасибо за вашу донацию! Вы помогли спасти жизни. Ждём вас снова через 60 дней.',
 ARRAY[],
 TRUE),

('Срочный запрос крови',
 'Срочно нужна кровь группы {группа}! Можете ли вы прийти сегодня или завтра? Это очень важно!',
 ARRAY['{группа}'],
 TRUE),

('Изменение даты донации',
 'Здравствуйте, {имя}! К сожалению, нам нужно перенести вашу донацию. Новая дата: {дата} в {время}. Подтвердите, пожалуйста.',
 ARRAY['{имя}', '{дата}', '{время}'],
 TRUE);

-- ============================================

-- Функция для обновления счётчика непрочитанных
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем диалог при добавлении нового сообщения
    UPDATE conversations
    SET 
        last_message_at = NEW.created_at,
        last_message_preview = LEFT(NEW.content, 100),
        updated_at = NOW(),
        -- Увеличиваем счётчик непрочитанных для получателя
        donor_unread_count = CASE 
            WHEN NEW.sender_role = 'medical_center' OR NEW.sender_role = 'system' 
            THEN donor_unread_count + 1 
            ELSE donor_unread_count 
        END,
        medcenter_unread_count = CASE 
            WHEN NEW.sender_role = 'donor' 
            THEN medcenter_unread_count + 1 
            ELSE medcenter_unread_count 
        END
    WHERE id = NEW.conversation_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер на добавление сообщения
DROP TRIGGER IF EXISTS trigger_update_conversation ON messages;
CREATE TRIGGER trigger_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    WHEN (NEW.deleted_at IS NULL)
    EXECUTE FUNCTION update_conversation_on_message();

-- ============================================

-- Функция для сброса счётчика при прочтении
CREATE OR REPLACE FUNCTION reset_unread_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_read = TRUE AND OLD.is_read = FALSE THEN
        -- Определяем, кто прочитал (по sender_role отправителя)
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

-- Триггер на прочтение сообщения
DROP TRIGGER IF EXISTS trigger_reset_unread ON messages;
CREATE TRIGGER trigger_reset_unread
    AFTER UPDATE OF is_read ON messages
    FOR EACH ROW
    EXECUTE FUNCTION reset_unread_count();

-- ============================================

COMMENT ON FUNCTION update_conversation_on_message IS 'Автоматически обновляет диалог при новом сообщении';
COMMENT ON FUNCTION reset_unread_count IS 'Уменьшает счётчик непрочитанных при прочтении';
