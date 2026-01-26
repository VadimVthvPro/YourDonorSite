# 🔬 ГЛУБОКОЕ ИССЛЕДОВАНИЕ: Жизненный цикл донации (V2)

## 📊 EXECUTIVE SUMMARY

**Статус:** 🔴 **КРИТИЧЕСКАЯ ОШИБКА В МЕХАНИЗМЕ DONATION_HISTORY**

**Вы были правы!** Проблема не в схеме БД, а в **логике записи данных** при завершении донации!

---

## 🔄 ПРАВИЛЬНЫЙ ЖИЗНЕННЫЙ ЦИКЛ ДОНАЦИИ

### Шаг 1: Медцентр создаёт запрос крови

**Файл:** `app.py:1705-1764` (`POST /api/blood-requests`)

```python
# Медцентр создаёт запрос
INSERT INTO blood_requests (
    medical_center_id, blood_type, urgency, status,
    description, expires_at, needed_donors, current_donors
) VALUES (...)
```

**Статус запроса:** `status = 'active'`

**Уведомления:** Отправляются донорам через Telegram ✅

---

### Шаг 2: Доноры откликаются на запрос

**Файл:** `app.py:2799-2864` (`POST /api/donor/blood-requests/<id>/respond`)

```python
# Донор откликается
INSERT INTO donation_responses (
    request_id, user_id, medical_center_id,
    status, donor_comment
) VALUES (..., 'pending', ...)
```

**Статус отклика:** `status = 'pending'`

**Проверка:** Прошло ли 60 дней с последней донации ✅

---

### Шаг 3: Медцентр одобряет доноров

**ВАРИАНТ A:** Через `approved` статус (app.py:2890-3035)

```python
# Медцентр одобряет донора
UPDATE donation_responses 
SET status = 'approved',
    approved_at = NOW(),
    donation_date = ...,
    donation_time = ...
WHERE id = response_id
```

**ВАРИАНТ B:** Через `confirmed` статус (app.py:2060-2295)

```python
# Медцентр подтверждает донора
UPDATE donation_responses 
SET status = 'confirmed'
WHERE id = response_id
```

**При подтверждении:**
- ✅ Создаётся диалог (`conversations`)
- ✅ Отправляется приглашение в мессенджер
- ✅ Отправляется Telegram уведомление

---

### Шаг 4: 🔴 МЕДЦЕНТР ОТМЕЧАЕТ ДОНАЦИЮ КАК ВЫПОЛНЕННУЮ

**Файл:** `app.py:2060-2295` (`PUT /api/responses/<id>`)

```python
# Медцентр меняет статус на 'completed'
UPDATE donation_responses 
SET status = 'completed',
    donation_completed = TRUE,
    actual_donation_date = NOW()
WHERE id = response_id
```

**ЧТО ПРОИСХОДИТ:**

```python
if new_status == 'completed':
    # 1. Обновляем счётчики донора
    UPDATE users SET 
        last_donation_date = CURRENT_DATE, 
        total_donations = COALESCE(total_donations, 0) + 1,
        total_volume_ml = COALESCE(total_volume_ml, 0) + 450
    WHERE id = donor_id
    
    # 2. ❌ ПРОБЛЕМА: Вставляем в donation_history
    INSERT INTO donation_history (
        donor_id, medical_center_id, donation_date, 
        volume_ml, donation_type
    ) VALUES (...)
```

---

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА #1: Несоответствие схемы БД

### Текущий код (app.py:2143-2147):

```python
INSERT INTO donation_history 
(donor_id, medical_center_id, donation_date, volume_ml, donation_type, created_at)
VALUES (%s, %s, CURRENT_DATE, 450, 'blood', NOW())
```

### Схема БД (create_database.sql:325-334):

```sql
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,           -- ❌ НЕ donor_id!
    donation_date DATE NOT NULL,
    blood_center_id INTEGER,            -- ❌ НЕ medical_center_id!
    donation_type VARCHAR(50),
    volume_ml INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Результат:** `INSERT` **ПАДАЕТ** с ошибкой `column "donor_id" does not exist`! ❌

---

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА #2: Отсутствуют необходимые колонки

**Код вставляет:**
- `donor_id` (в БД: `user_id`)
- `medical_center_id` (в БД: `blood_center_id`)
- `donation_type` (✅ есть)
- `volume_ml` (✅ есть)
- `donation_date` (✅ есть)

**НЕ вставляет, но НУЖНО:**
- `blood_type` - для статистики медцентра!
- `status` - для фильтрации
- `response_id` - для связи с откликом

---

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА #3: Медцентр не получает статистику

**Статистика медцентра** (app.py:3797-3805):

```python
donations_stats = query_db("""
    SELECT 
        COUNT(*) as total_donations,
        COALESCE(SUM(volume_ml), 0) as total_volume_ml
    FROM donation_history dh
    JOIN users u ON dh.donor_id = u.id        -- ❌ donor_id не существует!
    WHERE dh.medical_center_id = %s           -- ❌ medical_center_id не существует!
    AND dh.donation_date BETWEEN %s AND %s
""", (medical_center_id, start_date, end_date), one=True)
```

**Результат:** Запрос **ПАДАЕТ** или возвращает 0! ❌

---

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА #4: Донор не получает статистику

**Статистика донора** (app.py:654-662):

```python
donations_history = query_db(
    """SELECT dh.*, mc.name as medical_center_name
       FROM donation_history dh
       LEFT JOIN medical_centers mc ON dh.medical_center_id = mc.id  -- ❌ НЕТ!
       WHERE dh.donor_id = %s  -- ❌ НЕТ!
       ORDER BY dh.donation_date DESC
       LIMIT 20""",
    (user_id,)
)
```

**Результат:** Запрос **ПАДАЕТ** или возвращает пустой список! ❌

---

## 🔴 НАЙДЕННАЯ ПРОБЛЕМА #5: Таймер 60 дней не работает

**Проверка при отклике** (app.py:2806-2826):

```python
# Получаем last_donation_date из таблицы users
donor = query_db(
    "SELECT last_donation_date FROM users WHERE id = %s",
    (user_id,), one=True
)

if donor and donor['last_donation_date']:
    days_since = (date.today() - last_date).days
    
    if days_since < 60:
        return jsonify({
            'error': f'Нельзя откликнуться! С последней донации прошло только {days_since} дней.'
        }), 403
```

**Проблема:** `last_donation_date` **обновляется** при `completed` (строка 2135), НО только если `INSERT INTO donation_history` **НЕ упадёт**!

**Если INSERT падает:**
- ❌ `last_donation_date` **НЕ обновляется** (транзакция откатывается)
- ❌ Донор **МОЖЕТ СРАЗУ** откликнуться снова
- ❌ Таймер 60 дней **НЕ РАБОТАЕТ**!

---

## ✅ РЕШЕНИЕ

### 1. Мигрировать схему donation_history

```sql
-- ПЕРЕИМЕНОВАТЬ КОЛОНКИ
ALTER TABLE donation_history RENAME COLUMN user_id TO donor_id;
ALTER TABLE donation_history RENAME COLUMN blood_center_id TO medical_center_id;

-- ДОБАВИТЬ НЕДОСТАЮЩИЕ КОЛОНКИ
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10);
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed';
ALTER TABLE donation_history ADD COLUMN IF NOT EXISTS response_id INTEGER REFERENCES donation_responses(id);

-- ЗАПОЛНИТЬ blood_type ИЗ ТАБЛИЦЫ users
UPDATE donation_history dh
SET blood_type = u.blood_type
FROM users u
WHERE dh.donor_id = u.id
AND dh.blood_type IS NULL;
```

---

### 2. Обновить код app.py (УЖЕ ИСПРАВЛЕНО!)

**Текущий код** (app.py:2143-2147) уже правильный:

```python
INSERT INTO donation_history 
(donor_id, medical_center_id, donation_date, volume_ml, donation_type, created_at)
VALUES (%s, %s, CURRENT_DATE, 450, 'blood', NOW())
```

✅ Использует `donor_id` и `medical_center_id`

**НО нужно добавить `blood_type`!**

---

### 3. Улучшить запись при `completed`

**НОВЫЙ КОД:**

```python
if new_status == 'completed':
    # Получаем группу крови донора
    donor = query_db(
        "SELECT blood_type FROM users WHERE id = %s",
        (resp['user_id'],), one=True
    )
    
    # 1. Обновляем счётчики донора
    query_db(
        """UPDATE users SET 
           last_donation_date = CURRENT_DATE, 
           total_donations = COALESCE(total_donations, 0) + 1,
           total_volume_ml = COALESCE(total_volume_ml, 0) + 450
           WHERE id = %s""",
        (resp['user_id'],), commit=True
    )
    
    # 2. Создаём запись в donation_history (С blood_type!)
    query_db(
        """INSERT INTO donation_history 
           (donor_id, medical_center_id, donation_date, blood_type, 
            volume_ml, donation_type, status, response_id, created_at)
           VALUES (%s, %s, CURRENT_DATE, %s, 450, 'blood', 'completed', %s, NOW())""",
        (resp['user_id'], resp['medical_center_id'], donor['blood_type'], response_id),
        commit=True
    )
    
    app.logger.info(f"✅ Донация добавлена: donor={resp['user_id']}, mc={resp['medical_center_id']}, blood_type={donor['blood_type']}")
```

---

## 📊 ПОТОК ДАННЫХ (ИСПРАВЛЕННЫЙ)

```
1. Медцентр создаёт запрос
   ↓
   INSERT INTO blood_requests (status='active')
   
2. Донор откликается
   ↓
   INSERT INTO donation_responses (status='pending')
   ↓
   Проверка: last_donation_date (60 дней) ✅
   
3. Медцентр одобряет
   ↓
   UPDATE donation_responses SET status='confirmed'
   ↓
   Создаётся диалог + уведомления ✅
   
4. Донор приходит и сдаёт кровь
   ↓
   Медцентр: UPDATE donation_responses SET status='completed'
   ↓
   4.1. UPDATE users SET last_donation_date, total_donations++ ✅
   4.2. INSERT INTO donation_history (donor_id, medical_center_id, blood_type) ✅
   ↓
   Таймер 60 дней ЗАПУЩЕН! ✅

5. Донор смотрит статистику
   ↓
   SELECT FROM donation_history WHERE donor_id=... ✅
   ↓
   Отображается история донаций + график ✅

6. Медцентр смотрит статистику
   ↓
   SELECT FROM donation_history WHERE medical_center_id=... ✅
   ↓
   Отображается количество донаций + диаграммы ✅
```

---

## 🧪 ТЕСТОВЫЙ СЦЕНАРИЙ

### Тест 1: Полный цикл донации

1. **Медцентр:** Создать запрос `O+`, срочность `urgent`
   - ✅ Запрос появляется у доноров `O+`
   
2. **Донор:** Откликнуться на запрос
   - ✅ Отклик создан, `status='pending'`
   
3. **Медцентр:** Одобрить донора
   - ✅ Статус → `confirmed`
   - ✅ Создан диалог
   - ✅ Уведомление отправлено
   
4. **Медцентр:** Отметить донацию как выполненную
   - ✅ Статус → `completed`
   - ✅ `users.last_donation_date` = сегодня
   - ✅ `users.total_donations` += 1
   - ✅ `users.total_volume_ml` += 450
   - ✅ `donation_history` получает новую запись
   
5. **Донор:** Попытаться откликнуться снова
   - ❌ Ошибка: "Прошло только X дней (минимум 60)"
   
6. **Донор:** Открыть статистику
   - ✅ Отображается последняя донация
   - ✅ График показывает 1 донацию
   - ✅ Таймер показывает "осталось 60 дней"
   
7. **Медцентр:** Открыть статистику
   - ✅ Количество донаций = 1
   - ✅ Диаграмма по группам крови: `O+` = 1
   - ✅ Объём крови = 450 мл

---

## 📋 ФАЙЛЫ ДЛЯ ИСПРАВЛЕНИЯ

| Файл | Что делать |
|------|-----------|
| `migrate_donation_history_schema.sql` | ✅ Уже создан |
| `app.py` строки 2143-2148 | 🔧 Добавить `blood_type`, `status`, `response_id` |
| `donor-dashboard.js` | ✅ Уже исправлен (вызов `loadDonationStatistics`) |

---

## ✅ ИТОГ

**Вы абсолютно правы!** Проблема была в:

1. ❌ **Несоответствие схемы БД** (`user_id` vs `donor_id`, `blood_center_id` vs `medical_center_id`)
2. ❌ **Отсутствие колонки `blood_type`** в `donation_history`
3. ❌ **INSERT падает** → транзакция откатывается → `last_donation_date` не обновляется → таймер не работает!

**Решение:**
1. Мигрировать БД (переименовать, добавить колонки)
2. Добавить `blood_type`, `status`, `response_id` в `INSERT INTO donation_history`
3. Frontend уже исправлен (вызывает `loadDonationStatistics`)

---

**Готов создать скрипт исправления! 🚀**
