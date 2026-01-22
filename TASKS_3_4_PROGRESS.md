# Задачи 3 и 4: Прогресс выполнения

## ✅ ЧТО СДЕЛАНО:

### 1. Система отправки сообщений донорам (Задача 3):

**Backend:**
- ✅ Таблица `messages` в БД (уже существовала)
- ✅ API POST `/api/messages` - отправка сообщения
- ✅ API GET `/api/messages` - получение сообщений донором
- ✅ API PUT `/api/messages/<id>/read` - отметить как прочитанное
- ✅ API GET `/api/messages/unread-count` - счётчик непрочитанных
- ✅ Автоматическая отправка уведомления в Telegram при новом сообщении

**Frontend (медцентр):**
- ✅ Модалка `#donor-modal` добавлена в HTML
- ✅ Функция `openContactModal()` - открытие модалки
- ✅ Функция `sendMessageToDonor()` - отправка через API
- ✅ Кнопка "Написать" в списке доноров (`renderDonors()`)
- ✅ Красивая форма с темой и текстом сообщения

**Frontend (донор):**
- ✅ Пункт меню "Сообщения" с badge непрочитанных
- ⏳ НЕ СДЕЛАНО: Секция `#messages` с отображением сообщений

---

## ⏳ ЧТО НУЖНО ДОДЕЛАТЬ:

### Задача 3 (осталось):
1. Добавить секцию `#messages` в `donor-dashboard.html`
2. Добавить функции в `donor-dashboard.js`:
   - `loadMessages()` - загрузка сообщений
   - `renderMessages()` - отображение
   - `markAsRead()` - отметка прочитанным
   - `updateMessagesBadge()` - обновление счётчика

### Задача 4: Уведомления донору об откликах и запросах:

**Что нужно:**
1. API для получения активных запросов крови (для донора)
2. Функция отклика на запрос (донор откликается → медцентр видит)
3. Таблица `donation_responses` для откликов
4. Отображение запросов в секции `#requests` донора
5. Telegram уведомление донору при новом запросе крови
6. Telegram уведомление медцентру при отклике донора

---

## 🎯 БЫСТРЫЙ ПЛАН ЗАВЕРШЕНИЯ:

### Шаг 1: Завершить Задачу 3 (10 минут)
```javascript
// В donor-dashboard.js добавить:
async function loadMessages() {
    const response = await fetch(`${API_URL}/messages`, {headers: getAuthHeaders()});
    const messages = await response.json();
    renderMessages(messages);
    updateMessagesBadge();
}

function renderMessages(messages) {
    const container = document.getElementById('messages-list');
    container.innerHTML = messages.map(msg => `
        <div class="message-card ${msg.is_read ? '' : 'unread'}" data-id="${msg.id}">
            <div class="message-header">
                <strong>${msg.sender_name || 'Медцентр'}</strong>
                <span>${formatDate(msg.created_at)}</span>
            </div>
            <div class="message-subject">${msg.subject || 'Без темы'}</div>
            <div class="message-body">${msg.message}</div>
        </div>
    `).join('');
    
    // Обработчик клика - отметить прочитанным
    container.querySelectorAll('.message-card.unread').forEach(card => {
        card.addEventListener('click', () => markAsRead(card.dataset.id));
    });
}

async function updateMessagesBadge() {
    const response = await fetch(`${API_URL}/messages/unread-count`, {headers: getAuthHeaders()});
    const data = await response.json();
    document.getElementById('messages-badge').textContent = data.unread;
}
```

### Шаг 2: Задача 4 (15 минут)
1. Создать таблицу откликов:
```sql
CREATE TABLE donation_responses (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES blood_requests(id),
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

2. API для донора:
```python
@app.route('/api/donor/blood-requests', methods=['GET'])
@require_auth('donor')
def get_donor_blood_requests():
    user_id = g.session['user_id']
    user = query_db("SELECT blood_type, district_id FROM users WHERE id = %s", (user_id,), one=True)
    
    requests = query_db("""
        SELECT br.*, mc.name as medical_center_name
        FROM blood_requests br
        JOIN medical_centers mc ON br.medical_center_id = mc.id
        WHERE br.blood_type = %s AND br.status = 'active'
        AND mc.district_id = %s
        ORDER BY br.created_at DESC
    """, (user['blood_type'], user['district_id']))
    
    return jsonify(requests or [])

@app.route('/api/donor/respond/<int:request_id>', methods=['POST'])
@require_auth('donor')
def respond_to_request(request_id):
    user_id = g.session['user_id']
    
    # Проверка дубликата
    existing = query_db(
        "SELECT id FROM donation_responses WHERE request_id = %s AND user_id = %s",
        (request_id, user_id), one=True
    )
    if existing:
        return jsonify({'error': 'Вы уже откликнулись'}), 400
    
    # Создаём отклик
    query_db(
        "INSERT INTO donation_responses (request_id, user_id) VALUES (%s, %s)",
        (request_id, user_id), commit=True
    )
    
    # Отправляем уведомление медцентру в Telegram
    # ...
    
    return jsonify({'message': 'Отклик отправлен'}), 201
```

---

## 📝 ТЕКУЩИЙ СТАТУС:

- [x] Задача 1: Telegram уведомления
- [x] Задача 2: Меню "Запросы крови"
- [🔄] Задача 3: Отправка сообщений (90% готово, осталось отображение у донора)
- [ ] Задача 4: Отклики на запросы
- [x] Задача 5: Сохранение сессии

---

## 🚀 ЧТО УЖЕ РАБОТАЕТ:

1. Медцентр может написать донору через кнопку "Написать"
2. Сообщение сохраняется в БД
3. Донору приходит уведомление в Telegram
4. API для получения сообщений готов

## 🔧 ЧТО ОСТАЛОСЬ:

1. Отобразить сообщения в личном кабинете донора
2. Создать систему откликов на запросы крови
3. Добавить отображение активных запросов донору
4. Двусторонние уведомления (донор → медцентр)
