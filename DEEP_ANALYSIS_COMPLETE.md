# 🔬 ПОЛНОЕ ГЛУБОКОЕ ИССЛЕДОВАНИЕ СТАТИСТИКИ

## 📋 ПРОБЛЕМЫ

1. **У медцентра: "0 Запросов крови" и "0 Уникальных доноров"** (хотя запросов много)
2. **У донора: Статистика не обновляется** после завершения донации

---

## 🔍 ПУТЬ ДАННЫХ: ОТ ЗАПРОСА ДО СТАТИСТИКИ

### БЛОК 1: СОЗДАНИЕ ЗАПРОСА КРОВИ
**Эндпоинт:** `POST /api/blood-requests`  
**Таблица:** `blood_requests`
- Медцентр создаёт запрос
- Запись добавляется в `blood_requests` со `status='active'`

### БЛОК 2: ДОНОР ОТКЛИКАЕТСЯ
**Эндпоинт:** `POST /api/donor/blood-requests/<id>/respond`  
**Код:** `website/backend/app.py:2823`  
**Таблица:** `donation_responses`
- Донор откликается
- Создаётся запись в `donation_responses`:
  - `user_id` = ID донора
  - `request_id` = ID запроса
  - `medical_center_id` = ID медцентра (из запроса)
  - `status='pending'`

### БЛОК 3: МЕДЦЕНТР ПОДТВЕРЖДАЕТ
**Эндпоинт:** `PUT /api/responses/<id>`  
**Код:** `website/backend/app.py:2058-2165`  
**Таблица:** `donation_responses`
- Медцентр меняет статус на `'confirmed'`
- **ВАЖНО:** При `status='completed'` (строка 2131):
  - Обновляет `users.total_donations`, `users.last_donation_date`, `users.total_volume_ml`
  - Создаёт запись в `donation_history`

### БЛОК 4: КНОПКА "ВЫПОЛНЕН" (Ключевой момент!)
**Frontend:** `website/js/medcenter-dashboard.js:1131-1191`  
**Функция:** `fulfillRequest(requestId)`
**Что происходит:**
1. Получает все отклики со `status='confirmed'`
2. **ДЛЯ КАЖДОГО** подтверждённого отклика вызывает:
   - `POST /api/medical-center/donations` (строка 1157)
3. Обновляет статус запроса на `'fulfilled'`:
   - `PUT /api/blood-requests/<id>` с `status='fulfilled'`

**Эндпоинт:** `POST /api/medical-center/donations`  
**Код:** `website/backend/app.py:1995-2056`  
**Что делает:**
1. Вставляет запись в `donation_history` (строка 2029-2035)
2. Обновляет `users.total_donations`, `users.last_donation_date`, `users.total_volume_ml` (строка 2037-2046)
3. Если есть `response_id`, обновляет `donation_responses.status='completed'` (строка 2048-2056)

---

## 📊 СТАТИСТИКА МЕДЦЕНТРА

### ЭНДПОИНТ 1: `/api/stats/medcenter`
**Код:** `website/backend/app.py:2513-2563`  
**Что возвращает:**
- `total_donors`: COUNT DISTINCT user_id из `donation_responses` (через JOIN с `blood_requests`)
- `active_requests`: COUNT из `blood_requests` где `status='active'`
- `pending_responses`: COUNT из `donation_responses` где `status='pending'`
- `month_donations`: COUNT из `donation_history` за текущий месяц

### ЭНДПОИНТ 2: `/api/medical-center/statistics?period=all`
**Код:** `website/backend/app.py:3721-3901`  
**Что возвращает:**
- `blood_requests.total`: COUNT из `blood_requests` за период
- `responses.unique_donors`: COUNT DISTINCT user_id из `donation_responses`
- `donations.total`: COUNT из `donation_history` за период

**Frontend вызывает:** `medcenter-dashboard.js` → `loadStatistics()`

---

## 📊 СТАТИСТИКА ДОНОРА

### ЭНДПОИНТ: `/api/donor/statistics`
**Код:** `website/backend/app.py:615-740`  
**Что возвращает:**
- `total_donations`: из `users.total_donations`
- `total_volume_ml`: из `users.total_volume_ml`
- `last_donation_date`: из `users.last_donation_date`
- `donations_history`: SELECT из `donation_history` WHERE `donor_id=user_id`

**Frontend вызывает:** `donor-dashboard.js` → `loadDonationStatistics()`

---

## ⚠️ НАЙДЕННЫЕ ПРОБЛЕМЫ

### ПРОБЛЕМА 1: Запросы "0 ЗАПРОСОВ КРОВИ"
**SQL запрос:** (app.py:3766-3780)
```sql
SELECT COUNT(*) as total
FROM blood_requests
WHERE medical_center_id = %s
AND created_at::date BETWEEN %s AND %s
```

**Проблема:** Frontend по умолчанию отправляет `period='month'`  
**Решение:** Изменить на `period='all'` ИЛИ убрать фильтр по дате для `blood_requests.total`

### ПРОБЛЕМА 2: "0 УНИКАЛЬНЫХ ДОНОРОВ"
**SQL запрос:** (app.py:3800-3811)
```sql
SELECT COUNT(DISTINCT dr.user_id) as unique_donors
FROM donation_responses dr
JOIN blood_requests br ON dr.request_id = br.id
WHERE br.medical_center_id = %s
AND dr.created_at::date BETWEEN %s AND %s
```

**Проблема:** Фильтр по датам `dr.created_at BETWEEN start_date AND end_date`  
**Если `period='month'`**, а отклики были давно → покажет 0

**Решение:** 
1. Для главного меню (карточки) использовать `period='all'`
2. ИЛИ в `/api/stats/medcenter` убрать фильтр по датам для `total_donors` и `active_requests`

### ПРОБЛЕМА 3: Статистика донора не обновляется

**Потенциальные причины:**

#### 3.1. `fulfillRequest` не отправляет `response_id`
Смотрю код `medcenter-dashboard.js:1157-1168`:
```javascript
await fetch(`${MC_API_URL}/medical-center/donations`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
        donor_id: resp.user_id,
        blood_type: resp.donor_blood_type || request.blood_type,
        volume_ml: 450,
        donation_date: new Date().toISOString().split('T')[0],
        response_id: resp.id,  // ✅ ЕСТЬ!
        notes: `Донация по запросу #${requestId}`
    })
});
```
✅ `response_id` передаётся!

#### 3.2. Backend не обновляет `users` при INSERT в `donation_history`
Смотрю `app.py:2037-2046`:
```python
# Обновляем статистику донора в таблице users
query_db(
    """UPDATE users SET 
       total_donations = COALESCE(total_donations, 0) + 1,
       last_donation_date = %s,
       total_volume_ml = COALESCE(total_volume_ml, 0) + %s
       WHERE id = %s""",
    (donation_date, volume_ml, donor_id),
    commit=True
)
```
✅ Обновление есть!

#### 3.3. Дублирование: `update_response` ТОЖЕ обновляет `users` при `status='completed'`
Смотрю `app.py:2131-2164`:
- При `PUT /api/responses/<id>` с `status='completed'`:
  - Обновляет `users` (строка 2147-2154)
  - Вставляет в `donation_history` (строка 2157-2164)

**ВОЗМОЖНЫЙ БАГ:**
- `fulfillRequest` вызывает `POST /api/medical-center/donations`
- Затем, если есть `response_id`, backend вызывает `UPDATE donation_responses SET status='completed'`
- НО! Эндпоинт `PUT /api/responses/<id>` срабатывает ОТДЕЛЬНО, если медцентр вручную меняет статус

**РИСК ДУБЛИРОВАНИЯ:**
- Если `POST /api/medical-center/donations` создаёт donation_history
- И `PUT /api/responses/<id>` ТОЖЕ создаёт donation_history
- → Будет 2 записи!

#### 3.4. Проверка: Вызывает ли кнопка "Выполнен" правильный эндпоинт?
Смотрю `medcenter-dashboard.js:1062`:
```javascript
<button class="btn btn-primary btn-sm" onclick="fulfillRequest(${req.id})">
    Выполнен
</button>
```
✅ Правильно!

---

## 🔧 ЧТО НУЖНО ПРОВЕРИТЬ НА СЕРВЕРЕ

### 1. Есть ли данные в `blood_requests`?
```sql
SELECT COUNT(*), status FROM blood_requests WHERE medical_center_id=10 GROUP BY status;
```

### 2. Есть ли данные в `donation_responses`?
```sql
SELECT COUNT(*), status FROM donation_responses WHERE medical_center_id=10 GROUP BY status;
```

### 3. Есть ли данные в `donation_history`?
```sql
SELECT COUNT(*), donor_id FROM donation_history WHERE medical_center_id=10 GROUP BY donor_id;
```

### 4. Обновлена ли таблица `users` у доноров?
```sql
SELECT id, email, total_donations, last_donation_date, total_volume_ml 
FROM users 
WHERE role='donor' 
ORDER BY id;
```

### 5. Есть ли "потерянные" донации (responses completed БЕЗ donation_history)?
```sql
SELECT dr.id, dr.user_id, dr.status, dh.id as history_id
FROM donation_responses dr
LEFT JOIN donation_history dh ON dr.id = dh.response_id
WHERE dr.status IN ('completed', 'confirmed')
  AND dh.id IS NULL;
```

---

## 🎯 РЕШЕНИЯ

### РЕШЕНИЕ 1: Исправить "0 запросов" и "0 доноров" в меню медцентра

**Файл:** `website/backend/app.py`  
**Эндпоинт:** `/api/stats/medcenter` (строка 2513)

**Изменить:**
```python
# Уникальные доноры ЗА ВСЁ ВРЕМЯ (убрать фильтр по дате)
donors_count = query_db(
    """SELECT COUNT(DISTINCT dr.user_id) as count 
       FROM donation_responses dr
       JOIN blood_requests br ON dr.request_id = br.id
       WHERE br.medical_center_id = %s""",
    (mc_id,), one=True
)

# Все запросы ЗА ВСЁ ВРЕМЯ (не только active)
total_requests = query_db(
    "SELECT COUNT(*) as count FROM blood_requests WHERE medical_center_id = %s",
    (mc_id,), one=True
)
```

### РЕШЕНИЕ 2: Проверить, что `fulfillRequest` корректно работает

**Проверка на сервере:**
1. Посмотреть логи API во время нажатия "Выполнен"
2. Проверить, появляются ли записи в `donation_history`
3. Проверить, обновляется ли `users.total_donations`

### РЕШЕНИЕ 3: Добавить логирование в критические точки

**В `record_donation`:**
```python
app.logger.info(f"✅ Донация записана: donor_id={donor_id}, mc={mc_id}, blood_type={blood_type}, response_id={response_id}")
```

**В `update_response`:**
```python
app.logger.info(f"✅ Статус отклика обновлён: response_id={response_id}, new_status={new_status}")
if new_status == 'completed':
    app.logger.info(f"✅ Донация добавлена в историю через update_response")
```

---

## 📝 СЛЕДУЮЩИЕ ШАГИ

1. **Выполнить SQL запросы на сервере** (пункты 1-5 выше)
2. **Найти корневую причину** (нет данных? данные есть, но фильтры неверные?)
3. **Исправить код** (в зависимости от причины)
4. **Протестировать** весь цикл от создания запроса до статистики
