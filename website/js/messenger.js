/**
 * СИСТЕМА СООБЩЕНИЙ - JavaScript
 * Полноценный мессенджер для донора
 */

const MessengerAPI = {
    // Используем глобальный API URL из config.js
    get baseURL() {
        return window.API_URL || `${window.location.protocol}//${window.location.hostname}:5001/api`;
    },
    
    getToken() {
        return localStorage.getItem('auth_token');
    },
    
    headers() {
        return {
            'Authorization': `Bearer ${this.getToken()}`,
            'Content-Type': 'application/json'
        };
    },
    
    // Получить список диалогов
    async getConversations(status = 'active') {
        const response = await fetch(`${this.baseURL}/messages/conversations?status=${status}`, {
            headers: this.headers()
        });
        if (!response.ok) throw new Error('Ошибка загрузки диалогов');
        return await response.json();
    },
    
    // Получить сообщения в диалоге
    async getMessages(conversationId, beforeId = null) {
        let url = `${this.baseURL}/messages/conversations/${conversationId}/messages?limit=50`;
        if (beforeId) url += `&before_id=${beforeId}`;
        
        const response = await fetch(url, {
            headers: this.headers()
        });
        if (!response.ok) throw new Error('Ошибка загрузки сообщений');
        return await response.json();
    },
    
    // Отправить сообщение
    async sendMessage(conversationId, content, type = 'text', metadata = null) {
        const response = await fetch(`${this.baseURL}/messages/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify({ content, type, metadata })
        });
        if (!response.ok) throw new Error('Ошибка отправки сообщения');
        return await response.json();
    },
    
    // Отметить диалог как прочитанный
    async markAsRead(conversationId) {
        const response = await fetch(`${this.baseURL}/messages/conversations/${conversationId}/read`, {
            method: 'POST',
            headers: this.headers()
        });
        if (!response.ok) throw new Error('Ошибка отметки прочитанным');
        return await response.json();
    },
    
    // Long polling для обновлений
    async getUpdates(lastId = 0) {
        const response = await fetch(`${this.baseURL}/messages/updates?last_id=${lastId}`, {
            headers: this.headers()
        });
        if (!response.ok) throw new Error('Ошибка получения обновлений');
        return await response.json();
    },
    
    // Создать диалог
    async createConversation(recipientId) {
        const response = await fetch(`${this.baseURL}/messages/conversations`, {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify({ recipient_id: recipientId })
        });
        if (!response.ok) throw new Error('Ошибка создания диалога');
        return await response.json();
    }
};

// ============================================
// КЛАСС МЕССЕНДЖЕРА
// ============================================

class Messenger {
    constructor() {
        this.conversations = [];
        this.currentConversationId = null;
        this.messages = [];
        this.lastMessageId = 0;
        this.pollingInterval = null;
        this.isLoading = false;
        
        // Определяем роль пользователя
        this.userRole = this.detectUserRole();
        console.log('🔵 Роль пользователя:', this.userRole);
        
        this.init();
    }
    
    detectUserRole() {
        // Проверяем по body классу
        if (document.body.classList.contains('medcenter-page')) {
            return 'medical_center';
        }
        // По умолчанию - донор
        return 'donor';
    }
    
    init() {
        console.log('🔵 Инициализация мессенджера...');
        
        // Элементы DOM
        this.conversationsList = document.getElementById('conversations-list');
        this.chatPanel = document.getElementById('chat-panel');
        this.chatEmpty = document.getElementById('chat-empty');
        this.chatHeader = document.getElementById('chat-header');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-message-btn');
        this.searchInput = document.getElementById('conversation-search');
        this.chatBackBtn = document.getElementById('chat-back-btn');
        
        // События
        this.attachEventListeners();
        
        // Загрузка данных
        this.loadConversations();
        
        // Запуск long polling
        this.startPolling();
        
        console.log('✅ Мессенджер инициализирован');
    }
    
    attachEventListeners() {
        // Отправка сообщения
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Enter для отправки, Shift+Enter для новой строки
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Автоматическое изменение высоты textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });
        
        // Поиск диалогов
        this.searchInput.addEventListener('input', (e) => {
            this.filterConversations(e.target.value);
        });
        
        // Кнопка "Назад" на мобильных
        if (this.chatBackBtn) {
            this.chatBackBtn.addEventListener('click', () => {
                this.closeChatMobile();
            });
        }
    }
    
    // Закрытие чата на мобильных (возврат к списку диалогов)
    closeChatMobile() {
        this.chatPanel.classList.remove('active');
        
        // Убираем класс chat-open с контейнера
        const container = document.querySelector('.messenger-container');
        if (container) {
            container.classList.remove('chat-open');
        }
        
        // Сбрасываем текущий диалог
        this.currentConversationId = null;
        
        // Убираем active со всех диалогов
        this.conversationsList.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
    }
    
    // ============================================
    // ЗАГРУЗКА ДИАЛОГОВ
    // ============================================
    
    async loadConversations() {
        try {
            const data = await MessengerAPI.getConversations();
            this.conversations = data.conversations || [];
            
            console.log(`📥 Загружено диалогов: ${this.conversations.length}`);
            
            // 🔧 FIX: Инициализируем lastMessageId из диалогов при первой загрузке
            if (this.lastMessageId === 0 && this.conversations.length > 0) {
                // Берём максимальный ID последнего сообщения из всех диалогов
                const maxId = this.conversations.reduce((max, conv) => {
                    const msgId = conv.last_message?.id || 0;
                    return Math.max(max, msgId);
                }, 0);
                
                if (maxId > 0) {
                    this.lastMessageId = maxId;
                    console.log(`🔧 lastMessageId инициализирован: ${this.lastMessageId}`);
                }
            }
            
            this.renderConversations();
            this.updateTotalUnreadCount();
        } catch (error) {
            console.error('Ошибка загрузки диалогов:', error);
            // Не показываем alert при polling-ошибках
            if (!this._isPollingUpdate) {
                this.showError('Не удалось загрузить диалоги');
            }
        }
    }
    
    renderConversations() {
        if (!this.conversationsList) return;
        
        if (this.conversations.length === 0) {
            this.conversationsList.innerHTML = `
                <div class="no-conversations">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                    </svg>
                    <p>Нет диалогов</p>
                </div>
            `;
            return;
        }
        
        this.conversationsList.innerHTML = this.conversations.map(conv => this.renderConversationItem(conv)).join('');
        
        // Добавляем обработчики клика
        this.conversationsList.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const convId = parseInt(item.dataset.conversationId);
                this.openConversation(convId);
            });
        });
    }
    
    renderConversationItem(conv) {
        const isActive = this.currentConversationId === conv.id;
        const unreadBadge = conv.unread_count > 0 ? 
            `<span class="conversation-badge">${conv.unread_count}</span>` : '';
        
        // 🔧 FIX: Безопасная обработка last_message
        const lastMessage = conv.last_message || {};
        const time = this.formatTime(lastMessage.time || lastMessage.created_at);
        const preview = lastMessage.preview || lastMessage.content || 'Нет сообщений';
        
        return `
            <div class="conversation-item ${isActive ? 'active' : ''}" data-conversation-id="${conv.id}">
                <div class="conversation-avatar">${conv.partner?.avatar || '?'}</div>
                <div class="conversation-info">
                    <div class="conversation-name">${this.escapeHtml(conv.partner?.name || 'Неизвестно')}</div>
                    <div class="conversation-preview">${this.escapeHtml(preview.substring(0, 50))}</div>
                </div>
                <div class="conversation-meta">
                    <div class="conversation-time">${time}</div>
                    ${unreadBadge}
                </div>
            </div>
        `;
    }
    
    filterConversations(query) {
        const items = this.conversationsList.querySelectorAll('.conversation-item');
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            const name = item.querySelector('.conversation-name').textContent.toLowerCase();
            const preview = item.querySelector('.conversation-preview').textContent.toLowerCase();
            
            if (name.includes(lowerQuery) || preview.includes(lowerQuery)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    // ============================================
    // ОТКРЫТИЕ ДИАЛОГА
    // ============================================
    
    async openConversation(conversationId) {
        console.log(`💬 Открытие диалога ${conversationId}`);
        
        this.currentConversationId = conversationId;
        this.messages = [];
        
        // Находим диалог
        const conversation = this.conversations.find(c => c.id === conversationId);
        if (!conversation) return;
        
        // Обновляем UI
        this.updateActiveConversation(conversationId);
        this.showChatPanel();
        this.updateChatHeader(conversation);
        
        // Загружаем сообщения
        await this.loadMessages(conversationId);
        
        // Отмечаем как прочитанное
        if (conversation.unread_count > 0) {
            this.markAsRead(conversationId);
        }
        
        // На мобильных показываем чат и добавляем класс для переключения вида
        if (window.innerWidth <= 768) {
            this.chatPanel.classList.add('active');
            
            // Добавляем класс chat-open на контейнер для CSS
            const container = document.querySelector('.messenger-container');
            if (container) {
                container.classList.add('chat-open');
            }
        }
    }
    
    updateActiveConversation(conversationId) {
        this.conversationsList.querySelectorAll('.conversation-item').forEach(item => {
            if (parseInt(item.dataset.conversationId) === conversationId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    showChatPanel() {
        this.chatEmpty.style.display = 'none';
        this.chatHeader.style.display = 'flex';
        this.chatMessages.style.display = 'block';
        this.chatInput.style.display = 'block';
    }
    
    updateChatHeader(conversation) {
        const avatar = document.getElementById('chat-avatar');
        const name = document.getElementById('chat-name');
        const status = document.getElementById('chat-status');
        
        if (avatar) avatar.textContent = conversation.partner.avatar;
        if (name) name.textContent = conversation.partner.name;
        if (status) status.textContent = 'онлайн'; // TODO: реальный статус
    }
    
    // ============================================
    // ЗАГРУЗКА СООБЩЕНИЙ
    // ============================================
    
    async loadMessages(conversationId) {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            
            const data = await MessengerAPI.getMessages(conversationId);
            this.messages = data.messages || [];
            
            console.log(`📥 Загружено сообщений: ${this.messages.length}`);
            
            // Обновляем lastMessageId для polling
            if (this.messages.length > 0) {
                this.lastMessageId = Math.max(...this.messages.map(m => m.id));
            }
            
            this.renderMessages();
            this.scrollToBottom();
        } catch (error) {
            console.error('Ошибка загрузки сообщений:', error);
            this.showError('Не удалось загрузить сообщения');
        } finally {
            this.isLoading = false;
        }
    }
    
    renderMessages() {
        if (!this.chatMessages) return;
        
        if (this.messages.length === 0) {
            this.chatMessages.innerHTML = `
                <div class="chat-empty" style="height: 100%;">
                    <p>Нет сообщений</p>
                    <p style="font-size: 14px; color: #999;">Напишите первое сообщение</p>
                </div>
            `;
            return;
        }
        
        // Группируем по датам
        const groupedMessages = this.groupMessagesByDate(this.messages);
        
        let html = '';
        for (const [date, messages] of Object.entries(groupedMessages)) {
            html += `<div class="chat-date-divider"><span>${date}</span></div>`;
            html += messages.map(msg => this.renderMessage(msg)).join('');
        }
        
        this.chatMessages.innerHTML = html;
    }
    
    groupMessagesByDate(messages) {
        const groups = {};
        
        messages.forEach(msg => {
            const date = new Date(msg.created_at);
            const dateKey = this.formatDate(date);
            
            if (!groups[dateKey]) {
                groups[dateKey] = [];
            }
            groups[dateKey].push(msg);
        });
        
        return groups;
    }
    
    renderMessage(msg) {
        // Приводим userRole к формату БД: 'medical_center' → 'medcenter'
        const normalizedUserRole = this.userRole === 'medical_center' ? 'medcenter' : this.userRole;
        const isOwn = msg.sender_type === normalizedUserRole;
        const isSystem = msg.sender_type === 'system';
        
        const messageClass = isSystem ? 'system' : (isOwn ? 'own' : 'other');
        
        if (msg.type === 'notification' || msg.type === 'invitation') {
            return this.renderNotificationMessage(msg);
        }
        
        if (msg.type === 'system') {
            return `
                <div class="message system">
                    <div class="message-bubble">
                        <div class="message-content">${this.formatMessageContent(msg.content)}</div>
                    </div>
                </div>
            `;
        }
        
        const time = new Date(msg.created_at).toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        const readStatus = isOwn ? this.getReadStatus(msg) : '';
        
        return `
            <div class="message ${messageClass}">
                <div class="message-bubble">
                    <div class="message-content">${this.formatMessageContent(msg.content)}</div>
                    <div class="message-time">
                        ${time}
                        ${readStatus}
                    </div>
                </div>
            </div>
        `;
    }
    
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
    
    getReadStatus(msg) {
        if (msg.is_read) {
            return `
                <span class="message-status">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9,11 12,14 22,4"/>
                        <polyline points="2,11 5,14 9,10"/>
                    </svg>
                </span>
            `;
        } else {
            return `
                <span class="message-status">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20,6 9,17 4,12"/>
                    </svg>
                </span>
            `;
        }
    }
    
    // ============================================
    // ОТПРАВКА СООБЩЕНИЯ
    // ============================================
    
    async sendMessage() {
        const content = this.messageInput.value.trim();
        
        if (!content || !this.currentConversationId) return;
        
        try {
            // Очищаем поле ввода
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
            
            // Отправляем на сервер
            const message = await MessengerAPI.sendMessage(this.currentConversationId, content);
            
            console.log('✅ Сообщение отправлено:', message);
            
            // Добавляем в список сообщений
            this.messages.push(message);
            this.lastMessageId = Math.max(this.lastMessageId, message.id);
            
            // Обновляем UI
            this.appendMessage(message);
            this.scrollToBottom();
            
            // Обновляем превью в списке диалогов
            this.updateConversationPreview(this.currentConversationId, content);
            
        } catch (error) {
            console.error('Ошибка отправки сообщения:', error);
            this.showError('Не удалось отправить сообщение');
        }
    }
    
    appendMessage(msg) {
        // Добавляем сообщение в конец
        const messageHtml = this.renderMessage(msg);
        this.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    }
    
    updateConversationPreview(conversationId, preview) {
        const now = new Date().toISOString();
        
        // Обновляем в массиве conversations
        const conv = this.conversations.find(c => c.id === conversationId);
        if (conv) {
            conv.last_message = conv.last_message || {};
            conv.last_message.preview = preview;
            conv.last_message.content = preview;
            conv.last_message.time = now;
        }
        
        // Обновляем в DOM
        const item = this.conversationsList.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (item) {
            const previewEl = item.querySelector('.conversation-preview');
            const timeEl = item.querySelector('.conversation-time');
            
            if (previewEl) previewEl.textContent = preview.substring(0, 50);
            if (timeEl) timeEl.textContent = 'только что';
            
            // 🔧 FIX: Перемещаем диалог наверх списка
            if (item.parentNode && item.parentNode.firstChild !== item) {
                item.parentNode.insertBefore(item, item.parentNode.firstChild);
            }
        }
    }
    
    // ============================================
    // LONG POLLING
    // ============================================
    
    startPolling() {
        console.log('🔄 Запуск long polling...');
        
        // 🔧 Polling для новых сообщений - каждые 3 сек
        this.pollingInterval = setInterval(() => {
            this.checkForUpdates();
        }, 3000);
        
        // 🔧 FIX: Отдельный таймер для обновления боковой панели - каждые 10 сек
        this.conversationsRefreshInterval = setInterval(() => {
            this._isPollingUpdate = true;
            this.loadConversations().finally(() => {
                this._isPollingUpdate = false;
            });
        }, 10000);
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        // 🔧 FIX: Очищаем также таймер обновления диалогов
        if (this.conversationsRefreshInterval) {
            clearInterval(this.conversationsRefreshInterval);
            this.conversationsRefreshInterval = null;
        }
    }
    
    async checkForUpdates() {
        try {
            const data = await MessengerAPI.getUpdates(this.lastMessageId);
            
            if (data.messages && data.messages.length > 0) {
                console.log(`🔔 Новых сообщений: ${data.messages.length}`);
                
                data.messages.forEach(msg => {
                    // Обновляем lastMessageId
                    this.lastMessageId = Math.max(this.lastMessageId, msg.id);
                    
                    // Если сообщение в текущем диалоге - добавляем в чат
                    if (msg.conversation_id === this.currentConversationId) {
                        // Проверяем, что сообщение ещё не добавлено
                        const exists = this.messages.some(m => m.id === msg.id);
                        if (!exists) {
                            this.messages.push(msg);
                            this.appendMessage(msg);
                            this.scrollToBottom();
                            
                            // Отмечаем как прочитанное
                            this.markAsRead(this.currentConversationId);
                        }
                    }
                    
                    // 🔧 FIX: Обновляем превью в боковой панели для диалога с новым сообщением
                    this.updateConversationInSidebar(msg.conversation_id, msg);
                });
            }
            
            // 🔧 FIX: Обновляем счётчики непрочитанных независимо от новых сообщений
            if (data.unread_counts) {
                this.updateUnreadCounts(data.unread_counts);
            }
            
        } catch (error) {
            // Не спамим ошибками в консоль при сетевых проблемах
            if (error.message !== 'Failed to fetch') {
                console.error('Ошибка polling:', error);
            }
        }
    }
    
    // 🔧 NEW: Обновление конкретного диалога в боковой панели
    updateConversationInSidebar(conversationId, newMessage) {
        const item = this.conversationsList.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (item) {
            const previewEl = item.querySelector('.conversation-preview');
            const timeEl = item.querySelector('.conversation-time');
            
            if (previewEl && newMessage.content) {
                previewEl.textContent = newMessage.content.substring(0, 50);
            }
            if (timeEl) {
                timeEl.textContent = this.formatTime(newMessage.created_at);
            }
            
            // Перемещаем диалог наверх списка
            if (item.parentNode.firstChild !== item) {
                item.parentNode.insertBefore(item, item.parentNode.firstChild);
            }
        }
        
        // Обновляем также в массиве conversations
        const conv = this.conversations.find(c => c.id === conversationId);
        if (conv) {
            conv.last_message = conv.last_message || {};
            conv.last_message.preview = newMessage.content;
            conv.last_message.time = newMessage.created_at;
            conv.last_message.id = newMessage.id;
        }
    }
    
    updateUnreadCounts(counts) {
        for (const [convId, count] of Object.entries(counts)) {
            const item = this.conversationsList.querySelector(`[data-conversation-id="${convId}"]`);
            if (item) {
                let badge = item.querySelector('.conversation-badge');
                
                if (count > 0) {
                    if (!badge) {
                        const meta = item.querySelector('.conversation-meta');
                        badge = document.createElement('span');
                        badge.className = 'conversation-badge';
                        meta.appendChild(badge);
                    }
                    badge.textContent = count;
                } else if (badge) {
                    badge.remove();
                }
            }
        }
        
        // Обновляем общий счётчик в меню
        this.updateTotalUnreadCount();
    }
    
    updateTotalUnreadCount() {
        const totalUnread = this.conversations.reduce((sum, conv) => sum + (conv.unread_count || 0), 0);
        const badge = document.getElementById('messages-badge');
        
        if (badge) {
            badge.textContent = totalUnread;
            badge.style.display = totalUnread > 0 ? 'inline-block' : 'none';
        }
        
        // Обновляем заголовок документа
        if (totalUnread > 0) {
            document.title = `(${totalUnread}) Твой Донор - Сообщения`;
        } else {
            document.title = 'Твой Донор - Личный кабинет';
        }
    }
    
    async markAsRead(conversationId) {
        try {
            await MessengerAPI.markAsRead(conversationId);
            
            // Обновляем счётчик в диалоге
            const conv = this.conversations.find(c => c.id === conversationId);
            if (conv) {
                conv.unread_count = 0;
            }
            
            // Убираем badge
            const item = this.conversationsList.querySelector(`[data-conversation-id="${conversationId}"]`);
            if (item) {
                const badge = item.querySelector('.conversation-badge');
                if (badge) badge.remove();
            }
        } catch (error) {
            console.error('Ошибка отметки прочитанным:', error);
        }
    }
    
    // ============================================
    // ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    // ============================================
    
    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
    
    formatTime(isoString) {
        if (!isoString) return '';
        
        try {
            const date = new Date(isoString);
            
            // 🔧 FIX: Проверка валидности даты
            if (isNaN(date.getTime())) {
                console.warn('Невалидная дата:', isoString);
                return '';
            }
            
            const now = new Date();
            const diff = now - date;
            
            // Защита от будущих дат
            if (diff < 0) return 'только что';
            
            // Меньше минуты
            if (diff < 60000) return 'только что';
            
            // Меньше часа
            if (diff < 3600000) {
                const minutes = Math.floor(diff / 60000);
                return `${minutes} мин назад`;
            }
            
            // Сегодня
            if (date.toDateString() === now.toDateString()) {
                return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            }
            
            // Вчера
            const yesterday = new Date(now);
            yesterday.setDate(yesterday.getDate() - 1);
            if (date.toDateString() === yesterday.toDateString()) {
                return 'вчера';
            }
            
            // Иначе дата
            return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
        } catch (e) {
            console.error('Ошибка форматирования даты:', e);
            return '';
        }
    }
    
    formatDate(date) {
        const now = new Date();
        
        if (date.toDateString() === now.toDateString()) {
            return 'Сегодня';
        }
        
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (date.toDateString() === yesterday.toDateString()) {
            return 'Вчера';
        }
        
        return date.toLocaleDateString('ru-RU', { 
            day: 'numeric', 
            month: 'long',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatMessageContent(content) {
        // Сначала экранируем HTML
        let formatted = this.escapeHtml(content);
        
        // Конвертируем markdown в HTML
        // **жирный текст**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Разделители ---
        formatted = formatted.replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 12px 0;">');
        
        // Списки • пункт
        formatted = formatted.replace(/^• (.+)$/gm, '<div style="margin-left: 16px; margin-bottom: 4px;">• $1</div>');
        
        // Переносы строк
        formatted = formatted.replace(/\n\n/g, '<br><br>');
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    showError(message) {
        // TODO: Показать уведомление об ошибке
        console.error(message);
        alert(message);
    }
    
    destroy() {
        this.stopPolling();
        console.log('❌ Мессенджер уничтожен');
    }
}

// ============================================
// ЭКСПОРТ
// ============================================

window.Messenger = Messenger;

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

function initMessengerUI() {
    console.log('🚀 Запуск initMessengerUI...');
    
    // Создаём глобальный экземпляр мессенджера
    if (!window.messenger) {
        window.messenger = new Messenger();
        console.log('✅ Экземпляр messenger создан');
        // 🔧 FIX: Убрана дублированная загрузка - она уже происходит в init()
    } else {
        console.log('ℹ️ Messenger уже инициализирован');
        // 🔧 FIX: При повторном вызове перезагружаем диалоги
        window.messenger.loadConversations();
    }
}

// Экспортируем функцию инициализации
window.initMessengerUI = initMessengerUI;
