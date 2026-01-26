# 🔬 ГЛУБОКОЕ ИССЛЕДОВАНИЕ: Проблемы со статистикой

## 📊 EXECUTIVE SUMMARY

**Статус:** 🔴 **КРИТИЧЕСКИЕ НЕСООТВЕТСТВИЯ ОБНАРУЖЕНЫ**

**Найдено 3 критических проблемы:**
1. ❌ **Несоответствие схемы БД и кода:** `user_id` vs `donor_id` в таблице `donation_history`
2. ❌ **Отсутствие колонки `medical_center_id`** в схеме БД
3. ❌ **Frontend не вызывает `loadDonationStatistics()`** при инициализации

---

## 🔍 ПРОБЛЕМА #1: Несоответствие схемы БД donation_history

### Схема БД (create_database.sql:325-334):

```sql
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),  -- ❌ СТАРОЕ НАЗВАНИЕ
    donation_date DATE NOT NULL,
    blood_center_id INTEGER REFERENCES medical_centers(id),  -- ❌ НЕВЕРНОЕ НАЗВАНИЕ
    donation_type VARCHAR(50),
    volume_ml INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Что использует backend (app.py:654-662):

```python
donations_history = query_db(
    """SELECT dh.*, mc.name as medical_center_name
       FROM donation_history dh
       LEFT JOIN medical_centers mc ON dh.medical_center_id = mc.id  -- ❌ НЕТ ТАКОЙ КОЛОНКИ!
       WHERE dh.donor_id = %s  -- ❌ НЕТ ТАКОЙ КОЛОНКИ!
       ORDER BY dh.donation_date DESC
       LIMIT 20""",
    (user_id,)
)
```

**❌ КРИТИЧЕСКАЯ ОШИБКА:** Backend пытается читать из колонок `donor_id` и `medical_center_id`, которых **НЕТ** в БД!

**Фактически в БД есть:**
- `user_id` (не `donor_id`)
- `blood_center_id` (не `medical_center_id`)
- **НЕТ** колонок: `blood_type`, `status`, `response_id`

---

## 🔍 ПРОБЛЕМА #2: Backend INSERT использует несуществующие колонки

### В app.py:2029-2035 (запись донации):

```python
query_db(
    """INSERT INTO donation_history 
       (donor_id, medical_center_id, donation_date, blood_type, volume_ml, status, notes, response_id)
       VALUES (%s, %s, %s, %s, %s, 'completed', %s, %s)""",
    (donor_id, mc_id, donation_date, blood_type, volume_ml, notes, response_id),
    commit=True
)
```

**❌ ОШИБКА:** Пытается вставить в колонки:
- `donor_id` → НЕТ в БД (есть `user_id`)
- `medical_center_id` → НЕТ в БД (есть `blood_center_id`)
- `blood_type` → НЕТ в БД
- `status` → НЕТ в БД
- `response_id` → НЕТ в БД

**Результат:** Вставка **ПАДАЕТ** с ошибкой!

---

## 🔍 ПРОБЛЕМА #3: Frontend не вызывает loadDonationStatistics()

### В donor-dashboard.js:11-47:

```javascript
document.addEventListener('DOMContentLoaded', async function() {
    const isAuth = await checkAuthAndRestore();
    
    if (!isAuth) {
        window.location.href = 'auth.html';
        return;
    }
    
    // Асинхронная загрузка данных
    (async () => {
        try {
            await loadUserDataFromAPI();
            await Promise.all([
                loadRequestsFromAPI(),
                loadDonateCenters()
            ]);
            
            initMessenger();
        } catch (e) {
            console.error('✗ Ошибка загрузки данных:', e);
        }
    })();
});
```

**❌ ПРОБЛЕМА:** `loadDonationStatistics()` **НЕ ВЫЗЫВАЕТСЯ** при инициализации!

**Функция существует** (строка 2080), но никогда не выполняется!

---

## 📐 ПОТОК ДАННЫХ (ТЕКУЩИЙ vs ОЖИДАЕМЫЙ)

### ТЕКУЩИЙ (сломан):

```
1. Медцентр помечает донацию как "completed"
   ↓
2. app.py:2142: INSERT INTO donation_history (donor_id, medical_center_id, ...)
   ❌ ОШИБКА: column "donor_id" does not exist
   ↓
3. Вставка ПАДАЕТ → данные НЕ попадают в БД
   ↓
4. Frontend запрашивает статистику
   ↓
5. app.py:654: SELECT ... WHERE dh.donor_id = %s
   ❌ ОШИБКА: column "donor_id" does not exist
   ↓
6. Запрос ПАДАЕТ → возвращается пустой ответ
   ↓
7. Frontend: stats.donations_history = [] → ПУСТО ❌
```

### ОЖИДАЕМЫЙ (после исправления):

```
1. Медцентр помечает донацию как "completed"
   ↓
2. INSERT INTO donation_history (user_id, blood_center_id, ...)
   ✅ Успешно вставлено
   ↓
3. UPDATE users SET total_donations = total_donations + 1
   ✅ Счётчик увеличен
   ↓
4. Frontend вызывает loadDonationStatistics()
   ↓
5. SELECT ... FROM donation_history WHERE user_id = ...
   ✅ Возвращает данные
   ↓
6. Frontend рендерит статистику
   ✅ Всё отображается! 🎉
```

---

## ✅ РЕШЕНИЕ

### Шаг 1: Мигрировать схему БД

Нужно привести `donation_history` в соответствие с кодом:

```sql
-- МИГРАЦИЯ: donation_history
-- Цель: Привести схему в соответствие с backend

-- 1. Переименовать user_id → donor_id (для единообразия)
ALTER TABLE donation_history 
RENAME COLUMN user_id TO donor_id;

-- 2. Переименовать blood_center_id → medical_center_id
ALTER TABLE donation_history 
RENAME COLUMN blood_center_id TO medical_center_id;

-- 3. Добавить недостающие колонки
ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10);

ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed';

ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS response_id INTEGER REFERENCES donation_responses(id);

ALTER TABLE donation_history 
ADD COLUMN IF NOT EXISTS donation_type VARCHAR(50) DEFAULT 'blood';

-- 4. Обновить индексы
CREATE INDEX IF NOT EXISTS idx_donation_history_donor ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_medcenter ON donation_history(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_response ON donation_history(response_id);

-- 5. Мигрировать существующие данные (заполнить blood_type из users)
UPDATE donation_history dh
SET blood_type = u.blood_type
FROM users u
WHERE dh.donor_id = u.id
AND dh.blood_type IS NULL;
```

---

### Шаг 2: Обновить frontend (вызывать статистику)

**Файл:** `website/js/donor-dashboard.js`

```javascript
document.addEventListener('DOMContentLoaded', async function() {
    const isAuth = await checkAuthAndRestore();
    
    if (!isAuth) {
        window.location.href = 'auth.html';
        return;
    }
    
    // Асинхронная загрузка данных
    (async () => {
        try {
            await loadUserDataFromAPI();
            
            await Promise.all([
                loadRequestsFromAPI(),
                loadDonateCenters(),
                loadDonationStatistics()  // ✅ ДОБАВИТЬ ЭТУ СТРОКУ!
            ]);
            
            initMessenger();
        } catch (e) {
            console.error('✗ Ошибка загрузки данных:', e);
        }
    })();
});
```

---

### Шаг 3: Проверить app.py (уже исправлено ранее)

В app.py:2142-2148 уже есть правильный INSERT:

```python
query_db(
    """INSERT INTO donation_history 
       (donor_id, medical_center_id, donation_date, volume_ml, donation_type, created_at)
       VALUES (%s, %s, CURRENT_DATE, 450, 'blood', NOW())""",
    (resp['user_id'], resp['medical_center_id']), commit=True
)
```

✅ Это нужно оставить как есть (после миграции БД заработает)

---

## 📝 PLAN ИСПРАВЛЕНИЯ

| Шаг | Действие | Файл | Статус |
|-----|----------|------|--------|
| 1 | Создать SQL миграцию | `migrate_donation_history.sql` | ⏳ |
| 2 | Применить миграцию на сервере | SQL | ⏳ |
| 3 | Обновить donor-dashboard.js | `donor-dashboard.js` | ⏳ |
| 4 | Проверить медцентр статистику | `medcenter-dashboard.js` | ⏳ |
| 5 | Деплой на сервер | Bash скрипт | ⏳ |
| 6 | Тестирование | Manual | ⏳ |

---

## 🧪 ТЕСТОВЫЕ СЦЕНАРИИ

### Тест 1: Проверка БД после миграции

```sql
-- Проверяем схему
\d donation_history

-- Должны увидеть:
-- - donor_id (вместо user_id) ✅
-- - medical_center_id (вместо blood_center_id) ✅
-- - blood_type ✅
-- - status ✅
-- - response_id ✅
```

### Тест 2: Запись донации (медцентр)

1. Медцентр отмечает донацию как "completed"
2. ✅ **Ожидается:** Запись успешно вставляется в `donation_history`
3. Проверка в БД:
   ```sql
   SELECT * FROM donation_history ORDER BY created_at DESC LIMIT 1;
   ```

### Тест 3: Статистика донора

1. Донор заходит в раздел "Статистика"
2. ✅ **Ожидается:**
   - Общее количество донаций
   - История донаций (таблица)
   - График по месяцам
   - Уровень донора
   - Достижения

### Тест 4: Статистика медцентра

1. Медцентр заходит в раздел "Статистика"
2. ✅ **Ожидается:**
   - Количество донаций за период
   - График по группам крови
   - Диаграмма по срочности запросов

---

## 🔄 ОТКАТ (если нужно)

```sql
-- Создаём резервную копию ПЕРЕД миграцией:
CREATE TABLE donation_history_backup AS SELECT * FROM donation_history;

-- Для отката:
DROP TABLE donation_history;
ALTER TABLE donation_history_backup RENAME TO donation_history;
```

---

## ✅ ИТОГ

**Найдено 3 критических несоответствия:**
1. ❌ `user_id` vs `donor_id`
2. ❌ `blood_center_id` vs `medical_center_id`
3. ❌ Отсутствуют колонки: `blood_type`, `status`, `response_id`
4. ❌ Frontend не вызывает `loadDonationStatistics()`

**Решение:**
1. Мигрировать схему БД (переименовать, добавить колонки)
2. Обновить frontend (вызывать статистику)
3. Задеплоить изменения

**Ожидаемый результат:**
- ✅ Донации записываются в БД
- ✅ Статистика загружается корректно
- ✅ Всё отображается для донора и медцентра

---

**Готов к исправлению! 🚀**
