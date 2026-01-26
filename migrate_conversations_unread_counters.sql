-- ============================================
-- МИГРАЦИЯ: Добавление счётчиков непрочитанных сообщений
-- ============================================

-- Добавляем колонки для счётчиков непрочитанных
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS donor_unread_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS medcenter_unread_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS donor_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- Копируем user_id в donor_id (если еще не сделано)
UPDATE conversations
SET donor_id = user_id
WHERE donor_id IS NULL;

-- Создаем индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_conv_donor ON conversations(donor_id);

-- Пересчитываем непрочитанные для доноров
UPDATE conversations c
SET donor_unread_count = (
    SELECT COUNT(*)
    FROM chat_messages cm
    WHERE cm.donor_id = c.donor_id
      AND cm.medcenter_id = c.medical_center_id
      AND cm.sender_type = 'medcenter'
      AND cm.is_read = FALSE
);

-- Пересчитываем непрочитанные для медцентров
UPDATE conversations c
SET medcenter_unread_count = (
    SELECT COUNT(*)
    FROM chat_messages cm
    WHERE cm.donor_id = c.donor_id
      AND cm.medcenter_id = c.medical_center_id
      AND cm.sender_type = 'donor'
      AND cm.is_read = FALSE
);

-- Проверяем результат
SELECT 
    'Обновлено диалогов' as result,
    COUNT(*) as total,
    SUM(donor_unread_count) as total_donor_unread,
    SUM(medcenter_unread_count) as total_medcenter_unread
FROM conversations;
