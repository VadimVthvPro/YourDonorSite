#!/bin/bash
echo "========================================="
echo "🔧 КОМПЛЕКСНОЕ ИСПРАВЛЕНИЕ СТАТИСТИКИ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 1: СОЗДАНИЕ ТАБЛИЦЫ donation_history"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Создаём таблицу
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    donation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    donation_type VARCHAR(20) DEFAULT 'blood',
    volume_ml INTEGER DEFAULT 450,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_donation_history_donor ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);
CREATE INDEX IF NOT EXISTS idx_donation_history_mc ON donation_history(medical_center_id);

SELECT '✅ Таблица donation_history создана' as result;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 2: МИГРАЦИЯ ЗАВЕРШЁННЫХ ДОНАЦИЙ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Мигрируем donation_responses → donation_history
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
    AND dh.medical_center_id = dr.medical_center_id
    AND dh.donation_date = COALESCE(dr.actual_donation_date::date, dr.updated_at::date)
)
ORDER BY dr.id;

SELECT '✅ Миграция завершена' as result;
SELECT COUNT(*) as "Записей в donation_history" FROM donation_history;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 3: ПРОВЕРКА РЕЗУЛЬТАТОВ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo -u postgres psql -d your_donor << 'EOSQL'

-- Сравнение users vs donation_history
SELECT 
    u.id as "ID",
    u.full_name as "Донор",
    u.total_donations as "Счётчик users",
    COUNT(dh.id) as "Записей history",
    CASE 
        WHEN u.total_donations = COUNT(dh.id) THEN '✅'
        WHEN u.total_donations > COUNT(dh.id) THEN '⚠️ users > history'
        WHEN u.total_donations < COUNT(dh.id) THEN '❌ history > users'
        ELSE '❓'
    END as "Статус"
FROM users u
LEFT JOIN donation_history dh ON u.id = dh.donor_id
WHERE u.total_donations > 0 OR dh.id IS NOT NULL
GROUP BY u.id, u.full_name, u.total_donations
ORDER BY u.total_donations DESC;

EOSQL

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ШАГ 4: ПЕРЕЗАПУСК API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

supervisorctl restart tvoydonor-api
sleep 3
supervisorctl status tvoydonor-api

echo ""
echo "=========================================
✅ ВСЁ ИСПРАВЛЕНО!
=========================================
"

echo ""
echo "🧪 ПРОВЕРЬТЕ СЕЙЧАС:"
echo ""
echo "1. ДОНОР:"
echo "   Откройте кабинет донора → раздел 'Статистика'"
echo "   Должна показаться история донаций!"
echo ""
echo "2. МЕДЦЕНТР:"
echo "   Откройте кабинет медцентра → главная страница"
echo "   Счётчики должны показать реальные данные!"
echo ""

ENDSSH
