# 🔍 ГЛУБОКОЕ ИССЛЕДОВАНИЕ: Проблемы мессенджера

## 📊 EXECUTIVE SUMMARY

**Статус:** 🔴 **КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ**

**Проблемы:**
1. ❌ **Несоответствие схемы БД и кода:** Таблица `chat_messages` использует старые названия колонок
2. ❌ **Клишированные сообщения отображаются не с той стороны**
3. ❌ **Несоответствие между backend и frontend** в названиях полей

---

## 🔍 ПРОБЛЕМА #1: Несоответствие схемы БД

### Текущая схема таблицы `chat_messages`:

```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER,
    sender_role VARCHAR(20) NOT NULL,  -- ❌ СТАРОЕ НАЗВАНИЕ!
    message TEXT NOT NULL,             -- ❌ СТАРОЕ НАЗВАНИЕ!
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Что использует backend (`app.py:2207-2217`):

```python
query_db(
    """INSERT INTO chat_messages 
       (conversation_id, sender_type, sender_id, message_type, message_text, created_at)
       VALUES (%s, %s, %s, %s, %s, NOW())""",  -- ❌ НЕСУЩЕСТВУЮЩИЕ КОЛОНКИ!
    (
        conversation['id'],
        'medcenter',            # sender_type ❌
        resp['medical_center_id'],
        'invitation',           # message_type ❌
        message_text            # message_text ❌
    ), commit=True
)
```

**❌ КРИТИЧЕСКАЯ ОШИБКА:** Backend пытается вставить в колонки `sender_type`, `message_type`, `message_text`, которых **НЕТ** в БД!

**Фактически в БД есть:**
- `sender_role` (не `sender_type`)
- `message` (не `message_text`)
- **НЕТ** колонки `message_type` вообще!

---

## 🔍 ПРОБЛЕМА #2: format_message возвращает неверные поля

### В `messaging_api.py:76-87`:

```python
def format_message(msg):
    """Форматировать сообщение для отправки клиенту"""
    return {
        'id': msg['id'],
        'conversation_id': msg['conversation_id'],
        'sender_id': msg.get('sender_id'),
        'sender_type': msg.get('sender_type'),  # ❌ В БД это sender_role!
        'content': msg.get('message_text'),      # ❌ В БД это message!
        'type': msg.get('message_type', 'text'), # ❌ Этой колонки вообще нет в БД!
        'is_read': msg.get('is_read', False),
        'created_at': msg['created_at'].isoformat() if msg.get('created_at') else None
    }
```

**❌ ОШИБКА:** Функция пытается получить поля которых нет в БД!

**Результат:** Frontend получает `undefined` для всех ключевых полей!

---

## 🔍 ПРОБЛЕМА #3: renderMessage работает с неверными данными

### В `messenger.js:388-428`:

```javascript
renderMessage(msg) {
    // Приводим userRole к формату БД: 'medical_center' → 'medcenter'
    const normalizedUserRole = this.userRole === 'medical_center' ? 'medcenter' : this.userRole;
    const isOwn = msg.sender_type === normalizedUserRole;  // ❌ msg.sender_type = undefined!
    const isSystem = msg.sender_type === 'system';
    
    const messageClass = isSystem ? 'system' : (isOwn ? 'own' : 'other');
    
    // ...
    
    return `
        <div class="message ${messageClass}">  <!-- ❌ Всегда 'other'! -->
            <div class="message-bubble">
                <div class="message-content">${this.formatMessageContent(msg.content)}</div>
                <!-- ❌ msg.content = undefined! -->
            </div>
        </div>
    `;
}
```

**❌ ПРОБЛЕМА:**
- `msg.sender_type` = `undefined` (потому что `format_message` возвращает `undefined`)
- `isOwn` всегда `false` → все сообщения отображаются как `'other'` (слева)
- `msg.content` = `undefined` → сообщения пустые!

---

## 🔍 ПРОБЛЕМА #4: renderNotificationMessage использует sender_role

### В `messenger.js:430-449`:

```javascript
renderNotificationMessage(msg) {
    const title = msg.type === 'invitation' ? '✅ Приглашение на донацию' : '📢 Уведомление';
    
    // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Определяем, своё ли это сообщение
    const isOwn = msg.sender_role === this.userRole;  // ❌ msg.sender_role тоже undefined!
    const messageClass = isOwn ? 'own' : 'other';
    
    return `
        <div class="message ${messageClass}">  <!-- ❌ Всегда 'other'! -->
            <div class="message-bubble message-notification">
                <div class="notification-header">
                    ${title}
                </div>
                <div class="notification-content">
                    ${this.formatMessageContent(msg.content)}  <!-- ❌ undefined! -->
                </div>
            </div>
        </div>
    `;
}
```

**❌ РЕЗУЛЬТАТ:** Клишированные сообщения (приглашения на донацию) **всегда** отображаются слева (как сообщения донора), хотя их отправляет медцентр!

---

## 📐 АРХИТЕКТУРА ТЕКУЩЕЙ СИСТЕМЫ

### Поток данных:

```
1. Медцентр подтверждает донора (update_response)
   ↓
2. Backend: INSERT INTO chat_messages (sender_type, message_type, message_text)
   ❌ ОШИБКА: Эти колонки НЕ СУЩЕСТВУЮТ в БД!
   ↓
3. БД: Вставка ПАДАЕТ или данные идут в неверные колонки
   ↓
4. Frontend запрашивает сообщения
   ↓
5. Backend: SELECT * FROM chat_messages WHERE conversation_id = ...
   Возвращает: { sender_role, message, ... }
   ↓
6. format_message пытается прочитать sender_type, message_text
   Возвращает: { sender_type: undefined, content: undefined }
   ↓
7. Frontend: renderMessage получает undefined поля
   Результат: Все сообщения отображаются слева, контент пустой
```

---

## 🎯 КОРНЕВАЯ ПРИЧИНА

**Было сделано неполное обновление системы:**

1. ✅ Frontend обновлён для работы с `sender_type`, `message_text`, `message_type`
2. ✅ `messaging_api.py` обновлён для форматирования этих полей
3. ✅ `app.py` обновлён для вставки этих полей
4. ❌ **НО!** Схема БД `chat_messages` **НЕ** была обновлена!

**Результат:** Backend пишет в несуществующие колонки, читает старые колонки, format_message возвращает undefined → фронт падает.

---

## ✅ РЕШЕНИЕ

### Шаг 1: Обновить схему БД

Нужно добавить миграцию для таблицы `chat_messages`:

```sql
-- Переименовать sender_role → sender_type
ALTER TABLE chat_messages RENAME COLUMN sender_role TO sender_type;

-- Переименовать message → message_text
ALTER TABLE chat_messages RENAME COLUMN message TO message_text;

-- Добавить колонку message_type
ALTER TABLE chat_messages ADD COLUMN message_type VARCHAR(50) DEFAULT 'text';

-- Добавить недостающие колонки для совместимости
ALTER TABLE chat_messages ADD COLUMN metadata JSONB;
ALTER TABLE chat_messages ADD COLUMN read_at TIMESTAMP;
ALTER TABLE chat_messages ADD COLUMN edited_at TIMESTAMP;
ALTER TABLE chat_messages ADD COLUMN deleted_at TIMESTAMP;
```

---

### Шаг 2: Обновить `format_message` (уже сделано ранее, но проверим)

```python
def format_message(msg):
    """Форматировать сообщение для отправки клиенту"""
    return {
        'id': msg['id'],
        'conversation_id': msg['conversation_id'],
        'sender_id': msg.get('sender_id'),
        'sender_type': msg['sender_type'],  # ✅ Будет работать после миграции
        'content': msg['message_text'],      # ✅ Будет работать после миграции
        'type': msg.get('message_type', 'text'),
        'is_read': msg.get('is_read', False),
        'created_at': msg['created_at'].isoformat() if msg.get('created_at') else None
    }
```

---

### Шаг 3: Обновить `renderNotificationMessage` в `messenger.js`

**Проблема:** Использует `msg.sender_role`, которого нет в ответе `format_message`

```javascript
renderNotificationMessage(msg) {
    const title = msg.type === 'invitation' ? '✅ Приглашение на донацию' : '📢 Уведомление';
    
    // ✅ ИСПРАВЛЕНО: Используем sender_type вместо sender_role
    const normalizedUserRole = this.userRole === 'medical_center' ? 'medcenter' : this.userRole;
    const isOwn = msg.sender_type === normalizedUserRole;
    const messageClass = isOwn ? 'own' : 'other';
    
    return `
        <div class="message ${messageClass}">
            <div class="message-bubble message-notification">
                <div class="notification-header">
                    ${title}
                </div>
                <div class="notification-content">
                    ${this.formatMessageContent(msg.content)}
                </div>
            </div>
        </div>
    `;
}
```

---

## 📝 PLAN ИСПРАВЛЕНИЯ

| Шаг | Действие | Файл | Статус |
|-----|----------|------|--------|
| 1 | Создать миграцию БД | `update_chat_messages_schema.sql` | ⏳ |
| 2 | Применить миграцию на сервере | SQL | ⏳ |
| 3 | Исправить `renderNotificationMessage` | `messenger.js` | ⏳ |
| 4 | Проверить `format_message` | `messaging_api.py` | ✅ (уже исправлено) |
| 5 | Проверить INSERT в `app.py` | `app.py` | ✅ (уже исправлено) |
| 6 | Деплой на сервер | Bash скрипт | ⏳ |
| 7 | Тестирование | Manual | ⏳ |

---

## 🧪 ТЕСТОВЫЕ СЦЕНАРИИ

### Тест 1: Обычное сообщение от донора

1. Донор отправляет: "Привет"
2. ✅ **Ожидается:** Сообщение справа (у донора), слева (у медцентра)

### Тест 2: Обычное сообщение от медцентра

1. Медцентр отправляет: "Здравствуйте"
2. ✅ **Ожидается:** Сообщение справа (у медцентра), слева (у донора)

### Тест 3: Клишированное сообщение (приглашение)

1. Медцентр подтверждает донора
2. Автоматически отправляется приглашение на донацию
3. ✅ **Ожидается:**
   - У медцентра: Сообщение **справа** (своё)
   - У донора: Сообщение **слева** (от медцентра)

### Тест 4: Содержимое сообщений

1. Любое сообщение
2. ✅ **Ожидается:** Текст отображается корректно (не `undefined`)

---

## 🚨 РИСКИ

| Риск | Вероятность | Последствия | Mitigation |
|------|-------------|-------------|------------|
| Миграция БД сломает существующие сообщения | ⚠️ Средняя | Потеря истории переписки | Бэкап БД перед миграцией |
| Несовместимость с существующими данными | 🟡 Низкая | Старые сообщения не отобразятся | Миграция данных с `UPDATE` |
| Несоответствие фронт/бэк после деплоя | 🟢 Очень низкая | Временные ошибки до обновления страниц | Cache-busting + уведомление юзерам |

---

## ✅ ИТОГ

**Найдено 4 критических несоответствия:**
1. ❌ Схема БД не обновлена (sender_role vs sender_type, message vs message_text)
2. ❌ Отсутствует колонка `message_type` в БД
3. ❌ `format_message` читает неверные поля из БД
4. ❌ `renderNotificationMessage` использует `sender_role` вместо `sender_type`

**Решение:**
1. Мигрировать схему БД
2. Исправить `renderNotificationMessage` в frontend
3. Задеплоить изменения

**Ожидаемый результат после фикса:**
- ✅ Сообщения от медцентра — **справа** (у медцентра), **слева** (у донора)
- ✅ Сообщения от донора — **справа** (у донора), **слева** (у медцентра)
- ✅ Клишированные сообщения отображаются корректно
- ✅ Контент сообщений не `undefined`

---

**Готов к исправлению! 🚀**
