#!/bin/bash

echo "🔍 ДИАГНОСТИКА: Почему мобильный CSS не применился"
echo "=================================================="

# Параметры
SERVER="root@178.172.212.221"
PASSWORD="Vadamahjkl1!"

echo ""
echo "📋 Шаг 1: Проверяем CSS на сервере..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
echo "--- Содержимое @media (max-width: 768px) для .contra-card ---"
grep -A 30 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep -A 20 ".contra-card" | head -25
ENDSSH

echo ""
echo "📋 Шаг 2: Проверяем версию CSS в HTML файлах..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
echo "--- В index.html ---"
grep "styles.css" /opt/tvoydonor/website/index.html
echo ""
echo "--- В donor-dashboard.html ---"
grep "styles.css" /opt/tvoydonor/website/donor-dashboard.html
echo ""
echo "--- В medcenter-dashboard.html ---"
grep "styles.css" /opt/tvoydonor/website/medcenter-dashboard.html
ENDSSH

echo ""
echo "📋 Шаг 3: Проверяем размер styles.css..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
ls -lh /opt/tvoydonor/website/css/styles.css
wc -l /opt/tvoydonor/website/css/styles.css
ENDSSH

echo ""
echo "📋 Шаг 4: Проверяем права доступа..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
ls -la /opt/tvoydonor/website/css/styles.css
ENDSSH

echo ""
echo "📋 Шаг 5: Проверяем последнее изменение styles.css..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
stat /opt/tvoydonor/website/css/styles.css | grep Modify
ENDSSH

echo ""
echo "📋 Шаг 6: Проверяем nginx кэш..."
sshpass -p "$PASSWORD" ssh $SERVER << 'ENDSSH'
nginx -V 2>&1 | grep cache
ENDSSH

echo ""
echo "✅ Диагностика завершена!"
echo ""
echo "Теперь я точно пойму проблему..."
