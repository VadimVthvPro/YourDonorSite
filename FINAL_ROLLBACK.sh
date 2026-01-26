#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "🚨 ЭКСТРЕННЫЙ ОТКАТ - УБИРАЕМ АВТОВХОД"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Загружаю исправленные файлы..."
echo ""

cd /Users/VadimVthv/Your_donor

# Загружаем файлы БЕЗ автовхода
scp website/js/app.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp website/js/auth.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp website/index.html root@178.172.212.221:/opt/tvoydonor/website/

# Обновляем версию
ssh root@178.172.212.221 '
cd /opt/tvoydonor/website
TIMESTAMP=$(date +%s)
sed -i "s/window.VERSION = .*/window.VERSION = '"'"'${TIMESTAMP}'"'"';/" js/config.js
nginx -t && systemctl reload nginx
echo "✅ Готово! Версия: ${TIMESTAMP}"
'

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ ОТКАТ ЗАВЕРШЁН!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 ПРОВЕРЬТЕ:"
echo "  1. Откройте: https://tvoydonor.by/"
echo "  2. Нажмите: Cmd+Shift+R"
echo "  3. Сайт должен работать НОРМАЛЬНО"
echo ""
