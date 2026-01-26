#!/bin/bash
echo "========================================="
echo "🚀 КОМПЛЕКСНОЕ РЕШЕНИЕ ВСЕХ ПРОБЛЕМ"
echo "========================================="
echo ""
echo "Решаемые проблемы:"
echo "1. ✅ Мобильный дизайн (противопоказания горизонтальные)"
echo "2. ✅ Статистика донора и медцентра"
echo "3. ✅ UX регистрации (подсказки и ошибки)"
echo ""
echo "Пароль: Vadamahjkl1! (ввести несколько раз)"
echo ""

# =====================================
# ПРОБЛЕМА 1: МОБИЛЬНЫЙ ДИЗАЙН
# =====================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ПРОБЛЕМА 1: ИСПРАВЛЕНИЕ МОБИЛЬНОГО ДИЗАЙНА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Загружаем исправленный CSS..."
scp /Users/VadimVthv/Your_donor/website/css/styles.css root@178.172.212.221:/opt/tvoydonor/website/css/styles.css

echo ""
echo "2️⃣ Обновляем версию CSS в HTML..."
ssh root@178.172.212.221 << 'ENDSSH1'
VERSION=$(date +%Y%m%d%H%M%S)
sed -i "s/styles\.css?v=[^\"']*/styles.css?v=${VERSION}/" /opt/tvoydonor/website/index.html
echo "✅ CSS версия обновлена: ?v=${VERSION}"
ENDSSH1

# =====================================
# ПРОБЛЕМА 2: СТАТИСТИКА
# =====================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ПРОБЛЕМА 2: ИСПРАВЛЕНИЕ СТАТИСТИКИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "3️⃣ Загружаем исправленный app.py..."
scp /Users/VadimVthv/Your_donor/website/backend/app.py root@178.172.212.221:/opt/tvoydonor/website/backend/app.py

echo ""
echo "4️⃣ Создаём таблицу donation_history и мигрируем данные..."
ssh root@178.172.212.221 << 'ENDSSH2'

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

-- Мигрируем donation_responses → donation_history
INSERT INTO donation_history (donor_id, medical_center_id, donation_date, donation_type, volume_ml, created_at)
SELECT 
    dr.user_id,
    dr.medical_center_id,
    COALESCE(dr.actual_donation_date::date, dr.updated_at::date, CURRENT_DATE),
    'blood',
    450,
    COALESCE(dr.actual_donation_date, dr.updated_at, NOW())
FROM donation_responses dr
WHERE dr.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM donation_history dh
    WHERE dh.donor_id = dr.user_id
    AND dh.medical_center_id = dr.medical_center_id
    AND dh.donation_date = COALESCE(dr.actual_donation_date::date, dr.updated_at::date)
);

SELECT '✅ Таблица donation_history создана' as result;
SELECT COUNT(*) as "Записей в donation_history" FROM donation_history;

EOSQL

echo ""
echo "✅ База данных обновлена"

ENDSSH2

# =====================================
# ПРОБЛЕМА 3: UX РЕГИСТРАЦИИ
# =====================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ПРОБЛЕМА 3: УЛУЧШЕНИЕ UX РЕГИСТРАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "5️⃣ Загружаем улучшенные JS файлы..."
scp /Users/VadimVthv/Your_donor/website/js/auth.js root@178.172.212.221:/opt/tvoydonor/website/js/auth.js
scp /Users/VadimVthv/Your_donor/website/js/donor-dashboard.js root@178.172.212.221:/opt/tvoydonor/website/js/donor-dashboard.js

echo ""
echo "6️⃣ Обновляем версии JS в HTML..."
ssh root@178.172.212.221 << 'ENDSSH3'
VERSION=$(date +%Y%m%d%H%M%S)
sed -i "s/auth\.js?v=[^\"']*/auth.js?v=${VERSION}/" /opt/tvoydonor/website/pages/auth.html
sed -i "s/donor-dashboard\.js?v=[^\"']*/donor-dashboard.js?v=${VERSION}/" /opt/tvoydonor/website/pages/donor-dashboard.html
echo "✅ JS версии обновлены: ?v=${VERSION}"
ENDSSH3

# =====================================
# ПЕРЕЗАПУСК API
# =====================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ФИНАЛЬНЫЙ ШАГ: ПЕРЕЗАПУСК API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "7️⃣ Перезапускаем API..."
ssh root@178.172.212.221 << 'ENDSSH4'
supervisorctl restart tvoydonor-api
sleep 3
supervisorctl status tvoydonor-api
ENDSSH4

echo ""
echo "=========================================
✅ ВСЁ ИСПРАВЛЕНО И ЗАГРУЖЕНО НА СЕРВЕР!
=========================================
"

echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. МОБИЛЬНЫЙ ДИЗАЙН:"
echo "   • Откройте https://tvoydonor.by на телефоне"
echo "   • Прокрутите до 'Противопоказания'"
echo "   • ✅ Карточки должны быть горизонтальными"
echo ""
echo "2. СТАТИСТИКА:"
echo "   • Донор → раздел 'Статистика'"
echo "   • ✅ Должна показаться история донаций"
echo "   • Медцентр → главная страница"
echo "   • ✅ Счётчики должны работать"
echo ""
echo "3. РЕГИСТРАЦИЯ:"
echo "   • Попробуйте зарегистрироваться"
echo "   • ✅ Должны быть подсказки и чёткие ошибки"
echo ""

