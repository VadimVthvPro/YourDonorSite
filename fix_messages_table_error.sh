#!/bin/bash
echo "========================================="
echo "🔧 ИСПРАВЛЕНИЕ ОШИБКИ ОТПРАВКИ СООБЩЕНИЙ"
echo "========================================="

ssh root@178.172.212.221 << 'ENDSSH'

echo ""
echo "1️⃣ Проверяем код функции send_conversation_message..."
grep -n "def send_conversation_message" /opt/tvoydonor/website/backend/app.py -A 60 | grep -A 30 "INSERT INTO"

echo ""
echo "2️⃣ Структура таблицы messages (СТАРАЯ):"
export PGPASSWORD='u1oFnZALhyfpbtir08nH'
psql -U donor_user -h localhost your_donor -c "\d messages" | head -20

echo ""
echo "3️⃣ Структура таблицы chat_messages (ПРАВИЛЬНАЯ):"
psql -U donor_user -h localhost your_donor -c "\d chat_messages"

echo ""
echo "========================================="
echo "❌ ПРОБЛЕМА НАЙДЕНА!"
echo "========================================="
echo ""
echo "Код в app.py использует INSERT INTO messages"
echo "но должен использовать INSERT INTO chat_messages!"
echo ""
echo "messages имеет: from_user_id, from_medcenter_id, message"
echo "chat_messages имеет: conversation_id, sender_id, sender_type, message_text"
echo ""
echo "Нужно проверить локальный app.py и загрузить правильную версию!"
echo ""

ENDSSH

echo ""
echo "========================================="
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "========================================="
