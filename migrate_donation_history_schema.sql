-- ============================================
-- МИГРАЦИЯ: donation_history
-- Цель: Привести схему БД в соответствие с backend кодом
-- ============================================

\echo '🔄 Начинаем миграцию donation_history...'

-- Создаём резервную копию
CREATE TABLE IF NOT EXISTS donation_history_backup_20260126 AS 
SELECT * FROM donation_history;

\echo '✅ Резервная копия создана: donation_history_backup_20260126'

-- 1️⃣ Переименовать user_id → donor_id
\echo '1️⃣ Переименовываем user_id → donor_id...'
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='donation_history' AND column_name='user_id'
    ) THEN
        ALTER TABLE donation_history RENAME COLUMN user_id TO donor_id;
        RAISE NOTICE 'Колонка user_id переименована в donor_id';
    ELSE
        RAISE NOTICE 'Колонка user_id уже не существует (возможно, уже donor_id)';
    END IF;
END $$;

-- 2️⃣ Переименовать blood_center_id → medical_center_id
\echo '2️⃣ Переименовываем blood_center_id → medical_center_id...'
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='donation_history' AND column_name='blood_center_id'
    ) THEN
        ALTER TABLE donation_history RENAME COLUMN blood_center_id TO medical_center_id;
        RAISE NOTICE 'Колонка blood_center_id переименована в medical_center_id';
    ELSE
        RAISE NOTICE 'Колонка blood_center_id уже не существует (возможно, уже medical_center_id)';
    END IF;
END $$;

-- 3️⃣ Добавить колонку blood_type
\echo '3️⃣ Добавляем колонку blood_type...'
ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10);

-- 4️⃣ Добавить колонку status
\echo '4️⃣ Добавляем колонку status...'
ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed';

-- 5️⃣ Добавить колонку response_id
\echo '5️⃣ Добавляем колонку response_id...'
ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS response_id INTEGER REFERENCES donation_responses(id) ON DELETE SET NULL;

-- 6️⃣ Убедиться что donation_type существует
\echo '6️⃣ Проверяем колонку donation_type...'
ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS donation_type VARCHAR(50) DEFAULT 'blood';

-- 7️⃣ Обновить статус для старых записей
\echo '7️⃣ Обновляем статус для существующих записей...'
UPDATE donation_history 
SET status = 'completed' 
WHERE status IS NULL;

-- 8️⃣ Мигрировать blood_type из таблицы users
\echo '8️⃣ Заполняем blood_type из таблицы users...'
UPDATE donation_history dh
SET blood_type = u.blood_type
FROM users u
WHERE dh.donor_id = u.id
AND dh.blood_type IS NULL;

-- 9️⃣ Создать/обновить индексы
\echo '9️⃣ Создаём индексы...'
DROP INDEX IF EXISTS idx_donation_history_user;
CREATE INDEX IF NOT EXISTS idx_donation_history_donor ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_medcenter ON donation_history(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_response ON donation_history(response_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);
CREATE INDEX IF NOT EXISTS idx_donation_history_status ON donation_history(status);

-- 🔟 Проверка финальной схемы
\echo ''
\echo '📊 Финальная схема таблицы donation_history:'
\d donation_history

\echo ''
\echo '📋 Количество записей:'
SELECT COUNT(*) as total_records FROM donation_history;

\echo ''
\echo '✅ Миграция завершена успешно!'
\echo ''
\echo 'ℹ️  Резервная копия: donation_history_backup_20260126'
\echo 'ℹ️  Для отката выполните:'
\echo '    DROP TABLE donation_history;'
\echo '    ALTER TABLE donation_history_backup_20260126 RENAME TO donation_history;'
