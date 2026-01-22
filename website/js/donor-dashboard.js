/**
 * Твой Донор - Личный кабинет донора
 * Функционал управления профилем и откликов на запросы
 */

console.log('==== donor-dashboard.js ЗАГРУЖЕН ====');

// Используем DONOR_API_URL из app.js или определяем свой
const DONOR_DONOR_API_URL = window.DONOR_API_URL || 'http://localhost:5001/api';

document.addEventListener('DOMContentLoaded', function() {
    // Проверка авторизации
    if (!checkAuth()) {
        window.location.href = 'auth.html';
        return;
    }
    
    initNavigation();
    initMobileSidebar();
    loadUserDataFromAPI();
    loadRequestsFromAPI();
    loadMessagesFromAPI();
    initForms();
    initModal();
    initLogout();
});

/**
 * Проверка авторизации
 */
function checkAuth() {
    return localStorage.getItem('auth_token') !== null && localStorage.getItem('user_type') === 'donor';
}

function getAuthHeaders() {
    return {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Загрузка данных пользователя из API
 */
async function loadUserDataFromAPI() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/profile`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const user = await response.json();
            displayUserData(user);
        } else {
            // Токен невалидный
            localStorage.clear();
            window.location.href = 'auth.html';
        }
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
        loadUserData(); // fallback
    }
}

function displayUserData(user) {
    // Имя пользователя
    const userName = document.getElementById('user-name');
    if (userName) userName.textContent = user.full_name || 'Донор';
    
    // Группа крови
    const bloodType = document.getElementById('user-blood-type');
    if (bloodType) bloodType.textContent = user.blood_type || '-';
    
    // Статистика
    const donationsCount = document.getElementById('donations-count');
    if (donationsCount) donationsCount.textContent = user.total_donations || 0;
    
    const lastDonation = document.getElementById('last-donation');
    if (lastDonation) {
        lastDonation.textContent = user.last_donation_date 
            ? new Date(user.last_donation_date).toLocaleDateString('ru-RU')
            : 'Нет данных';
    }
    
    // Информация о медцентре
    const mcName = document.getElementById('user-medcenter');
    if (mcName) mcName.textContent = user.medical_center_name || '-';
    
    const mcAddress = document.getElementById('medcenter-address');
    if (mcAddress) mcAddress.textContent = user.medical_center_address || '-';
    
    const mcPhone = document.getElementById('medcenter-phone');
    if (mcPhone) mcPhone.textContent = user.medical_center_phone || '-';
    
    // Заполняем форму профиля
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        const phoneInput = profileForm.querySelector('[name="phone"]');
        const emailInput = profileForm.querySelector('[name="email"]');
        const telegramInput = profileForm.querySelector('[name="telegram_username"]');
        
        if (phoneInput) phoneInput.value = user.phone || '';
        if (emailInput) emailInput.value = user.email || '';
        if (telegramInput) telegramInput.value = user.telegram_username || '';
    }
}

/**
 * Загрузка активных запросов крови из API
 */
async function loadRequestsFromAPI() {
    try {
        console.log('Загрузка запросов крови...');
        
        const response = await fetch(`${DONOR_API_URL}/donor/blood-requests`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const requests = await response.json();
        console.log('Запросы крови загружены:', requests);
        
        displayBloodRequests(requests);
        updateRequestsBadges(requests);
    } catch (error) {
        console.error('Ошибка загрузки запросов крови:', error);
        const container = document.getElementById('blood-requests-list');
        if (container) {
            container.innerHTML = '<div class="request-empty"><p>Ошибка загрузки запросов</p></div>';
        }
    }
}

/**
 * Отображение запросов крови
 */
function displayBloodRequests(requests) {
    const container = document.getElementById('blood-requests-list');
    
    if (!container) {
        console.warn('Контейнер blood-requests-list не найден');
        return;
    }
    
    if (requests.length === 0) {
        container.innerHTML = `
            <div class="request-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 4C12 4 6 10 6 14a6 6 0 1012 0c0-4-6-10-6-10z"/>
                </svg>
                <p>Нет активных запросов крови</p>
                <p style="font-size: var(--text-sm); margin-top: 8px;">Мы уведомим вас, когда появится срочная необходимость в донации</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = requests.map(r => {
        const isResponded = r.response_id !== null;
        const responseStatus = r.response_status;
        
        return `
            <div class="request-card urgency-${r.urgency}" data-id="${r.id}" data-urgency="${r.urgency}" data-responded="${isResponded}">
                <div class="request-card-header">
                    <div class="request-blood-type">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 4C12 4 6 10 6 14a6 6 0 1012 0c0-4-6-10-6-10z"/>
                        </svg>
                        ${r.blood_type}
                    </div>
                    <div class="request-urgency ${r.urgency}">
                        ${getUrgencyText(r.urgency)}
                    </div>
                </div>
                
                <div class="request-card-body">
                    ${r.description ? `<div class="request-description">${r.description}</div>` : ''}
                    
                    <div class="request-medcenter-info">
                        <div class="info-row">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                            </svg>
                            <strong>${r.medical_center_name}</strong>
                        </div>
                        ${r.medical_center_address ? `
                            <div class="info-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                                    <path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                ${r.medical_center_address}
                            </div>
                        ` : ''}
                        ${r.medical_center_phone ? `
                            <div class="info-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
                                </svg>
                                ${r.medical_center_phone}
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="request-meta">
                        <span>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M12 6v6l4 2"/>
                            </svg>
                            ${formatDate(r.created_at)}
                        </span>
                        <span>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M12 8v4M12 16h.01"/>
                            </svg>
                            Действителен до ${formatDate(r.expires_at)}
                        </span>
                    </div>
                </div>
                
                <div class="request-card-footer">
                    ${isResponded ? `
                        <div class="request-response-status ${responseStatus}">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                            ${getResponseStatusText(responseStatus)}
                        </div>
                        ${responseStatus === 'pending' ? `
                            <button class="btn-cancel-response" data-id="${r.id}">
                                Отменить отклик
                            </button>
                        ` : ''}
                    ` : `
                        <button class="btn-respond" data-id="${r.id}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 4C12 4 6 10 6 14a6 6 0 1012 0c0-4-6-10-6-10z"/>
                            </svg>
                            Откликнуться
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join('');
    
    // Обработчики кнопок
    container.querySelectorAll('.btn-respond').forEach(btn => {
        btn.addEventListener('click', () => openRespondModal(btn.dataset.id));
    });
    
    container.querySelectorAll('.btn-cancel-response').forEach(btn => {
        btn.addEventListener('click', () => cancelResponse(btn.dataset.id));
    });
    
    // Фильтры
    initRequestFilters(requests);
}

/**
 * Обновление бейджей с количеством запросов
 */
function updateRequestsBadges(requests) {
    const totalCount = requests.length;
    const criticalCount = requests.filter(r => r.urgency === 'critical').length;
    const urgentCount = requests.filter(r => r.urgency === 'urgent').length;
    const respondedCount = requests.filter(r => r.response_id !== null).length;
    
    // Бейдж в навигации
    const navBadge = document.getElementById('requests-badge');
    if (navBadge) {
        navBadge.textContent = totalCount;
        navBadge.style.display = totalCount > 0 ? 'inline-flex' : 'none';
    }
    
    // Бейджи в фильтрах
    document.getElementById('filter-count-all').textContent = totalCount;
    document.getElementById('filter-count-critical').textContent = criticalCount;
    document.getElementById('filter-count-urgent').textContent = urgentCount;
    document.getElementById('filter-count-responded').textContent = respondedCount;
}

/**
 * Инициализация фильтров запросов
 */
function initRequestFilters(requests) {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const requestCards = document.querySelectorAll('.request-card');
    
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.dataset.filter;
            
            // Активная кнопка
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Фильтрация карточек
            requestCards.forEach(card => {
                const urgency = card.dataset.urgency;
                const responded = card.dataset.responded === 'true';
                
                let show = false;
                
                if (filter === 'all') {
                    show = true;
                } else if (filter === 'responded') {
                    show = responded;
                } else {
                    show = urgency === filter;
                }
                
                card.style.display = show ? 'block' : 'none';
            });
        });
    });
}

/**
 * Открыть модальное окно для отклика
 */
function openRespondModal(requestId) {
    const modal = document.createElement('div');
    modal.className = 'modal-respond active';
    modal.innerHTML = `
        <div class="modal-respond-content">
            <div class="modal-respond-header">
                <h3>Отклик на запрос</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-respond-body">
                <p>Вы уверены, что готовы прийти на донацию?</p>
                <p style="margin-top: 12px; font-size: var(--text-sm); color: var(--color-gray-600);">
                    Медицинский центр получит уведомление о вашем отклике.
                </p>
                <textarea id="response-message" placeholder="Дополнительная информация (необязательно)" 
                          style="width: 100%; margin-top: 16px; padding: 12px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md); min-height: 80px;"></textarea>
            </div>
            <div class="modal-respond-footer">
                <button class="btn-cancel-response" onclick="this.closest('.modal-respond').remove()">
                    Отмена
                </button>
                <button class="btn-respond" id="confirm-respond-btn">
                    Подтвердить отклик
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Закрытие по клику вне
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    // Закрытие по кнопке
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    
    // Подтверждение
    modal.querySelector('#confirm-respond-btn').addEventListener('click', () => {
        const message = document.getElementById('response-message').value;
        respondToBloodRequest(requestId, message);
        modal.remove();
    });
}

/**
 * Откликнуться на запрос крови
 */
async function respondToBloodRequest(requestId, message = '') {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/blood-requests/${requestId}/respond`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ message })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('✅ Ваш отклик отправлен! Медицинский центр свяжется с вами.', 'success');
            loadRequestsFromAPI();
        } else {
            showNotification('❌ ' + (result.error || 'Ошибка отклика'), 'error');
        }
    } catch (error) {
        console.error('Ошибка отклика:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Отменить отклик на запрос
 */
async function cancelResponse(requestId) {
    if (!confirm('Вы уверены, что хотите отменить свой отклик?')) {
        return;
    }
    
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/blood-requests/${requestId}/respond`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Отклик отменён', 'info');
            loadRequestsFromAPI();
        } else {
            showNotification('Ошибка: ' + (result.error || 'Не удалось отменить'), 'error');
        }
    } catch (error) {
        console.error('Ошибка отмены отклика:', error);
        showNotification('Ошибка соединения', 'error');
    }
}

function getUrgencyText(urgency) {
    const map = { 
        'normal': 'Обычный', 
        'urgent': 'Срочно', 
        'critical': 'Критично' 
    };
    return map[urgency] || urgency;
}

function getResponseStatusText(status) {
    const map = {
        'pending': 'Отклик отправлен',
        'approved': 'Одобрено',
        'rejected': 'Отклонено'
    };
    return map[status] || status;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = date - now;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 24 && hours >= 0) {
        return `Через ${hours} ч.`;
    }
    
    return date.toLocaleDateString('ru-RU', { 
        day: 'numeric', 
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Загрузка сообщений от медцентра
 */
/**
 * Загрузка сообщений от медцентра
 */
async function loadMessagesFromAPI() {
    try {
        console.log('Загрузка сообщений...');
        
        const response = await fetch(`${DONOR_API_URL}/donor/messages`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const messages = await response.json();
        console.log('Сообщения загружены:', messages);
        
        displayMessages(messages);
        updateMessagesBadge(messages);
    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
        const container = document.getElementById('messages-list');
        if (container) {
            container.innerHTML = '<p class="no-data">Ошибка загрузки сообщений</p>';
        }
    }
}

function displayMessages(messages) {
    const container = document.getElementById('messages-list');
    if (!container) return;
    
    if (!messages || messages.length === 0) {
        container.innerHTML = `
            <div class="request-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                </svg>
                <p>Нет сообщений</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = messages.map(m => `
        <div class="message-item ${m.is_read ? 'read' : 'unread'}" data-id="${m.id}">
            <div class="message-header">
                <div class="message-from">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                    </svg>
                    ${m.from_medcenter_name || 'Медицинский центр'}
                </div>
                <span class="message-date">${formatMessageDate(m.created_at)}</span>
            </div>
            ${m.subject ? `<div class="message-subject">${m.subject}</div>` : ''}
            <div class="message-text">${m.message}</div>
            ${!m.is_read ? '<div class="message-unread-indicator"></div>' : ''}
        </div>
    `).join('');
    
    // Пометить сообщения как прочитанные при клике
    container.querySelectorAll('.message-item.unread').forEach(item => {
        item.addEventListener('click', () => markMessageAsRead(item.dataset.id));
    });
}

function updateMessagesBadge(messages) {
    const unreadCount = messages.filter(m => !m.is_read).length;
    const badge = document.getElementById('messages-badge');
    
    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline-flex' : 'none';
    }
}

async function markMessageAsRead(messageId) {
    try {
        await fetch(`${DONOR_API_URL}/donor/messages/${messageId}/read`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        loadMessagesFromAPI(); // Перезагрузить сообщения
    } catch (error) {
        console.error('Ошибка отметки сообщения как прочитанного:', error);
    }
}

function formatMessageDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Сегодня, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
        return 'Вчера, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString('ru-RU', { 
            day: 'numeric', 
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}
    `).join('');
}

/**
 * Навигация по секциям
 */
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-section]');
    const sections = document.querySelectorAll('.dashboard-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            const sectionId = item.dataset.section;
            
            // Обновляем активную навигацию
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Показываем нужную секцию
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === sectionId) {
                    section.classList.add('active');
                }
            });
            
            // Обновляем заголовок
            updatePageTitle(sectionId);
            
            // Закрываем мобильное меню
            document.querySelector('.sidebar')?.classList.remove('active');
        });
    });
    
    // Обработка хэша в URL
    if (window.location.hash) {
        const hash = window.location.hash.slice(1);
        const navItem = document.querySelector(`.nav-item[data-section="${hash}"]`);
        if (navItem) {
            navItem.click();
        }
    }
}

/**
 * Обновление заголовка страницы
 */
function updatePageTitle(sectionId) {
    const titles = {
        'dashboard': 'Личный кабинет',
        'requests': 'Запросы крови',
        'donations': 'Мои донации',
        'donate': 'Хочу сдать кровь',
        'certificate': 'Медицинская справка',
        'profile': 'Мой профиль'
    };
    
    document.querySelector('.page-title').textContent = titles[sectionId] || 'Личный кабинет';
}

/**
 * Мобильное меню
 */
function initMobileSidebar() {
    const toggle = document.querySelector('.mobile-sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
        
        // Закрытие при клике вне меню
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }
}

/**
 * Загрузка данных пользователя
 */
function loadUserData() {
    const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
    
    // Имя пользователя
    const fio = userData.fio || 'Пользователь';
    document.getElementById('user-name').textContent = fio;
    document.getElementById('user-initials').textContent = getInitials(fio);
    
    // Статистика
    const donations = parseInt(localStorage.getItem('donor_donations') || '0');
    document.getElementById('stat-donations').textContent = donations;
    document.getElementById('total-volume').textContent = donations * 450;
    document.getElementById('lives-saved').textContent = donations * 3;
    
    // Информация о профиле
    const bloodType = userData.blood_type || '—';
    document.getElementById('info-blood-type').textContent = bloodType;
    
    // Медцентр
    const medcenterId = userData.medcenter;
    if (medcenterId) {
        const centerName = getMedcenterName(medcenterId);
        document.getElementById('info-medcenter').textContent = centerName;
    }
    
    // Последняя донация и статус
    const lastDonation = userData.last_donation;
    if (lastDonation) {
        const date = new Date(lastDonation);
        document.getElementById('info-last-donation').textContent = formatDate(date);
        
        // Расчёт дней до следующей донации
        const daysSince = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
        const daysUntilNext = 60 - daysSince;
        
        if (daysUntilNext > 0) {
            document.getElementById('stat-next').textContent = `${daysUntilNext} дн.`;
            document.getElementById('stat-status').textContent = 'Восст.';
        } else {
            document.getElementById('stat-next').textContent = 'Готов';
            document.getElementById('stat-status').textContent = 'Готов';
        }
    } else {
        document.getElementById('info-last-donation').textContent = 'Ещё не сдавали';
        document.getElementById('stat-next').textContent = 'Готов';
        document.getElementById('stat-status').textContent = 'Готов';
    }
    
    // Telegram
    if (userData.telegram) {
        document.getElementById('info-telegram').textContent = `@${userData.telegram}`;
        updateTelegramStatus(true, userData.telegram);
    }
    
    // Заполнение форм профиля
    document.getElementById('profile-fio').value = fio;
    document.getElementById('profile-birth').value = userData.birth_year || '';
    document.getElementById('profile-phone').value = userData.phone || '';
    document.getElementById('telegram-username').value = userData.telegram || '';
    
    if (userData.last_donation) {
        document.getElementById('profile-last-donation').value = userData.last_donation;
    }
    
    // Выбор группы крови
    if (bloodType !== '—') {
        const bloodRadio = document.querySelector(`input[name="blood_type"][value="${bloodType}"]`);
        if (bloodRadio) bloodRadio.checked = true;
    }
}

/**
 * Получение инициалов
 */
function getInitials(fio) {
    const parts = fio.trim().split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return fio.slice(0, 2).toUpperCase();
}

/**
 * Форматирование даты
 */
function formatDate(date) {
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

/**
 * Получение имени медцентра по ID
 */
function getMedcenterName(id) {
    // Поиск в данных медцентров
    const centers = {
        1: 'РНПЦ трансфузиологии',
        2: 'ГКБСМП',
        3: '6-я ГКБ',
        4: 'МОКБ',
        5: 'Борисовская ЦРБ',
        // ... остальные центры
    };
    return centers[id] || `Центр #${id}`;
}

/**
 * Загрузка запросов
 */
function loadRequests() {
    const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
    const bloodType = userData.blood_type;
    
    // Демо-данные запросов
    const requests = [
        {
            id: 1,
            center: 'РНПЦ трансфузиологии',
            address: 'ул. Долгиновский тракт, 160',
            bloodType: bloodType || 'A+',
            urgency: 'urgent',
            distance: '5.2 км',
            date: new Date()
        },
        {
            id: 2,
            center: '6-я ГКБ',
            address: 'ул. Уральская, 5',
            bloodType: bloodType || 'A+',
            urgency: 'need',
            distance: '8.1 км',
            date: new Date(Date.now() - 86400000)
        },
        {
            id: 3,
            center: 'ГКБСМП',
            address: 'ул. Кижеватова, 58',
            bloodType: bloodType || 'A+',
            urgency: 'urgent',
            distance: '12.3 км',
            date: new Date(Date.now() - 172800000)
        }
    ];
    
    // Обновление счётчика
    document.getElementById('requests-badge').textContent = requests.length;
    document.getElementById('stat-requests').textContent = requests.length;
    
    // Отображение последних запросов на главной
    const recentList = document.getElementById('recent-requests-list');
    if (recentList) {
        recentList.innerHTML = requests.slice(0, 3).map(req => `
            <div class="request-item" data-id="${req.id}">
                <div class="request-urgency ${req.urgency}"></div>
                <div class="request-info">
                    <div class="request-name">${req.center}</div>
                    <div class="request-location">${req.distance}</div>
                </div>
                <span class="request-blood">${req.bloodType}</span>
            </div>
        `).join('');
        
        // Обработчики кликов
        recentList.querySelectorAll('.request-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                openRequestModal(requests.find(r => r.id == id));
            });
        });
    }
    
    // Полный список запросов
    const requestsList = document.getElementById('requests-list');
    if (requestsList) {
        requestsList.innerHTML = requests.map(req => `
            <div class="request-card ${req.urgency}" data-id="${req.id}">
                <div class="request-card-icon">${req.bloodType}</div>
                <div class="request-card-content">
                    <h4 class="request-card-title">${req.center}</h4>
                    <p class="request-card-address">${req.address}</p>
                    <div class="request-card-meta">
                        <span>${req.distance}</span>
                        <span>${req.urgency === 'urgent' ? 'Срочно' : 'Нужно пополнить'}</span>
                    </div>
                </div>
                <div class="request-card-action">
                    <button class="btn btn-primary respond-btn" data-id="${req.id}">Откликнуться</button>
                </div>
            </div>
        `).join('');
        
        // Обработчики кнопок
        requestsList.querySelectorAll('.respond-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                openRequestModal(requests.find(r => r.id == id));
            });
        });
    }
    
    // Центры для донации
    loadDonateCenters(requests);
}

/**
 * Загрузка центров для донации
 */
function loadDonateCenters(requests) {
    const container = document.getElementById('donate-centers');
    if (!container) return;
    
    if (requests.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <h3>Нет активных запросов</h3>
                <p>Сейчас нет центров, которым нужна ваша группа крови</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <p class="donate-intro">Найдено ${requests.length} центров, которым нужна ваша группа крови:</p>
        <div class="donate-list">
            ${requests.map(req => `
                <div class="donate-card ${req.urgency}">
                    <div class="donate-card-header">
                        <span class="urgency-badge ${req.urgency}">
                            ${req.urgency === 'urgent' ? 'Срочно' : 'Нужно'}
                        </span>
                        <span class="blood-badge">${req.bloodType}</span>
                    </div>
                    <h4>${req.center}</h4>
                    <p class="address">${req.address}</p>
                    <p class="distance">${req.distance} от вас</p>
                    <button class="btn btn-primary btn-full respond-btn" data-id="${req.id}">
                        Записаться на донацию
                    </button>
                </div>
            `).join('')}
        </div>
    `;
    
    // Стили для карточек
    const style = document.createElement('style');
    style.textContent = `
        .donate-intro {
            color: var(--color-gray-600);
            margin-bottom: var(--spacing-lg);
        }
        .donate-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: var(--spacing-lg);
        }
        .donate-card {
            background: var(--color-white);
            border-radius: var(--radius-xl);
            padding: var(--spacing-lg);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--color-gray-100);
        }
        .donate-card.urgent {
            border-left: 4px solid var(--color-danger);
        }
        .donate-card.need {
            border-left: 4px solid var(--color-warning);
        }
        .donate-card-header {
            display: flex;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-md);
        }
        .urgency-badge {
            padding: 0.25rem 0.75rem;
            font-size: var(--text-xs);
            font-weight: 700;
            border-radius: var(--radius-full);
        }
        .urgency-badge.urgent {
            background: var(--color-danger-light);
            color: var(--color-danger);
        }
        .urgency-badge.need {
            background: var(--color-warning-light);
            color: var(--color-warning);
        }
        .blood-badge {
            padding: 0.25rem 0.75rem;
            font-size: var(--text-xs);
            font-weight: 700;
            background: var(--color-primary-lighter);
            color: var(--color-primary);
            border-radius: var(--radius-full);
        }
        .donate-card h4 {
            font-size: var(--text-base);
            font-weight: 700;
            color: var(--color-gray-900);
            margin-bottom: var(--spacing-xs);
        }
        .donate-card .address {
            font-size: var(--text-sm);
            color: var(--color-gray-500);
            margin-bottom: var(--spacing-xs);
        }
        .donate-card .distance {
            font-size: var(--text-sm);
            color: var(--color-gray-400);
            margin-bottom: var(--spacing-md);
        }
    `;
    document.head.appendChild(style);
    
    // Обработчики
    container.querySelectorAll('.respond-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            showNotification('Ваша заявка отправлена! Ожидайте подтверждения.', 'success');
        });
    });
}

/**
 * Модальное окно
 */
function initModal() {
    const modal = document.getElementById('response-modal');
    if (!modal) return;
    
    const closeBtn = modal.querySelector('.modal-close');
    const cancelBtn = modal.querySelector('[data-action="cancel"]');
    const confirmBtn = modal.querySelector('[data-action="confirm"]');
    
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    confirmBtn.addEventListener('click', () => {
        // Отправка отклика
        showNotification('Ваш отклик отправлен! Медцентр свяжется с вами.', 'success');
        closeModal();
    });
    
    // Закрытие при клике на фон
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Закрытие по Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
}

function openRequestModal(request) {
    const modal = document.getElementById('response-modal');
    const details = document.getElementById('modal-request-details');
    
    details.innerHTML = `
        <div class="modal-request-info">
            <div class="info-row">
                <span class="label">Медцентр:</span>
                <span class="value">${request.center}</span>
            </div>
            <div class="info-row">
                <span class="label">Адрес:</span>
                <span class="value">${request.address}</span>
            </div>
            <div class="info-row">
                <span class="label">Группа крови:</span>
                <span class="value blood">${request.bloodType}</span>
            </div>
            <div class="info-row">
                <span class="label">Срочность:</span>
                <span class="value ${request.urgency}">${request.urgency === 'urgent' ? 'Срочно' : 'Нужно пополнить'}</span>
            </div>
            <div class="info-row">
                <span class="label">Расстояние:</span>
                <span class="value">${request.distance}</span>
            </div>
        </div>
        <p class="modal-note">После подтверждения отклика вам придёт уведомление в Telegram с подробной информацией.</p>
    `;
    
    // Добавляем стили
    const style = document.createElement('style');
    style.textContent = `
        .modal-request-info {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
        }
        .modal-request-info .info-row {
            display: flex;
            justify-content: space-between;
            padding-bottom: var(--spacing-md);
            border-bottom: 1px solid var(--color-gray-100);
        }
        .modal-request-info .label {
            color: var(--color-gray-500);
        }
        .modal-request-info .value {
            font-weight: 600;
            color: var(--color-gray-900);
        }
        .modal-request-info .value.blood {
            padding: 0.25rem 0.75rem;
            background: var(--color-primary-lighter);
            color: var(--color-primary);
            border-radius: var(--radius-full);
        }
        .modal-request-info .value.urgent {
            color: var(--color-danger);
        }
        .modal-request-info .value.need {
            color: var(--color-warning);
        }
        .modal-note {
            margin-top: var(--spacing-lg);
            padding: var(--spacing-md);
            background: var(--color-accent-light);
            border-radius: var(--radius-lg);
            font-size: var(--text-sm);
            color: var(--color-accent);
        }
    `;
    document.head.appendChild(style);
    
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('response-modal');
    modal.classList.remove('active');
}

/**
 * Инициализация форм
 */
function initForms() {
    // Форма профиля
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
            userData.phone = document.getElementById('profile-phone').value;
            localStorage.setItem('donor_user', JSON.stringify(userData));
            showNotification('Данные сохранены', 'success');
        });
    }
    
    // Форма медицинской информации
    const medicalForm = document.getElementById('medical-form');
    if (medicalForm) {
        medicalForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
            const bloodType = document.querySelector('input[name="blood_type"]:checked');
            if (bloodType) {
                userData.blood_type = bloodType.value;
            }
            userData.last_donation = document.getElementById('profile-last-donation').value;
            localStorage.setItem('donor_user', JSON.stringify(userData));
            showNotification('Медицинская информация обновлена', 'success');
            loadUserData();
        });
    }
    
    // Привязка Telegram
    const linkTelegramBtn = document.getElementById('link-telegram');
    if (linkTelegramBtn) {
        linkTelegramBtn.addEventListener('click', () => {
            const username = document.getElementById('telegram-username').value.trim();
            if (username) {
                const userData = JSON.parse(localStorage.getItem('donor_user') || '{}');
                userData.telegram = username;
                localStorage.setItem('donor_user', JSON.stringify(userData));
                updateTelegramStatus(true, username);
                showNotification('Telegram привязан! Ожидайте подтверждения от бота.', 'success');
            } else {
                showNotification('Введите username', 'error');
            }
        });
    }
    
    // Загрузка справки
    const certFile = document.getElementById('cert-file');
    if (certFile) {
        certFile.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // В реальном приложении здесь будет загрузка на сервер
                showNotification('Справка загружена!', 'success');
                updateCertificateStatus(true);
            }
        });
    }
}

/**
 * Обновление статуса Telegram
 */
function updateTelegramStatus(linked, username) {
    const statusEl = document.getElementById('telegram-status');
    if (!statusEl) return;
    
    if (linked) {
        statusEl.className = 'telegram-status linked';
        statusEl.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2s-.18-.04-.26-.02c-.12.02-1.96 1.25-5.54 3.67-.52.36-1 .53-1.42.52-.47-.01-1.37-.26-2.03-.48-.82-.27-1.47-.42-1.42-.88.03-.24.37-.49 1.02-.75 3.98-1.73 6.64-2.87 7.97-3.43 3.8-1.57 4.59-1.85 5.1-1.86.11 0 .37.03.54.17.14.12.18.28.2.45-.01.06.01.24 0 .38z"/>
            </svg>
            <div class="telegram-info">
                <h4>Telegram привязан</h4>
                <p>@${username}</p>
            </div>
        `;
    }
}

/**
 * Обновление статуса справки
 */
function updateCertificateStatus(uploaded) {
    const statusEl = document.getElementById('certificate-status');
    if (!statusEl || !uploaded) return;
    
    statusEl.innerHTML = `
        <div class="certificate-icon uploaded">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                <path d="M22 4L12 14.01l-3-3"/>
            </svg>
        </div>
        <div class="certificate-info">
            <h3>Справка загружена</h3>
            <p>Действительна до ${formatDate(new Date(Date.now() + 180 * 24 * 60 * 60 * 1000))}</p>
        </div>
    `;
}

/**
 * Выход из системы
 */
function initLogout() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            try {
                await fetch(`${DONOR_API_URL}/logout`, {
                    method: 'POST',
                    headers: getAuthHeaders()
                });
            } catch (error) {
                console.log('Logout error:', error);
            }
            
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_type');
            localStorage.removeItem('donor_user');
            window.location.href = 'auth.html';
        });
    }
}

/**
 * Показать уведомление
 */
function showNotification(message, type = 'info') {
    // Удаляем существующие уведомления
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' 
                ? '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/>' 
                : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'}
        </svg>
        <span>${message}</span>
    `;
    
    // Стили для уведомления
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 100px;
            right: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 24px;
            background: var(--color-white);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-xl);
            z-index: 1001;
            animation: slideIn 0.3s ease;
        }
        .notification.success {
            border-left: 4px solid var(--color-success);
        }
        .notification.success svg {
            color: var(--color-success);
        }
        .notification.error {
            border-left: 4px solid var(--color-danger);
        }
        .notification.error svg {
            color: var(--color-danger);
        }
        .notification svg {
            width: 20px;
            height: 20px;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(notification);
    
    // Автоматическое скрытие
    setTimeout(() => {
        notification.remove();
    }, 4000);
}
