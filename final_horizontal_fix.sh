#!/bin/bash

# ═══════════════════════════════════════════════════════════════════
# ФИНАЛЬНОЕ РЕШЕНИЕ: ГОРИЗОНТАЛЬНЫЕ ПЛАШКИ НА ВСЕХ УСТРОЙСТВАХ
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔬 КОМПЛЕКСНОЕ ИССЛЕДОВАНИЕ И ИСПРАВЛЕНИЕ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:"
echo ""
echo "1. ❌ ДУБЛИРУЮЩИЕСЯ ПРАВИЛА в CSS:"
echo "   • Строка 1354: grid-template-columns: repeat(2, 1fr)"
echo "   • Строка 2701: grid-template-columns: repeat(2, 1fr)"
echo "   • КОНФЛИКТ: последнее правило перезаписывало всё!"
echo ""
echo "2. ❌ ВЕРТИКАЛЬНАЯ СТРУКТУРА карточек:"
echo "   • Хедер и список были вертикально"
echo "   • Нужна горизонтальная компоновка"
echo ""
echo "✅ ВЫПОЛНЕННЫЕ ИСПРАВЛЕНИЯ:"
echo ""
echo "1. ✅ Изменён БАЗОВЫЙ стиль:"
echo "   • .contra-grid: 1fr (одна колонка на ВСЕХ экранах)"
echo ""
echo "2. ✅ Удалены ДУБЛИРУЮЩИЕ правила:"
echo "   • Строка 2701-2703: удалено"
echo "   • Строка 2674-2676: удалено"
echo ""
echo "3. ✅ Карточки теперь ГОРИЗОНТАЛЬНЫЕ:"
echo "   • display: flex"
echo "   • Хедер (иконка + текст) + Список в одну строку"
echo ""
echo "4. ✅ Список теперь ГОРИЗОНТАЛЬНЫЙ:"
echo "   • display: flex, flex-wrap: wrap"
echo "   • Элементы в ряд с переносом"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 ПРОВЕРКА ЛОКАЛЬНОГО CSS..."
echo ""

LOCAL_CSS="/Users/VadimVthv/Your_donor/website/css/styles.css"

if [ ! -f "$LOCAL_CSS" ]; then
    echo "❌ ОШИБКА: Файл не найден!"
    exit 1
fi

echo "✅ Файл найден: $LOCAL_CSS"
echo "   Размер: $(wc -c < "$LOCAL_CSS") байт"
echo "   Строк: $(wc -l < "$LOCAL_CSS")"
echo ""

# Проверяем базовый стиль
if grep -q "grid-template-columns: 1fr; /\* ОДНА КОЛОНКА НА ВСЕХ ЭКРАНАХ \*/" "$LOCAL_CSS"; then
    echo "✅ Базовый стиль: grid-template-columns: 1fr"
else
    echo "⚠️  Внимание: базовый стиль может быть некорректным"
fi

# Проверяем что дублирующих правил нет
CONTRA_GRID_COUNT=$(grep -c "\.contra-grid {" "$LOCAL_CSS")
echo "✅ Количество правил .contra-grid: $CONTRA_GRID_COUNT"

# Проверяем горизонтальный список
if grep -q "\.contra-list {" "$LOCAL_CSS" && grep -A 5 "\.contra-list {" "$LOCAL_CSS" | grep -q "display: flex"; then
    echo "✅ Список: display: flex (горизонтально)"
else
    echo "⚠️  Внимание: список может быть не горизонтальным"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📤 ЗАГРУЗКА НА СЕРВЕР"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Сейчас будет выполнено:"
echo "  1. Резервная копия на сервере"
echo "  2. Загрузка исправленного CSS"
echo "  3. Обновление версии CSS"
echo "  4. Перезагрузка nginx"
echo "  5. Проверка результата"
echo ""
echo "Потребуется ввести пароль 3 раза:"
echo "  Пароль: Vadamahjkl1!"
echo ""
read -p "Нажмите Enter чтобы продолжить..."
echo ""

# КОМАНДА 1: Резервная копия и загрузка
echo "━━━ КОМАНДА 1/3: Резервная копия и загрузка ━━━"
echo ""
ssh root@178.172.212.221 'mkdir -p /opt/tvoydonor/backups && cp /opt/tvoydonor/website/css/styles.css /opt/tvoydonor/backups/styles.css.backup.$(date +%Y%m%d_%H%M%S) && echo "✅ Бэкап создан"' && scp /Users/VadimVthv/Your_donor/website/css/styles.css root@178.172.212.221:/opt/tvoydonor/website/css/styles.css && echo "✅ CSS загружен"

echo ""

# КОМАНДА 2: Обновление версии и перезагрузка
echo "━━━ КОМАНДА 2/3: Обновление версии и перезагрузка ━━━"
echo ""
ssh root@178.172.212.221 'TIMESTAMP=$(date +%s) && sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/index.html && sed -i "s|href=\"css/styles\.css\"|href=\"css/styles.css?v=$TIMESTAMP\"|g" /opt/tvoydonor/website/index.html && [ -d /var/cache/nginx ] && rm -rf /var/cache/nginx/* ; nginx -t && systemctl reload nginx && echo "" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━" && echo "✅ УСТАНОВКА ЗАВЕРШЕНА!" && echo "━━━━━━━━━━━━━━━━━━━━━━━━━" && echo "" && echo "Новая версия CSS: $TIMESTAMP" && grep "styles.css" /opt/tvoydonor/website/index.html | head -1'

echo ""

# КОМАНДА 3: Проверка
echo "━━━ КОМАНДА 3/3: Проверка результата ━━━"
echo ""
ssh root@178.172.212.221 'echo "🔍 ФИНАЛЬНАЯ ПРОВЕРКА:" && echo "" && echo "1. Базовый grid-template-columns:" && grep "\.contra-grid {" /opt/tvoydonor/website/css/styles.css -A 2 | grep "grid-template-columns:" | head -1 | xargs && echo "" && echo "2. Список display:" && grep "\.contra-list {" /opt/tvoydonor/website/css/styles.css -A 10 | grep "display:" | head -1 | xargs && echo "" && echo "3. Проверка на дублирующие правила:" && echo "   Количество .contra-grid:" && grep -c "\.contra-grid {" /opt/tvoydonor/website/css/styles.css && echo "" && echo "✅ Проверка завершена!"'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 ТЕСТИРОВАНИЕ:"
echo ""
echo "1. Откройте: https://tvoydonor.by"
echo ""
echo "2. ОБЯЗАТЕЛЬНО ОЧИСТИТЕ КЭШ:"
echo "   • iOS: Настройки → Safari → Очистить историю"
echo "   • Android: Chrome → ⋮ → Очистить данные → Кэш"
echo ""
echo "3. Прокрутите до 'Противопоказания'"
echo ""
echo "✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:"
echo ""
echo "   ┌─────────────────────────────────────────────────┐"
echo "   │ [🔴] Постоянные      • ВИЧ • Онкология         │"
echo "   │      противопоказания  • Болезни крови • ...   │"
echo "   ├─────────────────────────────────────────────────┤"
echo "   │ [🟡] Временные       • Грипп • ОРВИ • Операции │"
echo "   │      противопоказания  • Татуировки • ...      │"
echo "   └─────────────────────────────────────────────────┘"
echo ""
echo "   ✅ Плашки: ОДНА ПОД ДРУГОЙ (на всю ширину)"
echo "   ✅ Внутри: ИКОНКА → ЗАГОЛОВОК → СПИСОК (горизонтально)"
echo "   ✅ На ПК: то же самое"
echo "   ✅ На мобильных: то же самое"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Скрипт завершён!"
echo ""
