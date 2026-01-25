#!/bin/bash
echo "========================================="
echo "🔧 ИСПРАВЛЕНИЕ ОТПРАВКИ СООБЩЕНИЙ"
echo "========================================="

echo ""
echo "1️⃣ Загружаем исправленный app.py..."
scp /Users/VadimVthv/Your_donor/website/backend/app.py root@178.172.212.221:/opt/tvoydonor/website/backend/app.py

echo ""
echo "2️⃣ Загружаем исправленный messaging_api.py..."
scp /Users/VadimVthv/Your_donor/website/backend/messaging_api.py root@178.172.212.221:/opt/tvoydonor/website/backend/messaging_api.py

echo ""
echo "3️⃣ Перезапускаем сервисы..."
ssh root@178.172.212.221 << 'ENDSSH'
supervisorctl restart all
sleep 3
supervisorctl status
ENDSSH

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo ""
echo "🌐 Откройте https://tvoydonor.by"
echo "🔄 ЖЁСТКО обновите страницу (Cmd+Shift+R)"
echo "💬 Попробуйте отправить сообщение!"
echo ""
