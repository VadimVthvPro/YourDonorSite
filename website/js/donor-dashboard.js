/**
 * Твой Донор - Личный кабинет донора
 * Функционал управления профилем и откликов на запросы
 */

console.log('==== donor-dashboard.js ЗАГРУЖЕН ====');

// Используем API_URL из app.js или определяем свой
const DONOR_API_URL = window.API_URL || 'http://localhost:5001/api';

document.addEventListener('DOMContentLoaded', function() {
    // Проверка авторизации
    if (!checkAuth()) {
        window.location.href = 'auth.html';
        return;
    }
    
    // Синхронные функции инициализации
    initNavigation();
    initMobileSidebar();
    initForms();
    initModal();
    initLogout();
    initCertificateUpload();  // Инициализация drag-n-drop
    
    // Асинхронная загрузка данных (последовательно)
    (async () => {
        try {
            await loadUserDataFromAPI();
            console.log('✓ Данные донора загружены');
            
            // После загрузки профиля загружаем остальное
            await Promise.all([
                loadRequestsFromAPI(),
                loadMessagesFromAPI(),
                loadDonateCenters()
            ]);
            console.log('✓ Все данные загружены');
        } catch (e) {
            console.error('✗ Ошибка загрузки данных:', e);
        }
    })();
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
            console.log('Профиль донора загружен:', user);
            
            // Сохраняем в localStorage
            localStorage.setItem('donor_user', JSON.stringify(user));
            
            displayUserData(user);
            
            // Обновляем виджет обратного отсчёта
            updateMainCountdownWidget(user);
            
            // Проверяем статус Telegram
            await checkTelegramLinkStatus();
        } else if (response.status === 401 || response.status === 403) {
            // Только при ошибке авторизации
            console.error('Токен невалидный или истёк');
            localStorage.clear();
            window.location.href = '../pages/auth.html';
        } else {
            // Другие ошибки - пробуем загрузить из localStorage
            console.error('Ошибка загрузки профиля, статус:', response.status);
            const cachedUser = localStorage.getItem('donor_user');
            if (cachedUser) {
                displayUserData(JSON.parse(cachedUser));
                showNotification('Работаем в оффлайн режиме', 'info');
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
        // Пробуем загрузить из кеша
        const cachedUser = localStorage.getItem('donor_user');
        if (cachedUser) {
            try {
                displayUserData(JSON.parse(cachedUser));
                showNotification('Нет соединения. Показаны кешированные данные', 'info');
            } catch (e) {
                console.error('Ошибка загрузки кеша:', e);
            }
        }
    }
}

/**
 * Проверка статуса привязки Telegram
 */
async function checkTelegramLinkStatus() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/telegram/status`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const status = await response.json();
            
            if (status.linked && status.telegram_username) {
                // Telegram привязан
                updateTelegramStatus(true, status.telegram_username);
                
                // Скрываем кнопки привязки
                const step1 = document.getElementById('telegram-step-1');
                const step2 = document.getElementById('telegram-step-2');
                if (step1) step1.style.display = 'none';
                if (step2) step2.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Ошибка проверки статуса Telegram:', error);
    }
}

function displayUserData(user) {
    console.log('Отображение данных пользователя:', user);
    
    // Имя пользователя в шапке
    const userName = document.getElementById('user-name');
    if (userName) userName.textContent = user.full_name || 'Донор';
    
    // ИНИЦИАЛЫ в аватаре (ИСПРАВЛЕНИЕ)
    const userInitials = document.getElementById('user-initials');
    if (userInitials && user.full_name) {
        userInitials.textContent = getInitials(user.full_name);
    }
    
    // Группа крови в шапке
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
    
    // Информация в карточке "Моя информация"
    const infoBloodType = document.getElementById('info-blood-type');
    if (infoBloodType) infoBloodType.textContent = user.blood_type || '-';
    
    const infoMedcenter = document.getElementById('info-medcenter');
    if (infoMedcenter) infoMedcenter.textContent = user.medical_center_name || '-';
    
    const infoLastDonation = document.getElementById('info-last-donation');
    if (infoLastDonation) {
        infoLastDonation.textContent = user.last_donation_date 
            ? new Date(user.last_donation_date).toLocaleDateString('ru-RU')
            : 'Нет данных';
    }
    
    const infoTelegram = document.getElementById('info-telegram');
    if (infoTelegram) {
        if (user.telegram_id) {
            infoTelegram.textContent = `✅ ${user.telegram_username}`;
            infoTelegram.style.color = 'var(--color-success)';
        } else {
            infoTelegram.textContent = 'Не привязан';
            infoTelegram.style.color = 'var(--color-text-secondary)';
        }
    }
    
    // Информация о медцентре (если есть элементы)
    const mcName = document.getElementById('user-medcenter');
    if (mcName) mcName.textContent = user.medical_center_name || '-';
    
    const mcAddress = document.getElementById('medcenter-address');
    if (mcAddress) mcAddress.textContent = user.medical_center_address || '-';
    
    const mcPhone = document.getElementById('medcenter-phone');
    if (mcPhone) mcPhone.textContent = user.medical_center_phone || '-';
    
    // Заполняем форму профиля по ID
    const profileFio = document.getElementById('profile-fio');
    if (profileFio) profileFio.value = user.full_name || '';
    
    const profileBirth = document.getElementById('profile-birth');
    if (profileBirth) profileBirth.value = user.birth_year || '';
    
    const profilePhone = document.getElementById('profile-phone');
    if (profilePhone) profilePhone.value = user.phone || '';
    
    // Заполняем группу крови в форме (радиокнопки)
    const bloodTypeRadio = document.querySelector(`input[name="blood_type"][value="${user.blood_type}"]`);
    if (bloodTypeRadio) bloodTypeRadio.checked = true;
    
    // Заполняем дату последней донации
    const profileLastDonation = document.getElementById('profile-last-donation');
    if (profileLastDonation && user.last_donation_date) {
        profileLastDonation.value = user.last_donation_date.split('T')[0];
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
        const urgency = r.urgency || 'normal';
        
        const urgencyLabels = {
            'normal': 'Обычный',
            'needed': 'Нужна кровь',
            'urgent': 'Срочный',
            'critical': 'Критичный'
        };
        
        const timeAgo = formatTimeAgo(r.created_at);
        const expiresDate = r.expires_at ? formatDateShort(r.expires_at) : null;
        
        // Дополнительная информация
        const neededDonors = r.needed_donors;
        const currentDonors = r.current_donors || 0;
        
        return `
            <article class="blood-request-card blood-request-card--${urgency}" data-id="${r.id}" data-urgency="${urgency}" data-responded="${isResponded}">
                <!-- Шапка -->
                <header class="card-header">
                    <div class="urgency-badge urgency-badge--${urgency}">
                        <span class="urgency-dot"></span>
                        <span class="urgency-text">${urgencyLabels[urgency]}</span>
                        </div>
                    <time class="card-time">${timeAgo}</time>
                </header>
                
                <!-- Контент -->
                <div class="card-body">
                    <!-- Основная инфа: группа + центр -->
                    <div class="request-main">
                        <div class="blood-type-large">${r.blood_type}</div>
                        <div class="center-info">
                            <div class="center-name">${r.medical_center_name}</div>
                        ${r.medical_center_address ? `
                                <div class="center-address">
                                    <span class="icon">📍</span>
                                ${r.medical_center_address}
                            </div>
                        ` : ''}
                        ${r.medical_center_phone ? `
                                <div class="center-phone">
                                    <span class="icon">📞</span>
                                ${r.medical_center_phone}
                            </div>
                        ` : ''}
                        </div>
                    </div>
                    
                    <!-- Дополнительная инфа -->
                    <div class="request-meta-donor">
                        ${expiresDate ? `
                            <div class="meta-chip">
                                <span class="meta-chip-label">Действует до</span>
                                <span class="meta-chip-value">${expiresDate}</span>
                    </div>
                        ` : ''}
                        ${neededDonors && !isResponded ? `
                            <div class="meta-chip meta-chip--accent">
                                <span class="meta-chip-label">Нужно ещё</span>
                                <span class="meta-chip-value">${neededDonors - currentDonors} доноров</span>
                            </div>
                        ` : ''}
                </div>
                
                    ${r.description ? `<div class="request-description-donor">${r.description}</div>` : ''}
                </div>
                
                <!-- Футер -->
                <footer class="card-footer card-footer--donor">
                    ${isResponded ? `
                        <div class="request-response-status ${responseStatus}">
                            <svg viewBox="0 0 24 24" fill="currentColor" style="width: 20px; height: 20px;">
                                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                            ${getResponseStatusText(responseStatus)}
                        </div>
                        ${responseStatus === 'pending' ? `
                            <button class="btn btn-ghost btn-sm btn-cancel-response" data-id="${r.id}">
                                Отменить отклик
                            </button>
                        ` : ''}
                    ` : `
                        <button class="btn btn-ghost btn-sm" onclick="showRequestDetails(${r.id})">
                            Подробнее
                        </button>
                        <button class="btn btn-primary btn-sm btn-respond" data-id="${r.id}">
                            Откликнуться
                        </button>
                    `}
                </footer>
            </article>
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
    
    // Бейджи в фильтрах (с проверкой существования)
    const filterCountAll = document.getElementById('filter-count-all');
    if (filterCountAll) filterCountAll.textContent = totalCount;
    
    const filterCountCritical = document.getElementById('filter-count-critical');
    if (filterCountCritical) filterCountCritical.textContent = criticalCount;
    
    const filterCountUrgent = document.getElementById('filter-count-urgent');
    if (filterCountUrgent) filterCountUrgent.textContent = urgentCount;
    
    const filterCountResponded = document.getElementById('filter-count-responded');
    if (filterCountResponded) filterCountResponded.textContent = respondedCount;
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
    // Проверка: можно ли откликаться
    if (!checkCanRespond()) {
        return;
    }
    
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
        'needed': 'Нужно пополнить', 
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
    
    // Обработка anchor-ссылок типа <a href="#donate">
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const hash = link.getAttribute('href').slice(1);
            const targetSection = document.getElementById(hash);
            
            if (targetSection && targetSection.classList.contains('dashboard-section')) {
                e.preventDefault();
                
                // Обновляем навигацию
                navItems.forEach(nav => nav.classList.remove('active'));
                const navItem = document.querySelector(`.nav-item[data-section="${hash}"]`);
                if (navItem) navItem.classList.add('active');
                
                // Показываем секцию
                sections.forEach(section => section.classList.remove('active'));
                targetSection.classList.add('active');
                
                // Обновляем заголовок
                updatePageTitle(hash);
            }
        });
    });
    
    // Обработка хэша в URL
    if (window.location.hash) {
        const hash = window.location.hash.slice(1);
        const navItem = document.querySelector('.nav-item[data-section="' + hash + '"]');
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
        const bloodRadio = document.querySelector('input[name="blood_type"][value="' + bloodType + '"]');
        if (bloodRadio) bloodRadio.checked = true;
    }
}

/**
 * Получение инициалов
 */
function getInitials(fio) {
    if (!fio || typeof fio !== 'string') return '??';
    
    const parts = fio.trim().split(/\s+/).filter(p => p.length > 0);
    
    if (parts.length === 0) return '??';
    
    // Если 3 слова или больше (Фамилия Имя Отчество) — берём первые буквы всех
    if (parts.length >= 3) {
        return parts.slice(0, 3).map(p => p[0].toUpperCase()).join('');
    }
    
    // Если 2 слова (Фамилия Имя) — берём первые буквы обоих
    if (parts.length === 2) {
        return parts.map(p => p[0].toUpperCase()).join('');
    }
    
    // Если 1 слово — берём первые 2 буквы
    return fio.slice(0, 2).toUpperCase();
}

/**
 * Форматирование даты
 */
function formatDate(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        
        // Проверка валидности даты
        if (isNaN(date.getTime())) {
            console.warn('Невалидная дата:', dateString);
            return dateString; // Возвращаем исходную строку
        }
        
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
    } catch (error) {
        console.error('Ошибка форматирования даты:', error, dateString);
        return dateString;
    }
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

// Mock function removed
// loadRequestsFromAPI handles the data loading

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
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                phone: document.getElementById('profile-phone')?.value || ''
            };
            
            try {
                const response = await fetch(`${DONOR_API_URL}/donor/profile`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ Данные сохранены', 'success');
                    // Перезагружаем профиль
                    await loadUserDataFromAPI();
                } else {
                    showNotification('❌ ' + (result.error || 'Ошибка сохранения'), 'error');
                }
            } catch (error) {
                console.error('Ошибка сохранения профиля:', error);
                showNotification('❌ Ошибка соединения', 'error');
            }
        });
    }
    
    // Форма медицинской информации
    const medicalForm = document.getElementById('medical-form');
    if (medicalForm) {
        medicalForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const bloodType = document.querySelector('input[name="blood_type"]:checked');
            const lastDonation = document.getElementById('profile-last-donation')?.value;
            
            const formData = {};
            if (bloodType) formData.blood_type = bloodType.value;
            if (lastDonation) formData.last_donation_date = lastDonation;
            
            try {
                const response = await fetch(`${DONOR_API_URL}/donor/profile`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ Медицинская информация обновлена', 'success');
                    await loadUserDataFromAPI();
                    
                    // Обновляем виджет обратного отсчёта
                    const user = JSON.parse(localStorage.getItem('donor_user'));
                    if (user) {
                        updateMainCountdownWidget(user);
                    }
                } else {
                    showNotification('❌ ' + (result.error || 'Ошибка обновления'), 'error');
                }
            } catch (error) {
                console.error('Ошибка обновления:', error);
                showNotification('❌ Ошибка соединения', 'error');
            }
        });
    }
    
    // Привязка Telegram - Генерация кода
    const generateCodeBtn = document.getElementById('generate-code-btn');
    if (generateCodeBtn) {
        generateCodeBtn.addEventListener('click', async () => {
            try {
                const response = await fetch(`${DONOR_API_URL}/donor/telegram/link-code`, {
                    headers: getAuthHeaders()
                });
                
                const result = await response.json();
                
                if (response.ok && result.code) {
                    // Показываем шаг 2 с кодом
                    document.getElementById('telegram-step-1').style.display = 'none';
                    document.getElementById('telegram-step-2').style.display = 'block';
                    
                    // Отображаем код
                    document.getElementById('telegram-code').textContent = result.code;
                    document.getElementById('code-in-instructions').textContent = result.code;
                    
                    // Запускаем таймер обратного отсчёта
                    startCodeTimer(result.expires_in || 600);
                    
                    showNotification('✅ Код сгенерирован! Откройте Telegram бота.', 'success');
            } else {
                    showNotification('❌ ' + (result.error || 'Ошибка генерации кода'), 'error');
                }
            } catch (error) {
                console.error('Ошибка генерации кода:', error);
                showNotification('❌ Ошибка соединения', 'error');
            }
        });
    }
    
    // Копирование кода
    const copyCodeBtn = document.getElementById('copy-code-btn');
    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', () => {
            const code = document.getElementById('telegram-code').textContent;
            navigator.clipboard.writeText(code).then(() => {
                showNotification('✅ Код скопирован!', 'success');
            }).catch(() => {
                showNotification('❌ Не удалось скопировать', 'error');
            });
        });
    }
    
    // Отмена привязки
    const cancelLinkBtn = document.getElementById('cancel-link-btn');
    if (cancelLinkBtn) {
        cancelLinkBtn.addEventListener('click', () => {
            document.getElementById('telegram-step-1').style.display = 'block';
            document.getElementById('telegram-step-2').style.display = 'none';
            if (window.codeTimerInterval) {
                clearInterval(window.codeTimerInterval);
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
                showNotification('✅ Справка загружена!', 'success');
                updateCertificateStatus(true);
            }
        });
    }
    
    // ============================================
    // Форма привязки к медцентру
    // ============================================
    
    // Загружаем регионы при инициализации
    loadRegionsForMedcenterForm();
    
    const regionSelect = document.getElementById('profile-region');
    const districtSelect = document.getElementById('profile-district');
    const medcenterSelect = document.getElementById('profile-medcenter');
    const medcenterForm = document.getElementById('medcenter-form');
    
    if (regionSelect) {
        regionSelect.addEventListener('change', async () => {
            const regionId = regionSelect.value;
            
            // Сброс районов и медцентров
            districtSelect.innerHTML = '<option value="">Выберите район</option>';
            districtSelect.disabled = !regionId;
            medcenterSelect.innerHTML = '<option value="">Сначала выберите район</option>';
            medcenterSelect.disabled = true;
            
            if (regionId) {
                try {
                    const response = await fetch(`${DONOR_API_URL}/regions/${regionId}/districts`);
                    const districts = await response.json();
                    
                    districtSelect.innerHTML = '<option value="">Выберите район</option>' +
                        districts.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
                    districtSelect.disabled = false;
                } catch (error) {
                    console.error('Ошибка загрузки районов:', error);
                    showNotification('❌ Ошибка загрузки районов', 'error');
                }
            }
        });
    }
    
    if (districtSelect) {
        districtSelect.addEventListener('change', async () => {
            const districtId = districtSelect.value;
            
            // Сброс медцентров
            medcenterSelect.innerHTML = '<option value="">Выберите медцентр</option>';
            medcenterSelect.disabled = !districtId;
            
            if (districtId) {
                try {
                    const response = await fetch(`${DONOR_API_URL}/medcenters?district_id=${districtId}`);
                    const medcenters = await response.json();
                    
                    if (medcenters.length === 0) {
                        medcenterSelect.innerHTML = '<option value="">Нет медцентров в этом районе</option>';
                    } else {
                        medcenterSelect.innerHTML = '<option value="">Выберите медцентр</option>' +
                            medcenters.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
                        medcenterSelect.disabled = false;
                    }
                } catch (error) {
                    console.error('Ошибка загрузки медцентров:', error);
                    showNotification('❌ Ошибка загрузки медцентров', 'error');
                }
            }
        });
    }
    
    if (medcenterForm) {
        medcenterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const medcenterId = medcenterSelect?.value;
            const districtId = districtSelect?.value;
            
            if (!medcenterId || !districtId) {
                showNotification('❌ Выберите медцентр', 'error');
                return;
            }
            
            try {
                const response = await fetch(`${DONOR_API_URL}/donor/profile`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        medical_center_id: parseInt(medcenterId),
                        district_id: parseInt(districtId)
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ Медцентр успешно обновлён!', 'success');
                    await loadUserDataFromAPI();
                } else {
                    showNotification('❌ ' + (result.error || 'Ошибка обновления'), 'error');
                }
            } catch (error) {
                console.error('Ошибка обновления медцентра:', error);
                showNotification('❌ Ошибка соединения', 'error');
            }
        });
    }
}

/**
 * Загрузка списка регионов для формы привязки к медцентру
 */
async function loadRegionsForMedcenterForm() {
    const regionSelect = document.getElementById('profile-region');
    if (!regionSelect) return;
    
    try {
        const response = await fetch(`${DONOR_API_URL}/regions`);
        const regions = await response.json();
        
        regionSelect.innerHTML = '<option value="">Выберите область</option>' +
            regions.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки регионов:', error);
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
                <h4>✅ Telegram привязан</h4>
                <p>@${username}</p>
                <button type="button" class="btn btn-outline btn-sm" id="unlink-telegram-btn" style="margin-top: 8px;">Отвязать аккаунт</button>
            </div>
        `;
        
        // Добавляем обработчик отвязки
        const unlinkBtn = document.getElementById('unlink-telegram-btn');
        if (unlinkBtn) {
            unlinkBtn.addEventListener('click', async () => {
                if (!confirm('Вы уверены, что хотите отвязать Telegram? Вы перестанете получать уведомления.')) {
                    return;
                }
                
                try {
                    const response = await fetch(`${DONOR_API_URL}/donor/telegram/unlink`, {
                        method: 'POST',
                        headers: getAuthHeaders()
                    });
                    
                    if (response.ok) {
                        showNotification('✅ Telegram отвязан', 'success');
                        
                        // Возвращаем к шагу 1
                        statusEl.className = 'telegram-status not-linked';
                        statusEl.innerHTML = `
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2s-.18-.04-.26-.02c-.12.02-1.96 1.25-5.54 3.67-.52.36-1 .53-1.42.52-.47-.01-1.37-.26-2.03-.48-.82-.27-1.47-.42-1.42-.88.03-.24.37-.49 1.02-.75 3.98-1.73 6.64-2.87 7.97-3.43 3.8-1.57 4.59-1.85 5.10-1.86.11 0 .37.03.54.17.14.12.18.28.2.45-.01.06.01.24 0 .38z"/>
                            </svg>
                            <div class="telegram-info">
                                <h4>Telegram не привязан</h4>
                                <p>Привяжите аккаунт для получения уведомлений</p>
                            </div>
                        `;
                        
                        const step1 = document.getElementById('telegram-step-1');
                        if (step1) step1.style.display = 'block';
                        
                        await loadUserDataFromAPI();
                    } else {
                        const result = await response.json();
                        showNotification('❌ ' + (result.error || 'Ошибка отвязки'), 'error');
                    }
                } catch (error) {
                    console.error('Ошибка отвязки Telegram:', error);
                    showNotification('❌ Ошибка соединения', 'error');
                }
            });
        }
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
 * Загрузка центров для донации
 */
async function loadDonateCenters() {
    try {
        console.log('Загрузка центров донации...');
        
        // Получаем АКТУАЛЬНЫЕ данные донора из API, а не из localStorage
        const profileResponse = await fetch(`${DONOR_API_URL}/donor/profile`, {
            headers: getAuthHeaders()
        });
        
        if (!profileResponse.ok) {
            throw new Error(`Ошибка загрузки профиля: ${profileResponse.status}`);
        }
        
        const donor = await profileResponse.json();
        const bloodType = donor.blood_type;
        const districtId = donor.district_id;
        
        console.log('Данные донора:', { bloodType, districtId });
        
        if (!bloodType || !districtId) {
            console.warn('Нет информации о группе крови или районе донора');
            const container = document.getElementById('donate-centers');
            if (container) {
                container.innerHTML = '<p class="no-data">Заполните профиль для просмотра центров донации</p>';
            }
            return;
        }
        
        // Загружаем медцентры района с данными о потребности в крови
        const response = await fetch(`${DONOR_API_URL}/medical-centers?district_id=${districtId}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const centers = await response.json();
        console.log('Центры донации загружены:', centers.length, 'шт.');
        
        displayDonateCenters(centers, bloodType);
    } catch (error) {
        console.error('Ошибка загрузки центров донации:', error);
        const container = document.getElementById('donate-centers');
        if (container) {
            container.innerHTML = '<p class="no-data">Ошибка загрузки центров донации</p>';
        }
    }
}

/**
 * Отображение центров для донации
 */
function displayDonateCenters(centers, userBloodType) {
    const container = document.getElementById('donate-centers');
    
    if (!container) {
        console.warn('Контейнер donate-centers не найден');
        return;
    }
    
    if (!centers || centers.length === 0) {
        container.innerHTML = `
            <div class="request-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                <p>Центры донации не найдены в вашем районе</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = centers.map(center => {
        // Проверяем, нужна ли этому центру кровь донора
        const needsBlood = center.blood_needs && center.blood_needs.some(
            need => need.blood_type === userBloodType && need.status !== 'normal'
        );
        
        const urgentNeed = center.blood_needs && center.blood_needs.find(
            need => need.blood_type === userBloodType && need.status === 'critical'
        );
        
        return `
            <div class="center-card ${needsBlood ? 'needs-blood' : ''}" data-id="${center.id}">
                ${urgentNeed ? '<div class="urgent-indicator">🚨 Срочно нужна ваша группа крови!</div>' : ''}
                
                <div class="center-header">
                    <h3>${center.name}</h3>
                    ${needsBlood ? '<span class="needs-badge">Нужна ваша кровь</span>' : ''}
                </div>
                
                <div class="center-info">
                    ${center.address ? `
                        <div class="info-row">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                                <path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                            ${center.address}
                        </div>
                    ` : ''}
                    
                    ${center.phone ? `
                        <div class="info-row">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
                            </svg>
                            <a href="tel:${center.phone}">${center.phone}</a>
                        </div>
                    ` : ''}
                    
                    ${center.email ? `
                        <div class="info-row">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                            <a href="mailto:${center.email}">${center.email}</a>
                        </div>
                    ` : ''}
                </div>
                
                ${center.blood_needs && center.blood_needs.length > 0 ? `
                    <div class="blood-needs-indicator">
                        <h4>Потребность в крови:</h4>
                        <div class="blood-types-grid">
                            ${center.blood_needs.map(need => `
                                <div class="blood-type-status ${need.status}">
                                    <span class="blood-type">${need.blood_type}</span>
                                    <span class="status-dot"></span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div class="center-actions">
                    <button class="btn-schedule-donation" data-center-id="${center.id}" data-center-name="${center.name}">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                            <line x1="16" y1="2" x2="16" y2="6"/>
                            <line x1="8" y1="2" x2="8" y2="6"/>
                            <line x1="3" y1="10" x2="21" y2="10"/>
                        </svg>
                        Записаться на плановую донацию
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    // Добавляем обработчики для кнопок записи
    container.querySelectorAll('.btn-schedule-donation').forEach(btn => {
        btn.addEventListener('click', () => {
            const centerId = btn.dataset.centerId;
            const centerName = btn.dataset.centerName;
            openScheduleDonationModal(centerId, centerName);
        });
    });
}

/**
 * Открыть модальное окно для записи на донацию
 */
function openScheduleDonationModal(centerId, centerName) {
    // Создаём модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal-respond active';
    modal.innerHTML = `
        <div class="modal-respond-content">
            <div class="modal-respond-header">
                <h3>Записаться на донацию</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-respond-body">
                <p><strong>Медицинский центр:</strong> ${centerName}</p>
                <p style="margin-top: 12px; font-size: var(--text-sm); color: var(--color-gray-600);">
                    Медицинский центр получит информацию о вашей готовности сдать кровь и свяжется с вами для уточнения деталей.
                </p>
                
                <div style="margin-top: 16px;">
                    <label for="donation-date" style="display: block; margin-bottom: 8px; font-weight: 500;">
                        Предпочтительная дата (необязательно):
                    </label>
                    <input type="date" id="donation-date" 
                           style="width: 100%; padding: 12px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md);"
                           min="${new Date().toISOString().split('T')[0]}">
                </div>
                
                <div style="margin-top: 16px;">
                    <label for="donation-comment" style="display: block; margin-bottom: 8px; font-weight: 500;">
                        Комментарий (необязательно):
                    </label>
                    <textarea id="donation-comment" placeholder="Дополнительная информация или пожелания" 
                              style="width: 100%; padding: 12px; border: 1px solid var(--color-gray-300); border-radius: var(--radius-md); min-height: 80px; resize: vertical;"></textarea>
                </div>
            </div>
            <div class="modal-respond-footer">
                <button class="btn-cancel-response" onclick="this.closest('.modal-respond').remove()">
                    Отмена
                </button>
                <button class="btn-respond" id="confirm-schedule-btn">
                    Отправить заявку
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
    modal.querySelector('#confirm-schedule-btn').addEventListener('click', () => {
        const date = document.getElementById('donation-date').value;
        const comment = document.getElementById('donation-comment').value;
        scheduleDonation(centerId, centerName, date, comment);
        modal.remove();
    });
}

/**
 * Отправить заявку на плановую донацию
 */
async function scheduleDonation(centerId, centerName, plannedDate, comment) {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/schedule-donation`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                medical_center_id: parseInt(centerId),
                planned_date: plannedDate || null,
                comment: comment || null
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`✅ Заявка отправлена в "${centerName}". Медицинский центр свяжется с вами для уточнения деталей.`, 'success');
        } else {
            showNotification('❌ ' + (result.error || 'Ошибка отправки заявки'), 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки заявки:', error);
        showNotification('❌ Ошибка соединения', 'error');
    }
}

/**
 * Запуск таймера обратного отсчёта для кода
 */
function startCodeTimer(seconds) {
    const timerEl = document.getElementById('code-timer');
    if (!timerEl) return;
    
    let remaining = seconds;
    
    const updateTimer = () => {
        const minutes = Math.floor(remaining / 60);
        const secs = remaining % 60;
        timerEl.textContent = `Код действителен: ${minutes}:${secs.toString().padStart(2, '0')}`;
        
        if (remaining <= 0) {
            clearInterval(window.codeTimerInterval);
            timerEl.textContent = 'Код истёк. Сгенерируйте новый.';
            timerEl.style.color = 'var(--color-danger)';
        }
        
        remaining--;
    };
    
    updateTimer();
    window.codeTimerInterval = setInterval(updateTimer, 1000);
}

/**
 * Показать уведомление
 */
function showNotification(message, type = 'info') {
    // Удаляем существующие уведомления
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // SVG иконки в зависимости от типа
    let svgIcon = '';
    if (type === 'success') {
        svgIcon = '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/>';
    } else if (type === 'error') {
        svgIcon = '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>';
    } else {
        svgIcon = '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>';
    }
    
    notification.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${svgIcon}
        </svg>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Автоматическое скрытие через 4 секунды    
    setTimeout(() => {
        notification.remove();
    }, 4000);
}

/**
 * Инициализация загрузки мед.справки с drag-n-drop
 */
function initCertificateUpload() {
    const dropZone = document.getElementById('cert-drop-zone');
    const fileInput = document.getElementById('cert-file');
    
    if (!dropZone || !fileInput) return;
    
    // Обработчики drag-n-drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Визуальная индикация
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        });
    });
    
    // Обработка drop
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadCertificate(files[0]);
    });
    
    // Клик по зоне = выбор файла
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Выбор файла через input
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadCertificate(e.target.files[0]);
    });
}

async function uploadCertificate(file) {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
        return showNotification('Разрешены только JPG, PNG, PDF', 'error');
    }
    
    if (file.size > 5 * 1024 * 1024) {
        return showNotification('Максимальный размер: 5MB', 'error');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showNotification('Загрузка...', 'info');
        
        const response = await fetch(`${DONOR_API_URL}/donor/medical-certificate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        
        if (!response.ok) throw new Error('Ошибка загрузки');
        
        showNotification('✅ Справка загружена!', 'success');
        
        // Обновляем статус справки
        await displayCertificateStatus();
    } catch (error) {
        console.error('Ошибка загрузки справки:', error);
        showNotification('Ошибка загрузки справки', 'error');
    }
}

/**
 * Показать статус загруженной справки
 */
async function displayCertificateStatus() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/medical-certificate`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        const data = await response.json();
        
        const statusDiv = document.getElementById('certificate-status');
        if (!statusDiv) return;
        
        if (data.has_certificate) {
            const uploadDate = new Date(data.uploaded_at).toLocaleDateString('ru-RU');
            statusDiv.innerHTML = `
                <div class="certificate-uploaded">
                    <div class="certificate-icon uploaded">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                            <path d="M14 2v6h6M9 10h6M9 14h6M9 18h6"/>
                            <circle cx="12" cy="12" r="10" stroke="#28a745" fill="none"/>
                            <path d="M9 12l2 2 4-4" stroke="#28a745"/>
                        </svg>
                    </div>
                    <div class="certificate-info">
                        <p><strong>Справка загружена</strong></p>
                        <p class="text-muted">Дата: ${uploadDate}</p>
                    </div>
                    <button class="btn btn-sm btn-outline" onclick="viewCertificate()">
                        Просмотреть
                    </button>
                </div>
            `;
        } else {
            // Показываем зону загрузки
            statusDiv.innerHTML = `
                <div class="upload-area" id="cert-drop-zone">
                    <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                    </svg>
                    <p><strong>Перетащите файл сюда</strong></p>
                    <p class="text-muted">или нажмите для выбора</p>
                    <p class="text-small">PDF, JPG, PNG (макс. 5 МБ)</p>
                    <input type="file" id="cert-file" accept=".pdf,.jpg,.jpeg,.png" style="display: none;">
                </div>
            `;
            // Переинициализируем drag-n-drop после обновления HTML
            setTimeout(initCertificateUpload, 100);
        }
    } catch (error) {
        console.error('Ошибка загрузки статуса справки:', error);
    }
}

/**
 * Открыть справку для просмотра
 */
function viewCertificate() {
    const token = getToken();
    if (!token) return;
    
    // Открываем в новой вкладке
    const url = `${DONOR_API_URL}/donor/medical-certificate/view?token=${token}`;
    window.open(url, '_blank');
}

// ============================================
// СИСТЕМА ЧАТОВ
// ============================================

/**
 * Загрузить список чатов донора
 */
async function loadDonorChats() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/chats`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (!response.ok) throw new Error('Ошибка загрузки чатов');
        
        const chats = await response.json();
        renderDonorChats(chats);
    } catch (error) {
        console.error('Ошибка загрузки чатов:', error);
    }
}

/**
 * Рендер списка чатов
 */
function renderDonorChats(chats) {
    const container = document.getElementById('chats-list');
    if (!container) return;
    
    if (!chats || chats.length === 0) {
        container.innerHTML = '<p class="no-data">Нет переписок</p>';
        return;
    }
    
    container.innerHTML = chats.map(chat => {
        const lastMessageTime = chat.last_message_time ? 
            new Date(chat.last_message_time).toLocaleString('ru-RU', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            }) : '';
        
        return `
            <div class="chat-card ${chat.unread_count > 0 ? 'unread' : ''}" 
                 onclick="openChat(${chat.medcenter_id}, '${chat.medcenter_name}')">
                <div class="chat-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                        <polyline points="9 22 9 12 15 12 15 22"/>
                    </svg>
                </div>
                <div class="chat-info">
                    <div class="chat-header">
                        <span class="chat-name">${chat.medcenter_name}</span>
                        ${chat.unread_count > 0 ? `<span class="chat-badge">${chat.unread_count}</span>` : ''}
                    </div>
                    <div class="chat-last-message">${chat.last_message || 'Нет сообщений'}</div>
                    <div class="chat-time">${lastMessageTime}</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Открыть чат с медцентром
 */
async function openChat(medcenterId, medcenterName) {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/chats/${medcenterId}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        
        if (!response.ok) throw new Error('Ошибка загрузки истории');
        
        const data = await response.json();
        
        // Создаём модальное окно чата
        const modal = document.createElement('div');
        modal.id = 'chat-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content chat-modal">
                <div class="modal-header">
                    <h3>💬 ${medcenterName}</h3>
                    <button class="modal-close" onclick="closeChatModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="chat-messages" id="chat-messages"></div>
                    <div class="chat-input-container">
                        <textarea id="chat-input" placeholder="Введите сообщение..." rows="2"></textarea>
                        <button class="btn btn-primary" onclick="sendChatMessage(${medcenterId})">
                            Отправить
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Рендерим сообщения
        renderChatMessages(data.messages);
        
        // Автоматическая прокрутка вниз
    setTimeout(() => {
            const messagesDiv = document.getElementById('chat-messages');
            if (messagesDiv) messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }, 100);
        
        // Enter для отправки
        document.getElementById('chat-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage(medcenterId);
            }
        });
        
    } catch (error) {
        console.error('Ошибка открытия чата:', error);
        showNotification('Ошибка загрузки чата', 'error');
    }
}

/**
 * Рендер сообщений чата
 */
function renderChatMessages(messages) {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    
    if (!messages || messages.length === 0) {
        container.innerHTML = '<p class="no-messages">Нет сообщений</p>';
        return;
    }
    
    container.innerHTML = messages.map(msg => {
        const time = new Date(msg.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const isOwn = msg.sender_type === 'donor';
        
        return `
            <div class="chat-message ${isOwn ? 'own' : 'other'}">
                <div class="message-content">${msg.message}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
    }).join('');
}

/**
 * Отправить сообщение в чат
 */
async function sendChatMessage(medcenterId) {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/chats/${medcenterId}/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        if (!response.ok) throw new Error('Ошибка отправки');
        
        // Очищаем поле ввода
        input.value = '';
        
        // Перезагружаем чат
        closeChatModal();
        const medcenterName = document.querySelector('.chat-modal h3')?.textContent.replace('💬 ', '');
        setTimeout(() => openChat(medcenterId, medcenterName || 'Медцентр'), 300);
        
    } catch (error) {
        console.error('Ошибка отправки сообщения:', error);
        showNotification('Ошибка отправки сообщения', 'error');
    }
}

/**
 * Закрыть модал чата
 */
function closeChatModal() {
    const modal = document.getElementById('chat-modal');
    if (modal) modal.remove();
}

/**
 * Форматировать время "X назад"
 */
function formatTimeAgo(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Только что';
    if (diffMins < 60) return `${diffMins} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays === 1) return 'Вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;
    return formatDateShort(dateString);
}

/**
 * Форматировать дату компактно
 */
function formatDateShort(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    const months = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ];
    
    return `${date.getDate()} ${months[date.getMonth()]}`;
}

/**
 * Показать детали запроса
 */
function showRequestDetails(requestId) {
    // TODO: Открыть модальное окно с подробной информацией о запросе
    console.log('Показать детали запроса:', requestId);
    showNotification('Детали запроса (в разработке)', 'info');
}

// ============================================
// СТАТИСТИКА ДОНАЦИЙ
// ============================================

/**
 * Загрузить статистику донаций
 */
async function loadDonationStatistics() {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/statistics`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            console.error('Ошибка загрузки статистики:', response.status);
            return;
        }
        
        const stats = await response.json();
        console.log('Статистика загружена:', stats);
        
        renderDonationStatistics(stats);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

/**
 * Отобразить статистику донаций
 */
function renderDonationStatistics(stats) {
    // Анимация заполнения капельки
    animateBloodDrop(stats.total_donations);
    
    // Герой-блок
    document.getElementById('drop-donations').textContent = stats.total_donations || 0;
    document.getElementById('lives-saved-hero').textContent = stats.lives_saved_estimate || 0;
    document.getElementById('hero-donations').textContent = stats.total_donations || 0;
    
    const volumeLiters = ((stats.total_volume_ml || 0) / 1000).toFixed(1);
    document.getElementById('hero-volume').textContent = volumeLiters;
    
    // Обратный отсчёт
    renderCountdown(stats);
    
    // Карточки статистики
    document.getElementById('stat-total-donations').textContent = stats.total_donations || 0;
    document.getElementById('stat-total-volume').textContent = volumeLiters + ' л';
    
    if (stats.last_donation_date) {
        document.getElementById('stat-last-date').textContent = formatDateShort(stats.last_donation_date);
    }
    
    if (stats.days_until_next !== null) {
        const daysCard = document.getElementById('days-card');
        const daysValue = document.getElementById('stat-days-until');
        
        if (stats.can_donate) {
            daysValue.textContent = 'Можно сдать!';
            daysValue.style.color = '#059669';
            daysCard.classList.add('highlight');
        } else {
            daysValue.textContent = stats.days_until_next + ' дней';
        }
    }
    
    // Уровень
    renderLevel(stats.level);
    
    // Достижения
    renderAchievements(stats.achievements);
    
    // История
    renderDonationsHistory(stats.donations_history);
}

/**
 * Анимация заполнения капли крови
 */
function animateBloodDrop(donations) {
    const fillElement = document.getElementById('bloodFill');
    if (!fillElement) return;
    
    // Рассчитываем процент заполнения (20 донаций = 100%)
    const maxDonations = 20;
    const fillPercent = Math.min((donations / maxDonations) * 100, 100);
    
    // Высота капли примерно 190 пикселей
    const dropHeight = 190;
    const fillHeight = (fillPercent / 100) * dropHeight;
    
    // Анимация
    setTimeout(() => {
        fillElement.setAttribute('y', 210 - fillHeight);
        fillElement.setAttribute('height', fillHeight);
    }, 100);
}

/**
 * Отобразить обратный отсчёт
 */
function renderCountdown(stats) {
    const container = document.getElementById('countdown-container');
    const value = document.getElementById('countdown-value');
    const progressBar = document.getElementById('countdown-progress-bar');
    const ctaButton = document.getElementById('donate-cta');
    
    if (stats.days_until_next === null || stats.days_until_next === undefined) {
        value.textContent = 'Нет данных';
        progressBar.style.width = '0%';
        return;
    }
    
    if (stats.can_donate) {
        value.textContent = '✅ Вы можете сдать кровь!';
        value.classList.add('can-donate');
        progressBar.style.width = '100%';
        progressBar.classList.add('complete');
        ctaButton.classList.add('pulse');
    } else if (stats.days_until_next <= 5) {
        value.textContent = `Ещё немного! ${stats.days_until_next} дней`;
        value.classList.add('almost-ready');
        const progress = ((60 - stats.days_until_next) / 60) * 100;
        progressBar.style.width = progress + '%';
    } else {
        value.textContent = `${stats.days_until_next} дней`;
        const progress = ((60 - stats.days_until_next) / 60) * 100;
        progressBar.style.width = progress + '%';
    }
}

/**
 * Отобразить уровень донора
 */
function renderLevel(level) {
    if (!level) return;
    
    const iconMap = {
        'drop_small': '💧',
        'drop': '🩸',
        'drop_plus': '🩸➕',
        'drop_star': '🩸⭐',
        'drop_crown': '🩸👑',
        'drop_laurel': '🩸🏆',
        'drop_halo': '🩸✨'
    };
    
    document.getElementById('level-icon').textContent = iconMap[level.icon] || '🩸';
    document.getElementById('level-name').textContent = level.name;
    document.getElementById('level-number').textContent = level.current;
    
    const progress = level.donations_to_next > 0 
        ? (level.donations_in_level / (level.donations_in_level + level.donations_to_next)) * 100 
        : 100;
    
    document.getElementById('level-progress-fill').style.width = progress + '%';
    document.getElementById('level-progress-text').textContent = 
        `${level.donations_in_level} / ${level.donations_in_level + level.donations_to_next}`;
    
    if (level.next_level_name) {
        document.getElementById('level-next').textContent = `Следующий: ${level.next_level_name}`;
    } else {
        document.getElementById('level-next').textContent = 'Максимальный уровень достигнут! 🎉';
    }
}

/**
 * Отобразить достижения
 */
function renderAchievements(achievements) {
    const grid = document.getElementById('achievements-grid');
    if (!grid || !achievements) return;
    
    grid.innerHTML = achievements.map(ach => `
        <div class="achievement-card ${ach.unlocked ? 'unlocked' : 'locked'}" 
             title="${ach.name}${ach.date ? ' (получено ' + formatDateShort(ach.date) + ')' : ''}">
            <span class="achievement-icon">${ach.icon}</span>
            <div class="achievement-name">${ach.name}</div>
            <div class="achievement-progress">${ach.progress}</div>
            ${ach.unlocked ? '<div class="achievement-check">✓</div>' : ''}
        </div>
    `).join('');
}

/**
 * Отобразить историю донаций
 */
function renderDonationsHistory(history) {
    const container = document.getElementById('donations-history');
    if (!container) return;
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="empty-history">
                <div class="empty-history-icon">🩸</div>
                <h3>История донаций пуста</h3>
                <p>Ваша первая донация может спасти чью-то жизнь</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.map(donation => `
        <div class="donation-history-item">
            <div class="donation-date">
                <div class="donation-date-icon">📅</div>
                <div class="donation-date-text">${formatDateShort(donation.donation_date)}</div>
            </div>
            <div class="donation-info">
                <div class="donation-center">${donation.medical_center_name || 'Медицинский центр'}</div>
                <div class="donation-details">${donation.volume_ml} мл</div>
            </div>
            <div class="donation-blood-type">
                🩸 ${donation.blood_type}
            </div>
            <div class="donation-status completed">✅ Успешно</div>
        </div>
    `).join('');
}

// ============================================
// ОБРАТНЫЙ ОТСЧЁТ НА ГЛАВНОЙ СТРАНИЦЕ
// ============================================

/**
 * Глобальная переменная для хранения состояния донора
 */
let canDonateNow = true;

/**
 * Обновить виджет обратного отсчёта на главной странице
 */
function updateMainCountdownWidget(user) {
    const widget = document.getElementById('countdown-widget');
    const statNext = document.getElementById('stat-next');
    
    if (!widget || !user) return;
    
    // Рассчитываем данные обратного отсчёта
    const countdownData = calculateCountdown(user.last_donation_date);
    
    if (!countdownData) {
        // Нет даты последней донации
        widget.style.display = 'none';
        if (statNext) statNext.textContent = 'Нет данных';
        canDonateNow = true;
        return;
    }
    
    widget.style.display = 'block';
    
    // Обновляем глобальное состояние
    canDonateNow = countdownData.canDonate;
    
    // Обновляем виджет
    const titleEl = document.getElementById('countdown-title');
    const daysEl = document.getElementById('countdown-days');
    const hoursEl = document.getElementById('countdown-hours');
    const messageEl = document.getElementById('countdown-message');
    const progressBar = document.getElementById('countdown-progress-bar-main');
    
    // Обновляем карточку статистики
    if (statNext) {
        if (countdownData.canDonate) {
            statNext.textContent = '✅ Можно сдать';
            statNext.style.color = '#059669';
        } else {
            statNext.textContent = `${countdownData.daysLeft} дней`;
            statNext.style.color = '#dc2626';
        }
    }
    
    // Обновляем виджет
    if (countdownData.canDonate) {
        widget.classList.remove('blocked');
        widget.classList.add('can-donate');
        
        if (titleEl) titleEl.textContent = '✅ Вы можете сдать кровь!';
        if (daysEl) daysEl.textContent = '00';
        if (hoursEl) hoursEl.textContent = '00';
        if (messageEl) messageEl.textContent = 'Вы готовы стать героем снова';
        if (progressBar) progressBar.style.width = '100%';
    } else {
        widget.classList.remove('can-donate');
        widget.classList.add('blocked');
        
        if (titleEl) titleEl.textContent = 'До следующей донации';
        if (daysEl) daysEl.textContent = String(countdownData.daysLeft).padStart(2, '0');
        if (hoursEl) hoursEl.textContent = String(countdownData.hoursLeft).padStart(2, '0');
        if (messageEl) messageEl.textContent = 'Организму нужно восстановиться (60 дней между донациями)';
        if (progressBar) {
            const progress = ((60 - countdownData.daysLeft) / 60) * 100;
            progressBar.style.width = progress + '%';
        }
    }
}

/**
 * Рассчитать обратный отсчёт до следующей донации
 */
function calculateCountdown(lastDonationDate) {
    if (!lastDonationDate) return null;
    
    const last = new Date(lastDonationDate);
    const now = new Date();
    const nextAllowed = new Date(last);
    nextAllowed.setDate(nextAllowed.getDate() + 60); // 60 дней
    
    const diffMs = nextAllowed - now;
    
    if (diffMs <= 0) {
        return {
            canDonate: true,
            daysLeft: 0,
            hoursLeft: 0
        };
    }
    
    const daysLeft = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hoursLeft = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    return {
        canDonate: false,
        daysLeft,
        hoursLeft
    };
}

/**
 * Проверить, может ли донор откликнуться
 */
function checkCanRespond() {
    if (!canDonateNow) {
        showNotification('❌ Нельзя откликнуться! С последней донации должно пройти 60 дней.', 'error');
        return false;
    }
    return true;
}

/**
 * Обновить дату последней донации через API
 */
async function updateLastDonationDate(newDate) {
    try {
        const response = await fetch(`${DONOR_API_URL}/donor/profile`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                last_donation_date: newDate
            })
        });
        
        if (response.ok) {
            showNotification('✅ Дата последней донации обновлена', 'success');
            
            // Обновляем данные пользователя
            const user = JSON.parse(localStorage.getItem('user')) || {};
            user.last_donation_date = newDate;
            localStorage.setItem('user', JSON.stringify(user));
            
            // Обновляем виджет
            updateMainCountdownWidget(user);
            
            return true;
        } else {
            const error = await response.json();
            showNotification('❌ ' + (error.error || 'Ошибка обновления'), 'error');
            return false;
        }
    } catch (error) {
        console.error('Ошибка обновления даты:', error);
        showNotification('❌ Ошибка соединения', 'error');
        return false;
    }
}

// Инициализация статистики при загрузке секции
document.addEventListener('DOMContentLoaded', () => {
    // Загрузить статистику при открытии секции "Мои донации"
    const donationsNav = document.querySelector('[data-section="donations"]');
    if (donationsNav) {
        donationsNav.addEventListener('click', () => {
            loadDonationStatistics();
        });
    }
    
    // CTA кнопка
    const ctaButton = document.getElementById('donate-cta');
    if (ctaButton) {
        ctaButton.addEventListener('click', () => {
            // Переход к секции "Хочу сдать кровь"
            const donateSection = document.querySelector('[data-section="donate"]');
            if (donateSection) donateSection.click();
        });
    }
});

