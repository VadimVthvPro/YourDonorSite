#!/bin/bash
echo "========================================="
echo "🔄 МИГРАЦИЯ ЗАВЕРШЁННЫХ ДОНАЦИЙ"
echo "========================================="

echo ""
echo "Подключаемся к серверу..."
echo "Пароль: Vadamahjkl1!"
echo ""

ssh root@178.172.212.221 << 'ENDSSH'

echo "Мигрируем donation_responses → donation_history..."

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Вставляем записи для всех завершённых донаций
INSERT INTO donation_history (donor_id, medical_center_id, donation_date, donation_type, volume_ml, created_at)
SELECT 
    dr.user_id as donor_id,
    dr.medical_center_id,
    COALESCE(dr.actual_donation_date::date, dr.updated_at::date, CURRENT_DATE) as donation_date,
    'blood' as donation_type,
    450 as volume_ml,
    COALESCE(dr.actual_donation_date, dr.updated_at, NOW()) as created_at
FROM donation_responses dr
WHERE dr.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM donation_history dh
    WHERE dh.donor_id = dr.user_id
    AND dh.donation_date = COALESCE(dr.actual_donation_date::date, dr.updated_at::date)
);

SELECT '✅ Миграция завершена!' as status;

-- Показываем результат
SELECT 
    COUNT(*) as "Всего записей",
    COUNT(DISTINCT donor_id) as "Уникальных доноров",
    MIN(donation_date) as "Первая донация",
    MAX(donation_date) as "Последняя донация"
FROM donation_history;

-- История по донорам
SELECT 
    u.id as "ID",
    u.full_name as "ФИО",
    u.total_donations as "Счётчик",
    COUNT(dh.id) as "В истории"
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0
GROUP BY u.id, u.full_name, u.total_donations
ORDER BY u.total_donations DESC;

EOSQL

echo ""
echo "=========================================
✅ МИГРАЦИЯ ЗАВЕРШЕНА!
=========================================
"

ENDSSH
