-- Очистка таблиц пользователей и связанных данных для тестирования

-- Отключаем проверку внешних ключей временно
SET session_replication_role = 'replica';

-- Удаляем историю донаций
DELETE FROM donation_history;

-- Удаляем отклики доноров
DELETE FROM donation_responses;

-- Удаляем сообщения чата
DELETE FROM chat_messages;

-- Удаляем сессии пользователей
DELETE FROM user_sessions;

-- Удаляем коды привязки Telegram
DELETE FROM telegram_link_codes;

-- Удаляем всех пользователей (доноров)
-- Не удаляем пользователей которые являются медцентрами (у них нет blood_type)
DELETE FROM users WHERE blood_type IS NOT NULL;

-- Включаем проверку внешних ключей обратно
SET session_replication_role = 'origin';

-- Показываем результат
SELECT '✅ Таблицы пользователей очищены!' as status;
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE blood_type IS NOT NULL) as donors,
    COUNT(*) FILTER (WHERE blood_type IS NULL) as medcenters
FROM users;
