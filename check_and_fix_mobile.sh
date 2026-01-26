#!/bin/bash

echo "🔍 ПРОВЕРКА И ИСПРАВЛЕНИЕ МОБИЛЬНОГО CSS"
echo "=========================================="

SERVER="root@178.172.212.221"

echo ""
echo "📋 Шаг 1: Проверяем текущий CSS на сервере..."
ssh $SERVER << 'ENDSSH'
echo "--- Проверка .contra-card в @media (max-width: 768px) ---"
grep -A 50 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep -A 15 ".contra-card {" | head -20
echo ""
echo "--- Размер файла ---"
ls -lh /opt/tvoydonor/website/css/styles.css
echo ""
echo "--- Последнее изменение ---"
stat /opt/tvoydonor/website/css/styles.css | grep Modify
ENDSSH

echo ""
echo "📋 Шаг 2: Загружаем ПРАВИЛЬНЫЙ styles.css..."
scp /Users/VadimVthv/Your_donor/website/css/styles.css $SERVER:/opt/tvoydonor/website/css/styles.css

echo ""
echo "📋 Шаг 3: Обновляем версию CSS в HTML..."
TIMESTAMP=$(date +%s)
ssh $SERVER << ENDSSH
# Обновляем версию в index.html
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/index.html

# Обновляем версию в donor-dashboard.html
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/donor-dashboard.html

# Обновляем версию в medcenter-dashboard.html
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/medcenter-dashboard.html

echo ""
echo "✅ Версия CSS обновлена на: $TIMESTAMP"
echo ""
echo "--- Проверяем обновление ---"
grep "styles.css" /opt/tvoydonor/website/index.html | head -1
ENDSSH

echo ""
echo "📋 Шаг 4: Перезагружаем nginx..."
ssh $SERVER << 'ENDSSH'
nginx -t && systemctl reload nginx
echo "✅ Nginx перезагружен"
ENDSSH

echo ""
echo "📋 Шаг 5: Проверяем что CSS обновился..."
ssh $SERVER << 'ENDSSH'
echo "--- Новый .contra-card в @media (max-width: 768px) ---"
grep -A 50 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep -A 15 ".contra-card {" | head -20
ENDSSH

echo ""
echo "✅ ГОТОВО!"
echo ""
echo "🧪 ТЕСТИРОВАНИЕ:"
echo "1. Откройте https://tvoydonor.by на телефоне"
echo "2. Жёстко обновите: Cmd+Shift+R (iOS) или Ctrl+Shift+R (Android)"
echo "3. Прокрутите до 'Противопоказания'"
echo "4. Каждая карточка должна быть ГОРИЗОНТАЛЬНОЙ"
echo ""
echo "Версия CSS: $TIMESTAMP"
