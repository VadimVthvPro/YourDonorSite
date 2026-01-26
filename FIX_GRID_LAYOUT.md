# 🎯 ИСПРАВЛЕНИЕ: ПЛАШКИ ГОРИЗОНТАЛЬНО (2 В РЯД)

## 📊 ЧТО ИЗМЕНИЛОСЬ:

### ❌ БЫЛО:
```
Плашки вертикально (столбиком):
┌──────────────┐
│ [🔴] Плашка 1│
├──────────────┤
│ [🟡] Плашка 2│
├──────────────┤
│ [🟢] Плашка 3│
├──────────────┤
│ [🔵] Плашка 4│
└──────────────┘
```

### ✅ СТАЛО:
```
Плашки горизонтально (2 в ряд):
┌──────────────┬──────────────┐
│ [🔴] Плашка 1│ [🟡] Плашка 2│
├──────────────┼──────────────┤
│ [🟢] Плашка 3│ [🔵] Плашка 4│
└──────────────┴──────────────┘
```

---

## 🔧 ИЗМЕНЕНИЕ В CSS:

```css
@media (max-width: 768px) {
    .contra-grid {
        grid-template-columns: repeat(2, 1fr); /* БЫЛО: 1fr */
        gap: 12px;
    }
}

@media (max-width: 480px) {
    .contra-grid {
        grid-template-columns: 1fr; /* Одна колонка на маленьких телефонах */
    }
}
```

---

## 📋 ПОШАГОВАЯ ИНСТРУКЦИЯ:

### ШАГ 1: Загрузить CSS на сервер

```bash
scp /Users/VadimVthv/Your_donor/website/css/styles.css root@178.172.212.221:/opt/tvoydonor/website/css/styles.css
```

**Пароль:** `Vadamahjkl1!`

---

### ШАГ 2: Подключиться к серверу

```bash
ssh root@178.172.212.221
```

**Пароль:** `Vadamahjkl1!`

---

### ШАГ 3: Обновить версию CSS

Скопируйте **все команды целиком**:

```bash
TIMESTAMP=$(date +%s)
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/index.html
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/donor-dashboard.html
sed -i "s|styles\.css?v=[0-9]*|styles.css?v=$TIMESTAMP|g" /opt/tvoydonor/website/medcenter-dashboard.html
echo "Новая версия CSS: $TIMESTAMP"
grep "styles.css" /opt/tvoydonor/website/index.html | head -1
```

---

### ШАГ 4: Перезагрузить nginx

```bash
nginx -t && systemctl reload nginx
```

Должно показать:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

### ШАГ 5: Проверить что применилось

```bash
grep -A 8 "@media (max-width: 768px)" /opt/tvoydonor/website/css/styles.css | grep -A 5 ".contra-grid {"
```

Должно показать:
```css
.contra-grid {
    grid-template-columns: repeat(2, 1fr); /* ← ДВЕ КОЛОНКИ! */
    gap: 12px;
    width: 100%;
    max-width: 100%;
}
```

---

### ШАГ 6: Выйти с сервера

```bash
exit
```

---

## 🧪 ТЕСТИРОВАНИЕ НА ТЕЛЕФОНЕ:

1. Откройте `https://tvoydonor.by`
2. **ЖЁСТКО обновите:**
   - **iOS/Mac:** `Cmd + Shift + R`
   - **Android:** `Ctrl + Shift + R`
   - Или: Настройки → Очистить кэш браузера
3. Прокрутите до раздела **"Противопоказания"**

---

## ✅ КАК ДОЛЖНО ВЫГЛЯДЕТЬ:

### На обычном телефоне (ширина 480px - 768px):
```
┌─────────────────────┬─────────────────────┐
│ [🔴] Постоянные     │ [🟡] Временные      │
│      Донорство      │      От месяца      │
│      невозможно     │      до года        │
│ • ВИЧ • Онкология   │ • Грипп • Операции  │
├─────────────────────┼─────────────────────┤
│ [🟢] После процедур │ [🔵] При приёме     │
│      Несколько      │      лекарств       │
│      дней/недель    │      Временно       │
│ • Татуировки        │ • Антибиотики       │
└─────────────────────┴─────────────────────┘
```
**2 колонки, 4 плашки в 2 ряда**

### На маленьком телефоне (ширина < 480px):
```
┌─────────────────────┐
│ [🔴] Постоянные     │
│      Донорство      │
│      невозможно     │
│ • ВИЧ • Онкология   │
├─────────────────────┤
│ [🟡] Временные      │
│      От месяца      │
│      до года        │
│ • Грипп • Операции  │
├─────────────────────┤
│ [🟢] После процедур │
│ ...                 │
└─────────────────────┘
```
**1 колонка, плашки друг под другом**

---

## 🔍 ЕСЛИ НЕ РАБОТАЕТ:

### Проблема 1: Старая версия CSS
```bash
# На сервере проверьте:
grep "grid-template-columns: repeat(2, 1fr)" /opt/tvoydonor/website/css/styles.css
```
Должна быть эта строка!

### Проблема 2: Кэш браузера
1. F12 (Developer Tools)
2. Network → Disable cache (поставить галочку)
3. Обновить страницу
4. Найти `styles.css?v=XXXXXX`
5. Открыть файл и найти `.contra-grid` в `@media (max-width: 768px)`
6. Должно быть `grid-template-columns: repeat(2, 1fr);`

### Проблема 3: Nginx не перезагрузился
```bash
ssh root@178.172.212.221
systemctl restart nginx
exit
```

---

## 📱 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА:

### В Chrome/Safari DevTools:
1. F12 → Elements
2. Найти `<div class="contra-grid">`
3. Посмотреть Computed → `grid-template-columns`
4. Должно быть: `271px 271px` (2 колонки) на телефоне
5. НЕ должно быть: `542px` (1 колонка)

---

**НАЧНИТЕ С ШАГА 1!** 🚀

После выполнения всех шагов напишите что получилось на телефоне.
