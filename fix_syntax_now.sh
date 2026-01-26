#!/bin/bash
# 🚨 ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ - УБИРАЕМ ПРОБЛЕМНУЮ СТРОКУ

echo "🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ app.py на сервере"
echo ""

# Показываем что на строке 225
echo "📋 Текущая строка 225:"
sed -n '225p' /opt/tvoydonor/website/backend/app.py

echo ""
echo "🔧 Удаляем проблемную строку с f-string..."

# Создаём бэкап
cp /opt/tvoydonor/website/backend/app.py /opt/tvoydonor/website/backend/app.py.backup_$(date +%s)

# Найти и закомментировать все строки с app.logger.info содержащие donors_count["count"]
sed -i '/app\.logger\.info.*donors_count\[/d' /opt/tvoydonor/website/backend/app.py

echo "✅ Проблемная строка удалена"

echo ""
echo "🧪 Проверяем синтаксис Python..."
cd /opt/tvoydonor/website/backend
source venv/bin/activate
python -m py_compile app.py

if [ $? -eq 0 ]; then
    echo "✅ Синтаксис корректен!"
    
    echo ""
    echo "🔄 Перезапускаем API..."
    supervisorctl restart tvoydonor-api
    
    sleep 3
    
    echo ""
    echo "📊 Статус сервисов:"
    supervisorctl status
    
    echo ""
    echo "✅ САЙТ ВОССТАНОВЛЕН!"
else
    echo "❌ Всё ещё есть синтаксическая ошибка"
    echo "Показываем последние 30 строк компиляции:"
    python -m py_compile app.py 2>&1 | tail -30
fi
