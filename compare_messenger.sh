#!/bin/bash
# Сравнение версий файлов messenger
echo "=========================================
🔍 СРАВНЕНИЕ ВЕРСИЙ MESSENGER.JS
========================================="

echo ""
echo "1️⃣ ЛОКАЛЬНАЯ версия (первые 30 строк):"
head -30 /Users/VadimVthv/Your_donor/website/js/messenger.js | grep -E "baseURL|API_URL|messenger|conversations"

echo ""
echo "2️⃣ СЕРВЕРНАЯ версия (первые 30 строк):"
ssh root@178.172.212.221 "head -30 /opt/tvoydonor/website/js/messenger.js | grep -E 'baseURL|API_URL|messenger|conversations'"

echo ""
echo "3️⃣ Дата изменения локального файла:"
ls -lh /Users/VadimVthv/Your_donor/website/js/messenger.js

echo ""
echo "4️⃣ Дата изменения файла на сервере:"
ssh root@178.172.212.221 "ls -lh /opt/tvoydonor/website/js/messenger.js"

echo ""
echo "========================================="
echo "✅ СРАВНЕНИЕ ЗАВЕРШЕНО"
echo "========================================="
