#!/bin/bash
echo "========================================="
echo "🔍 ДИАГНОСТИКА TELEGRAM ПРОБЛЕМ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Ошибка генерации кода привязки:"
tail -100 /var/log/tvoydonor-api.err.log | grep -B 10 -A 5 "link-code\|telegram_link"

echo ""
echo "2️⃣ Статус Telegram бота:"
supervisorctl status tvoydonor-bot

echo ""
echo "3️⃣ Логи Telegram бота (последние 50 строк):"
tail -50 /var/log/tvoydonor-bot.err.log

echo ""
echo "4️⃣ Логи Telegram бота (stdout):"
tail -50 /var/log/tvoydonor-bot.out.log

echo ""
echo "5️⃣ Проверка таблицы telegram_link_codes:"
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor -c "\d telegram_link_codes"

echo ""
echo "6️⃣ Последние коды привязки:"
psql -U donor_user -h localhost your_donor -c "
SELECT id, user_id, code, created_at, expires_at, used_at 
FROM telegram_link_codes 
ORDER BY created_at DESC 
LIMIT 5;
"

echo ""
echo "========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "========================================="

ENDSSH
