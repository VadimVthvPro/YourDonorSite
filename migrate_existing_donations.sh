#!/bin/bash
echo "========================================="
echo "🔄 МИГРАЦИЯ СУЩЕСТВУЮЩИХ ДОНАЦИЙ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "Мигрируем завершённые donation_responses в donation_history..."

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
)
ORDER BY dr.id;

-- Показываем результат
SELECT '
✅ Миграция завершена!' as info;

SELECT '
Статистика donation_history:' as info;
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT donor_id) as unique_donors,
    MIN(donation_date) as first_donation,
    MAX(donation_date) as last_donation
FROM donation_history;

SELECT '
История донаций по донорам:' as info;
SELECT 
    u.id,
    u.full_name,
    u.total_donations as donations_counter,
    COUNT(dh.id) as history_records,
    MAX(dh.donation_date) as last_in_history
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
