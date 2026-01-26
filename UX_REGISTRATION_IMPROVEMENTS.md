# 📋 НОВЫЕ ТРЕБОВАНИЯ: Улучшение UX регистрации

## 🎯 Задача

Улучшить процесс регистрации для доноров и медицентров.

---

## 📝 ТРЕБОВАНИЯ

### 1. Донор: Проверка дубликатов при регистрации

**Проблема:**
- Если донор с такими же данными уже существует, регистрация проходит без предупреждения
- Пользователь не понимает, что аккаунт уже создан

**Решение:**
```
Если при регистрации найден пользователь с:
- Тем же email
- Тем же телефоном
- Теми же ФИО + датой рождения

→ Показать модальное окно:
┌─────────────────────────────────────────────┐
│  ⚠️  Аккаунт уже существует                 │
├─────────────────────────────────────────────┤
│                                             │
│  Пользователь с такими данными уже          │
│  зарегистрирован в системе.                 │
│                                             │
│  Если это вы, попробуйте войти,             │
│  используя кнопку "Вход" ниже.              │
│                                             │
│  Если вы забыли пароль, свяжитесь с         │
│  поддержкой: support@tvoydonor.by           │
│                                             │
│  [ Перейти ко входу ]  [ Закрыть ]          │
└─────────────────────────────────────────────┘
```

---

### 2. Медцентр: Статус ожидания одобрения

**Проблема:**
- Медцентр регистрируется и попадает в статус `pending`
- Нет обратной связи о статусе заявки
- Непонятно, нужно ли регистрироваться заново после одобрения

**Решение A: Проверка статуса**

Добавить в форму входа медцентра кнопку "Проверить статус заявки":

```
┌─────────────────────────────────────────────┐
│  📋 Проверка статуса заявки                 │
├─────────────────────────────────────────────┤
│                                             │
│  Введите email, использованный при          │
│  регистрации:                               │
│                                             │
│  [_________________________________]        │
│                                             │
│  [ Проверить статус ]                       │
└─────────────────────────────────────────────┘

→ После проверки:

┌─────────────────────────────────────────────┐
│  ✅ Статус заявки: На рассмотрении          │
├─────────────────────────────────────────────┤
│                                             │
│  Ваша заявка на регистрацию медицинского    │
│  центра находится на рассмотрении.          │
│                                             │
│  📅 Дата подачи: 25.01.2026                 │
│  🏥 Название: ГУЗ "Полоцкая ЦГБ"            │
│  📧 Email: polotskcgb@gmail.com             │
│                                             │
│  ⏱️ Обычно рассмотрение занимает 1-2 дня.  │
│                                             │
│  ℹ️  После одобрения вы получите:          │
│     • Уведомление на email                  │
│     • Telegram уведомление (если привязан)  │
│                                             │
│  💡 Используйте те же учётные данные       │
│     для входа после одобрения.              │
│     НЕ РЕГИСТРИРУЙТЕСЬ ЗАНОВО!              │
│                                             │
│  [ Понятно ]                                │
└─────────────────────────────────────────────┘
```

**Решение B: Информационный баннер при регистрации**

После успешной регистрации медцентра показать:

```
┌─────────────────────────────────────────────┐
│  ✅ Заявка отправлена!                      │
├─────────────────────────────────────────────┤
│                                             │
│  Ваша заявка на регистрацию медицинского    │
│  центра успешно отправлена администратору.  │
│                                             │
│  📋 Что дальше?                             │
│                                             │
│  1. Администратор рассмотрит заявку в       │
│     течение 1-2 рабочих дней                │
│                                             │
│  2. Вы получите уведомление на email:       │
│     polotskcgb@gmail.com                    │
│                                             │
│  3. После одобрения используйте кнопку      │
│     "Вход" с теми же данными:               │
│     • Email: polotskcgb@gmail.com           │
│     • Пароль: ваш пароль                    │
│                                             │
│  ⚠️  ВАЖНО: НЕ регистрируйтесь заново!     │
│                                             │
│  🔗 Проверить статус заявки можно здесь:   │
│     [Проверить статус]                      │
│                                             │
│  [ На главную ]  [ Войти в аккаунт ]        │
└─────────────────────────────────────────────┘
```

---

### 3. Медцентр: Попытка входа с `pending` статусом

**Проблема:**
- Медцентр пытается войти, но статус `pending`
- Получает ошибку без объяснения

**Решение:**

При попытке входа с `pending` статусом показать:

```
┌─────────────────────────────────────────────┐
│  ⏱️  Заявка на рассмотрении                │
├─────────────────────────────────────────────┤
│                                             │
│  Ваша заявка на регистрацию медицинского    │
│  центра находится на рассмотрении           │
│  администратором.                           │
│                                             │
│  📋 Статус: Ожидает одобрения               │
│  📅 Дата подачи: 25.01.2026                 │
│  🏥 Название: ГУЗ "Полоцкая ЦГБ"            │
│                                             │
│  ℹ️  Вход будет доступен после одобрения   │
│     администратором (обычно 1-2 дня).       │
│                                             │
│  📧 Уведомление будет отправлено на:        │
│     polotskcgb@gmail.com                    │
│                                             │
│  По вопросам: support@tvoydonor.by          │
│                                             │
│  [ Понятно ]  [ Проверить статус ]          │
└─────────────────────────────────────────────┘
```

---

## 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Backend (app.py)

#### 1. API для проверки дубликатов донора

```python
@app.route('/api/check-donor-exists', methods=['POST'])
def check_donor_exists():
    """Проверить существование донора перед регистрацией"""
    data = request.json
    
    # Проверяем по email
    if data.get('email'):
        donor = query_db(
            "SELECT id, full_name, email FROM users WHERE email = %s",
            (data['email'],), one=True
        )
        if donor:
            return jsonify({
                'exists': True,
                'field': 'email',
                'message': 'Пользователь с таким email уже зарегистрирован'
            })
    
    # Проверяем по телефону
    if data.get('phone'):
        donor = query_db(
            "SELECT id, full_name, phone FROM users WHERE phone = %s",
            (data['phone'],), one=True
        )
        if donor:
            return jsonify({
                'exists': True,
                'field': 'phone',
                'message': 'Пользователь с таким телефоном уже зарегистрирован'
            })
    
    return jsonify({'exists': False})
```

#### 2. API для проверки статуса медцентра

```python
@app.route('/api/check-medcenter-status', methods=['POST'])
def check_medcenter_status():
    """Проверить статус заявки медцентра"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email обязателен'}), 400
    
    mc = query_db(
        """SELECT id, name, email, approval_status, created_at 
           FROM medical_centers WHERE email = %s""",
        (email,), one=True
    )
    
    if not mc:
        return jsonify({
            'found': False,
            'message': 'Медцентр с таким email не найден'
        })
    
    return jsonify({
        'found': True,
        'status': mc['approval_status'],
        'name': mc['name'],
        'email': mc['email'],
        'created_at': mc['created_at'].isoformat() if mc['created_at'] else None,
        'message': get_status_message(mc['approval_status'])
    })

def get_status_message(status):
    messages = {
        'pending': 'Ваша заявка находится на рассмотрении',
        'approved': 'Ваша заявка одобрена! Можете войти в систему',
        'rejected': 'К сожалению, ваша заявка отклонена. Свяжитесь с поддержкой'
    }
    return messages.get(status, 'Неизвестный статус')
```

#### 3. Улучшить обработку входа медцентра с `pending`

```python
@app.route('/api/medcenter/login', methods=['POST'])
def medcenter_login():
    # ... существующая логика ...
    
    # После проверки пароля:
    if mc['approval_status'] != 'approved':
        return jsonify({
            'error': 'pending_approval',
            'status': mc['approval_status'],
            'name': mc['name'],
            'email': mc['email'],
            'created_at': mc['created_at'].isoformat() if mc['created_at'] else None,
            'message': 'Ваша заявка находится на рассмотрении администратором'
        }), 403
    
    # ... остальная логика ...
```

---

### Frontend (auth.js)

#### 1. Проверка дубликатов при регистрации донора

```javascript
// При нажатии кнопки "Зарегистрироваться"
async function registerDonor() {
    const email = document.getElementById('donor-email').value;
    const phone = document.getElementById('donor-phone').value;
    
    // Проверяем дубликаты перед отправкой
    const checkResponse = await fetch(`${API_URL}/check-donor-exists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, phone })
    });
    
    const checkData = await checkResponse.json();
    
    if (checkData.exists) {
        showDuplicateModal(checkData.message);
        return;
    }
    
    // Продолжаем регистрацию...
}

function showDuplicateModal(message) {
    // Показываем модальное окно с предупреждением
    const modal = `
        <div class="modal-overlay">
            <div class="modal-content">
                <h3>⚠️ Аккаунт уже существует</h3>
                <p>${message}</p>
                <p>Если это вы, попробуйте войти.</p>
                <button onclick="switchToLogin()">Перейти ко входу</button>
                <button onclick="closeModal()">Закрыть</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);
}
```

#### 2. Баннер после регистрации медцентра

```javascript
async function registerMedcenter() {
    // ... существующая логика регистрации ...
    
    if (response.ok) {
        showPendingApprovalBanner(result.medical_center);
    }
}

function showPendingApprovalBanner(mc) {
    const banner = `
        <div class="success-banner">
            <h2>✅ Заявка отправлена!</h2>
            <div class="info-box">
                <h3>📋 Что дальше?</h3>
                <ol>
                    <li>Администратор рассмотрит заявку в течение 1-2 дней</li>
                    <li>Уведомление придёт на: ${mc.email}</li>
                    <li>После одобрения используйте кнопку "Вход"</li>
                </ol>
                <div class="warning">
                    ⚠️ ВАЖНО: НЕ регистрируйтесь заново!
                </div>
            </div>
            <button onclick="checkMedcenterStatus()">Проверить статус</button>
            <button onclick="goToLogin()">Войти в аккаунт</button>
        </div>
    `;
    // Показываем баннер
}
```

#### 3. Проверка статуса медцентра

```javascript
async function checkMedcenterStatus() {
    const email = prompt('Введите email, использованный при регистрации:');
    
    if (!email) return;
    
    const response = await fetch(`${API_URL}/check-medcenter-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    });
    
    const data = await response.json();
    
    if (data.found) {
        showStatusModal(data);
    } else {
        alert('Медцентр с таким email не найден');
    }
}

function showStatusModal(data) {
    let statusIcon = '';
    let statusText = '';
    
    if (data.status === 'pending') {
        statusIcon = '⏱️';
        statusText = 'На рассмотрении';
    } else if (data.status === 'approved') {
        statusIcon = '✅';
        statusText = 'Одобрено';
    } else if (data.status === 'rejected') {
        statusIcon = '❌';
        statusText = 'Отклонено';
    }
    
    const modal = `
        <div class="modal-overlay">
            <div class="modal-content">
                <h3>${statusIcon} Статус заявки: ${statusText}</h3>
                <p><strong>Название:</strong> ${data.name}</p>
                <p><strong>Email:</strong> ${data.email}</p>
                <p><strong>Дата подачи:</strong> ${formatDate(data.created_at)}</p>
                <p>${data.message}</p>
                ${data.status === 'pending' ? 
                    '<div class="info">💡 Используйте те же данные для входа после одобрения</div>' : 
                    ''}
                <button onclick="closeModal()">Понятно</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);
}
```

#### 4. Обработка входа с `pending` статусом

```javascript
async function loginMedcenter() {
    // ... существующая логика ...
    
    if (response.status === 403) {
        const errorData = await response.json();
        
        if (errorData.error === 'pending_approval') {
            showPendingApprovalModal(errorData);
            return;
        }
    }
    
    // ... остальная логика ...
}

function showPendingApprovalModal(data) {
    const modal = `
        <div class="modal-overlay">
            <div class="modal-content">
                <h3>⏱️ Заявка на рассмотрении</h3>
                <p>Ваша заявка находится на рассмотрении администратором.</p>
                <p><strong>Статус:</strong> Ожидает одобрения</p>
                <p><strong>Название:</strong> ${data.name}</p>
                <p><strong>Дата подачи:</strong> ${formatDate(data.created_at)}</p>
                <div class="info">
                    ℹ️ Вход будет доступен после одобрения (обычно 1-2 дня)
                </div>
                <button onclick="checkMedcenterStatus()">Проверить статус</button>
                <button onclick="closeModal()">Понятно</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modal);
}
```

---

## 📋 ПЛАН РЕАЛИЗАЦИИ

1. ✅ Backend API:
   - `/api/check-donor-exists` (POST)
   - `/api/check-medcenter-status` (POST)
   - Улучшить `/api/medcenter/login` (обработка `pending`)

2. ✅ Frontend (auth.js):
   - Проверка дубликатов при регистрации донора
   - Баннер после регистрации медцентра
   - Кнопка "Проверить статус заявки"
   - Модальные окна для всех сценариев

3. ✅ CSS стили:
   - `.success-banner`
   - `.modal-overlay`
   - `.modal-content`
   - `.info-box`
   - `.warning`

4. ✅ Тестирование:
   - Попытка регистрации с существующим email
   - Попытка регистрации с существующим телефоном
   - Проверка статуса `pending` медцентра
   - Попытка входа с `pending` статусом

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

✅ Донор видит предупреждение при дубликате
✅ Медцентр понимает, что заявка на рассмотрении
✅ Медцентр может проверить статус заявки
✅ Медцентр знает, что НЕ нужно регистрироваться заново
✅ Все сообщения понятные и информативные

---

**Готово к реализации после завершения задачи со статистикой!** 🚀
