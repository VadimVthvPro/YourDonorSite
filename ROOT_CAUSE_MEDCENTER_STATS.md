# 🚨 НАЙДЕНА КОРНЕВАЯ ПРИЧИНА!

## ❌ ПРОБЛЕМА:

### `/api/stats/medcenter` (главная панель):

**Строки 2518-2520:**
```python
donors_count = query_db(
    "SELECT COUNT(*) as count FROM users WHERE medical_center_id = %s AND is_active = TRUE",
    (mc_id,), one=True
)
```

**ОШИБКА:** Доноры **НЕ ПРИВЯЗАНЫ** к медцентрам! У `users` **НЕТ** колонки `medical_center_id`!

**Результат:** `donors_count = 0` ❌

---

### `/api/medical-center/statistics` (раздел "Статистика"):

**Строки 3757-3802:** Правильно считает уникальных доноров из `donation_responses`:

```python
responses_stats = query_db("""
    SELECT 
        COUNT(DISTINCT dr.user_id) as unique_donors,  # ✅ ПРАВИЛЬНО!
        ...
    FROM donation_responses dr
    JOIN blood_requests br ON dr.request_id = br.id
    WHERE br.medical_center_id = %s
""")
```

**НО:** Фильтруется по `period` (дата создания отклика)!

---

## ✅ РЕШЕНИЕ:

### **1. Исправить `/api/stats/medcenter`:**

**Было (строка 2518):**
```python
donors_count = query_db(
    "SELECT COUNT(*) as count FROM users WHERE medical_center_id = %s AND is_active = TRUE",
    (mc_id,), one=True
)
```

**Должно быть:**
```python
# Уникальные доноры, которые откликались на запросы медцентра
donors_count = query_db(
    """SELECT COUNT(DISTINCT dr.user_id) as count 
       FROM donation_responses dr
       JOIN blood_requests br ON dr.request_id = br.id
       WHERE br.medical_center_id = %s""",
    (mc_id,), one=True
)
```

### **2. Исправить `/api/medical-center/statistics` (period):**

**Frontend уже исправлен:** `currentStatsperiod = 'all'` ✅

**НО:** Нужно также убрать фильтр по дате для `blood_requests.total`!

---

## 📊 ОЖИДАЕМЫЕ ЗНАЧЕНИЯ ПОСЛЕ ИСПРАВЛЕНИЯ:

### **Главная панель (`/api/stats/medcenter`):**
- `total_donors`: 4 (уникальных доноров, откликавшихся на запросы)
- `active_requests`: 0 (нет активных)
- `pending_responses`: 1 (есть ожидающие)
- `month_donations`: 1 (донация за текущий месяц)

### **Раздел "Статистика" (`/api/medical-center/statistics?period=all`):**
- `blood_requests.total`: 28 ✅
- `responses.unique_donors`: 4 ✅
- `donations.total`: 1 ✅

---

## 🔧 КОД ИСПРАВЛЕНИЯ:

### **Файл:** `website/backend/app.py`

**Строки 2513-2555:**

```python
@app.route('/api/stats/medcenter', methods=['GET'])
@require_auth('medcenter')
def get_medcenter_stats():
    mc_id = g.session['medical_center_id']
    
    # ✅ ИСПРАВЛЕНО: Уникальные доноры из donation_responses
    donors_count = query_db(
        """SELECT COUNT(DISTINCT dr.user_id) as count 
           FROM donation_responses dr
           JOIN blood_requests br ON dr.request_id = br.id
           WHERE br.medical_center_id = %s""",
        (mc_id,), one=True
    )
    
    active_requests = query_db(
        "SELECT COUNT(*) as count FROM blood_requests WHERE medical_center_id = %s AND status = 'active'",
        (mc_id,), one=True
    )
    
    pending_responses = query_db(
        "SELECT COUNT(*) as count FROM donation_responses WHERE medical_center_id = %s AND status = 'pending'",
        (mc_id,), one=True
    )
    
    # Донации за текущий месяц
    from datetime import datetime, timedelta
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_donations = query_db(
        """SELECT COUNT(*) as count FROM donation_history 
           WHERE medical_center_id = %s AND donation_date >= %s""",
        (mc_id, start_of_month), one=True
    )
    
    # ✅ ИСПРАВЛЕНО: Доноры по группам крови из donation_responses
    donors_by_blood = query_db(
        """SELECT u.blood_type, COUNT(DISTINCT dr.user_id) as count 
           FROM donation_responses dr
           JOIN blood_requests br ON dr.request_id = br.id
           JOIN users u ON dr.user_id = u.id
           WHERE br.medical_center_id = %s AND u.blood_type IS NOT NULL
           GROUP BY u.blood_type""",
        (mc_id,)
    )
    
    return jsonify({
        'total_donors': donors_count['count'],
        'active_requests': active_requests['count'],
        'pending_responses': pending_responses['count'],
        'month_donations': month_donations['count'],
        'donors_by_blood_type': {item['blood_type']: item['count'] for item in donors_by_blood}
    })
```

---

## 🚀 ДЕПЛОЙ:

1. Исправить `app.py` (строки 2518-2546)
2. Загрузить на сервер
3. Перезапустить API
4. Тестировать

---

**ЭТО КОРНЕВАЯ ПРИЧИНА!** Главная панель считала доноров неправильно!
