#!/bin/bash
echo "========================================="
echo "🔧 ПОЛНОЕ ИСПРАВЛЕНИЕ ВСЕХ ПРОБЛЕМ"
echo "========================================="

echo ""
echo "1️⃣ Загружаем исправленный messenger.js..."
scp /Users/VadimVthv/Your_donor/website/js/messenger.js root@178.172.212.221:/opt/tvoydonor/website/js/messenger.js

echo ""
echo "2️⃣ Обновляем версию в HTML..."
ssh root@178.172.212.221 << 'ENDSSH'
TIMESTAMP=$(date +%Y%m%d%H%M)
sed -i "s/?v=[0-9]*/?v=$TIMESTAMP/g" /opt/tvoydonor/website/index.html
sed -i "s/?v=[0-9]*/?v=$TIMESTAMP/g" /opt/tvoydonor/website/pages/donor-dashboard.html
sed -i "s/?v=[0-9]*/?v=$TIMESTAMP/g" /opt/tvoydonor/website/pages/medcenter-dashboard.html
echo "Версия обновлена на: ?v=$TIMESTAMP"
ENDSSH

echo ""
echo "3️⃣ Проверяем логи отправки в Telegram..."
ssh root@178.172.212.221 "tail -100 /var/log/tvoydonor-api.out.log | grep -i 'сообщение отправлено\|telegram'"

echo ""
echo "4️⃣ Проверяем ошибки Telegram..."
ssh root@178.172.212.221 "tail -50 /var/log/tvoydonor-api.err.log | grep -i 'telegram' | tail -10"

echo ""
echo "5️⃣ Проверяем TELEGRAM_BOT_TOKEN..."
ssh root@178.172.212.221 "grep 'TELEGRAM_BOT_TOKEN' /opt/tvoydonor/website/backend/.env | head -c 60"

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!"
echo "========================================="
echo ""
echo "🌐 Откройте https://tvoydonor.by"
echo "🔄 ЖЁСТКО обновите (Cmd+Shift+R)"
echo "💬 Попробуйте отправить сообщение!"
echo ""
echo "📋 Проверьте:"
echo "  1. Ваши сообщения теперь СПРАВА ✓"
echo "  2. Уведомление в Telegram придёт донору 📱"
echo ""
