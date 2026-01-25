#!/bin/bash
echo "========================================="
echo "🔧 ИСПРАВЛЕНИЕ TELEGRAM ПРОБЛЕМ"
echo "========================================="

echo ""
echo "1️⃣ Загружаем исправленный app.py..."
scp /Users/VadimVthv/Your_donor/website/backend/app.py root@178.172.212.221:/opt/tvoydonor/website/backend/app.py

echo ""
echo "2️⃣ Загружаем исправленный telegram_bot.py..."
scp /Users/VadimVthv/Your_donor/website/backend/telegram_bot.py root@178.172.212.221:/opt/tvoydonor/website/backend/telegram_bot.py

echo ""
echo "3️⃣ Перезапускаем сервисы..."
ssh root@178.172.212.221 << 'ENDSSH'
supervisorctl restart all
sleep 3
supervisorctl status
ENDSSH

echo ""
echo "4️⃣ Проверяем логи бота..."
ssh root@178.172.212.221 "tail -20 /var/log/tvoydonor-bot.out.log"

echo ""
echo "========================================="
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================="
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. Откройте https://tvoydonor.by как ДОНОР"
echo "2. Перейдите в Настройки → Привязать Telegram"
echo "3. Нажмите \"Получить код\""
echo "4. Скопируйте 6-значный код"
echo "5. Откройте Telegram → @TvoyDonorZdesBot"
echo "6. Нажмите /start (если ещё не нажимали)"
echo "7. Отправьте код боту"
echo "8. Бот должен ОТВЕТИТЬ и привязать аккаунт!"
echo ""
