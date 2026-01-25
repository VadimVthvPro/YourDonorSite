#!/bin/bash
echo "========================================="
echo "🔍 ПРОВЕРКА DONATION_HISTORY"
echo "========================================="

echo ""
echo "Введите пароль root@178.172.212.221:"

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Проверяем существование таблицы donation_history:"
sudo -u postgres psql -d donor_db -c "\d donation_history" 2>&1

echo ""
echo "2️⃣ Проверяем записи в donation_history:"
sudo -u postgres psql -d donor_db -c "SELECT * FROM donation_history ORDER BY donation_date DESC LIMIT 5;" 2>&1

echo ""
echo "3️⃣ Проверяем donation_responses со статусом completed:"
sudo -u postgres psql -d donor_db -c "SELECT id, user_id, status, actual_donation_date FROM donation_responses WHERE status = 'completed' ORDER BY updated_at DESC LIMIT 5;"

echo ""
echo "4️⃣ Проверяем статистику донора в users:"
sudo -u postgres psql -d donor_db -c "SELECT id, full_name, total_donations, total_volume_ml, last_donation_date FROM users WHERE total_donations > 0;"

echo ""
echo "=========================================
✅ ПРОВЕРКА ЗАВЕРШЕНА
=========================================
"

ENDSSH
