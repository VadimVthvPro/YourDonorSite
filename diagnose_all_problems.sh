#!/bin/bash
echo "========================================="
echo "🔍 ПОЛНАЯ ДИАГНОСТИКА ВСЕХ ПРОБЛЕМ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Проверяем логи Telegram отправки:"
tail -50 /var/log/tvoydonor-api.out.log | grep -i "telegram\|сообщение отправлено"

echo ""
echo "2️⃣ Проверяем ошибки Telegram:"
tail -50 /var/log/tvoydonor-api.err.log | grep -i "telegram"

echo ""
echo "3️⃣ Проверяем данные донора в conversations:"
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor -c "
SELECT c.id, c.donor_id, u.full_name, u.telegram_id
FROM conversations c
JOIN users u ON u.id = c.donor_id
WHERE c.id = 1;
"

echo ""
echo "4️⃣ Проверяем отправленные сообщения:"
psql -U donor_user -h localhost your_donor -c "
SELECT id, conversation_id, sender_type, sender_id, message_text, created_at
FROM chat_messages
ORDER BY created_at DESC
LIMIT 5;
"

echo ""
echo "5️⃣ Проверяем TELEGRAM_BOT_TOKEN в .env:"
grep "TELEGRAM_BOT_TOKEN" /opt/tvoydonor/website/backend/.env | head -c 50

echo ""
echo ""
echo "========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "========================================="

ENDSSH
