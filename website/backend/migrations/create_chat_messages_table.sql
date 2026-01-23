-- Миграция: Создание таблицы для системы переписки
-- Дата: 2026-01-23
-- Описание: Таблица chat_messages для переписки между донорами и медцентрами

-- Создаём таблицу сообщений
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    donor_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medcenter_id INT NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('donor', 'medcenter')),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chat_messages_valid_sender CHECK (
        (sender_type = 'donor' AND donor_id IS NOT NULL) OR
        (sender_type = 'medcenter' AND medcenter_id IS NOT NULL)
    )
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_chat_messages_donor 
ON chat_messages(donor_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_medcenter 
ON chat_messages(medcenter_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_created 
ON chat_messages(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_unread 
ON chat_messages(is_read) 
WHERE is_read = FALSE;

-- Комментарии к полям
COMMENT ON TABLE chat_messages IS 'Сообщения в переписке между донорами и медцентрами';
COMMENT ON COLUMN chat_messages.donor_id IS 'ID донора (получатель или отправитель)';
COMMENT ON COLUMN chat_messages.medcenter_id IS 'ID медцентра (получатель или отправитель)';
COMMENT ON COLUMN chat_messages.sender_type IS 'Тип отправителя: donor или medcenter';
COMMENT ON COLUMN chat_messages.message IS 'Текст сообщения';
COMMENT ON COLUMN chat_messages.is_read IS 'Прочитано ли сообщение получателем';
COMMENT ON COLUMN chat_messages.created_at IS 'Дата и время отправки сообщения';
