-- 🔧 МИГРАЦИЯ: Создание записей donation_history для всех confirmed откликов
-- Эти отклики были подтверждены, но донации не были записаны в историю

BEGIN;

-- 1. Создаём записи в donation_history для всех confirmed/completed откликов БЕЗ history
INSERT INTO donation_history (donor_id, medical_center_id, donation_date, blood_type, volume_ml, status, notes, response_id, created_at)
SELECT 
    dr.user_id as donor_id,
    dr.medical_center_id,
    COALESCE(dr.updated_at::date, dr.created_at::date) as donation_date,
    br.blood_type,
    450 as volume_ml,
    'completed' as status,
    'Миграция: донация по запросу #' || dr.request_id as notes,
    dr.id as response_id,
    NOW() as created_at
FROM donation_responses dr
JOIN blood_requests br ON dr.request_id = br.id
LEFT JOIN donation_history dh ON dr.id = dh.response_id
WHERE dr.status IN ('confirmed', 'completed')
  AND dh.id IS NULL;  -- Только те, у которых НЕТ записи в history

-- 2. Обновляем статистику в таблице users для каждого донора
UPDATE users u
SET 
    total_donations = (
        SELECT COUNT(*) 
        FROM donation_history dh 
        WHERE dh.donor_id = u.id
    ),
    total_volume_ml = (
        SELECT COALESCE(SUM(dh.volume_ml), 0) 
        FROM donation_history dh 
        WHERE dh.donor_id = u.id
    ),
    last_donation_date = (
        SELECT MAX(dh.donation_date) 
        FROM donation_history dh 
        WHERE dh.donor_id = u.id
    )
WHERE u.id IN (
    SELECT DISTINCT donor_id 
    FROM donation_history
);

-- 3. Проверяем результаты
SELECT 'После миграции:' as info;

SELECT '=== donation_history ===' as table_name;
SELECT 
    medical_center_id,
    COUNT(*) as total_donations,
    COUNT(DISTINCT donor_id) as unique_donors
FROM donation_history
GROUP BY medical_center_id;

SELECT '=== users (доноры) ===' as table_name;
SELECT 
    id,
    email,
    total_donations,
    last_donation_date,
    total_volume_ml
FROM users
WHERE id IN (1, 3, 8, 11)
ORDER BY id;

COMMIT;

-- Показываем количество мигрированных записей
SELECT 
    COUNT(*) as migrated_donations,
    COUNT(DISTINCT donor_id) as affected_donors
FROM donation_history
WHERE notes LIKE 'Миграция:%';
