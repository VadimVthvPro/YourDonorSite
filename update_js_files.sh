#!/bin/bash
# Безопасное обновление JS файлов на сервере
# Использование: ./update_js_files.sh

set -e

echo "=========================================
🔄 ОБНОВЛЕНИЕ JS ФАЙЛОВ НА СЕРВЕРЕ
========================================="

echo ""
echo "1️⃣ Создаём backup старых JS файлов..."
ssh root@178.172.212.221 << 'ENDSSH'
cd /opt/tvoydonor/website
mkdir -p js_backup_$(date +%Y%m%d_%H%M%S)
cp -r js/*.js js_backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || echo "Backup создан"
ENDSSH

echo ""
echo "2️⃣ Загружаем актуальные JS файлы..."
scp /Users/VadimVthv/Your_donor/website/js/messenger.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp /Users/VadimVthv/Your_donor/website/js/config.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp /Users/VadimVthv/Your_donor/website/js/auth.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp /Users/VadimVthv/Your_donor/website/js/app.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp /Users/VadimVthv/Your_donor/website/js/donor-dashboard.js root@178.172.212.221:/opt/tvoydonor/website/js/
scp /Users/VadimVthv/Your_donor/website/js/medcenter-dashboard.js root@178.172.212.221:/opt/tvoydonor/website/js/

echo ""
echo "3️⃣ Обновляем временные метки в HTML для сброса кэша..."
TIMESTAMP=$(date +%Y%m%d%H%M)
ssh root@178.172.212.221 << ENDSSH
# Обновляем версии в index.html
sed -i "s/?v=[0-9]*/?v=${TIMESTAMP}/g" /opt/tvoydonor/website/index.html
sed -i "s/?v=[0-9]*/?v=${TIMESTAMP}/g" /opt/tvoydonor/website/pages/auth.html
sed -i "s/?v=[0-9]*/?v=${TIMESTAMP}/g" /opt/tvoydonor/website/pages/donor-dashboard.html
sed -i "s/?v=[0-9]*/?v=${TIMESTAMP}/g" /opt/tvoydonor/website/pages/medcenter-dashboard.html

echo "Версия обновлена на: ?v=${TIMESTAMP}"
ENDSSH

echo ""
echo "4️⃣ Проверяем что файлы обновились..."
ssh root@178.172.212.221 "ls -lh /opt/tvoydonor/website/js/messenger.js /opt/tvoydonor/website/js/config.js"

echo ""
echo "5️⃣ Проверяем baseURL в messenger.js на сервере..."
ssh root@178.172.212.221 "head -30 /opt/tvoydonor/website/js/messenger.js | grep -A 5 'baseURL'"

echo ""
echo "========================================="
echo "✅ JS ФАЙЛЫ ОБНОВЛЕНЫ!"
echo "========================================="
echo ""
echo "🌐 Откройте https://tvoydonor.by"
echo "🔄 ЖЁСТКО обновите страницу (Ctrl+Shift+R)"
echo "✅ Проверьте сообщения!"
