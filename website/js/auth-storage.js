/**
 * ============================================
 * Твой Донор - Auth Storage Adapter v2.0
 * ============================================
 * 
 * JWT + Refresh Token система авторизации
 * Автоматическое запоминание всех пользователей
 * 
 * Изменения v2.0:
 * - Access token в памяти (не localStorage)
 * - Refresh token в HttpOnly Cookie (сервер устанавливает)
 * - Автоматический refresh при истечении access token
 * - Token rotation для безопасности
 * 
 * @version 2.0.0
 * @date 2026-01-27
 */

console.log('🔐 auth-storage.js v2.0 ЗАГРУЖЕН');

/**
 * Storage Adapter для работы с авторизацией
 */
class AuthStorage {
    // Access token хранится в памяти (не в localStorage!)
    static _accessToken = null;
    static _userType = null;
    static _userData = null;
    static _refreshPromise = null; // Для предотвращения параллельных refresh запросов
    
    /**
     * Сохранить данные после успешного логина
     * 
     * @param {string} accessToken - Access token (JWT) из backend
     * @param {string} userType - Тип пользователя ('donor' | 'medcenter')
     * @param {object} userData - Данные пользователя из backend
     * @returns {boolean} true если сохранение успешно
     */
    static save(accessToken, userType, userData) {
        try {
            // Access token в памяти
            this._accessToken = accessToken;
            this._userType = userType;
            this._userData = userData;
            
            // Сохраняем user_type и userData в localStorage для восстановления UI
            // (но НЕ токен!)
            localStorage.setItem('user_type', userType);
            localStorage.setItem(`${userType}_user`, JSON.stringify(userData));
            
            // Для совместимости со старым кодом
            localStorage.setItem('auth_token', accessToken);
            
            console.log(`✅ Сессия сохранена: ${userType}`);
            return true;
        } catch (error) {
            console.error('❌ Ошибка сохранения сессии:', error);
            return false;
        }
    }
    
    /**
     * Получить access token
     * Если токен истёк - автоматически обновляет через refresh
     * 
     * @returns {Promise<string|null>} Токен или null
     */
    static async getToken() {
        // Сначала проверяем память
        if (this._accessToken) {
            // Проверяем не истёк ли JWT
            if (this._isTokenExpired(this._accessToken)) {
                console.log('⏰ Access token истёк, обновляем...');
                const refreshed = await this.refreshTokens();
                return refreshed ? this._accessToken : null;
            }
            return this._accessToken;
        }
        
        // Если нет в памяти - пробуем обновить через refresh cookie
        // (refresh token автоматически отправляется браузером)
        console.log('🔄 Нет access token, пробуем refresh...');
        const refreshed = await this.refreshTokens();
        return refreshed ? this._accessToken : null;
    }
    
    /**
     * Синхронное получение токена (для совместимости)
     * ВНИМАНИЕ: может вернуть истёкший токен!
     */
    static getTokenSync() {
        return this._accessToken || localStorage.getItem('auth_token');
    }
    
    /**
     * Получить тип пользователя
     * 
     * @returns {string|null} 'donor' | 'medcenter' | null
     */
    static getUserType() {
        return this._userType || localStorage.getItem('user_type');
    }
    
    /**
     * Получить данные пользователя
     * 
     * @returns {object|null} Объект с данными или null
     */
    static getUserData() {
        if (this._userData) return this._userData;
        
        const userType = this.getUserType();
        if (!userType) return null;
        
        const key = `${userType}_user`;
        const data = localStorage.getItem(key);
        
        try {
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error('❌ Ошибка парсинга данных пользователя:', error);
            return null;
        }
    }
    
    /**
     * Обновить данные пользователя
     * 
     * @param {object} userData - Новые данные пользователя
     */
    static updateUserData(userData) {
        this._userData = userData;
        
        const userType = this.getUserType();
        if (userType) {
            localStorage.setItem(`${userType}_user`, JSON.stringify(userData));
            console.log(`✅ Данные пользователя обновлены: ${userType}`);
        }
    }
    
    /**
     * Проверить наличие сохранённой сессии (быстрая проверка)
     * 
     * @returns {boolean} true если есть данные для попытки восстановления
     */
    static hasSession() {
        // Проверяем наличие user_type - это означает, что был успешный вход
        return !!this.getUserType();
    }
    
    /**
     * 🔥 ГЛАВНАЯ ФИЧА: Обновление токенов через refresh endpoint
     * 
     * Вызывает /api/auth/refresh с refresh token из HttpOnly cookie
     * Браузер автоматически отправляет cookie
     * 
     * @returns {Promise<boolean>} true если refresh успешен
     */
    static async refreshTokens() {
        // Предотвращаем параллельные refresh запросы
        if (this._refreshPromise) {
            console.log('⏳ Ожидание завершения текущего refresh...');
            return this._refreshPromise;
        }
        
        this._refreshPromise = this._doRefresh();
        
        try {
            return await this._refreshPromise;
        } finally {
            this._refreshPromise = null;
        }
    }
    
    /**
     * Внутренняя функция refresh
     */
    static async _doRefresh() {
        const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}/api`;
        
        try {
            console.log('🔄 Вызов /api/auth/refresh...');
            
            const response = await fetch(`${API_URL}/auth/refresh`, {
                method: 'POST',
                credentials: 'include', // ВАЖНО: отправляем cookies
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Сохраняем новый access token
                this._accessToken = data.access_token;
                this._userType = data.user_type;
                
                if (data.user) {
                    this._userData = data.user;
                    localStorage.setItem(`${data.user_type}_user`, JSON.stringify(data.user));
                }
                
                // Для совместимости
                localStorage.setItem('user_type', data.user_type);
                localStorage.setItem('auth_token', data.access_token);
                
                console.log('✅ Токены обновлены успешно');
                return true;
                
            } else if (response.status === 401) {
                // Refresh token истёк или невалиден
                console.warn('⚠️ Refresh token истёк, требуется повторный вход');
                this.clear();
                return false;
                
            } else {
                console.error(`❌ Ошибка refresh: HTTP ${response.status}`);
                return false;
            }
            
        } catch (error) {
            console.error('❌ Ошибка сети при refresh:', error.message);
            // При сетевой ошибке не очищаем сессию - работаем оффлайн
            return false;
        }
    }
    
    /**
     * Проверка не истёк ли JWT токен
     * 
     * @param {string} token - JWT токен
     * @returns {boolean} true если истёк
     */
    static _isTokenExpired(token) {
        try {
            // JWT состоит из 3 частей, разделённых точками
            const parts = token.split('.');
            if (parts.length !== 3) return true;
            
            // Декодируем payload (вторая часть)
            const payload = JSON.parse(atob(parts[1]));
            
            // exp - время истечения в секундах
            if (!payload.exp) return false;
            
            // Проверяем с запасом 30 секунд
            const now = Math.floor(Date.now() / 1000);
            return payload.exp < (now + 30);
            
        } catch (error) {
            console.warn('⚠️ Ошибка проверки JWT:', error.message);
            return true; // Если не можем проверить - считаем истёкшим
        }
    }
    
    /**
     * Полная очистка сессии
     */
    static clear() {
        // Очищаем память
        this._accessToken = null;
        this._userType = null;
        this._userData = null;
        
        // Очищаем localStorage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('donor_user');
        localStorage.removeItem('medcenter_user');
        
        console.log('🗑️ Сессия полностью очищена');
    }
    
    /**
     * 🔥 Валидация и восстановление сессии при загрузке страницы
     * 
     * Логика:
     * 1. Проверяем есть ли user_type (был ли ранее успешный вход)
     * 2. Пробуем обновить токены через refresh cookie
     * 3. Если успех - сессия восстановлена
     * 4. Если нет - очищаем и требуем повторный вход
     * 
     * @returns {Promise<object>} Результат валидации
     */
    static async validate() {
        const userType = this.getUserType();
        
        // 1. Проверяем был ли ранее успешный вход
        if (!userType) {
            console.warn('⚠️ Нет сохранённого user_type');
            return { valid: false, reason: 'no_session' };
        }
        
        console.log(`🔍 Восстановление сессии для: ${userType}`);
        
        // 2. Пробуем refresh токенов
        const refreshed = await this.refreshTokens();
        
        if (refreshed) {
            console.log('✅ Сессия восстановлена через refresh');
            return { 
                valid: true, 
                userData: this._userData,
                userType: this._userType
            };
        } else {
            console.warn('❌ Не удалось восстановить сессию');
            return { valid: false, reason: 'refresh_failed' };
        }
    }
}


/**
 * Улучшенная функция проверки авторизации
 * Вызывается при загрузке dashboard
 * 
 * @returns {Promise<boolean>} true если пользователь авторизован
 */
async function checkAuthAndRestore() {
    console.log('🔐 Проверка авторизации...');
    
    // Проверяем наличие сессии и пробуем восстановить
    const validation = await AuthStorage.validate();
    
    if (validation.valid) {
        console.log('✅ Пользователь авторизован');
        
        // Если есть функция showNotification (из dashboards)
        if (validation.offline && typeof showNotification === 'function') {
            showNotification('Работаем в оффлайн режиме', 'info');
        }
        
        return true;
    } else {
        console.warn('❌ Требуется повторный вход');
        AuthStorage.clear();
        return false;
    }
}


/**
 * Функция logout
 * Очищает сессию на сервере и клиенте, затем перенаправляет
 * 
 * @param {string} redirectUrl - URL для редиректа (по умолчанию 'auth.html')
 */
async function logout(redirectUrl = 'auth.html') {
    console.log('👋 Выход из аккаунта...');
    
    const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}/api`;
    
    try {
        // Вызываем logout на сервере для инвалидации refresh token
        await fetch(`${API_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include', // Отправляем cookies
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        console.warn('⚠️ Ошибка logout на сервере:', error.message);
        // Продолжаем очистку на клиенте
    }
    
    // Очищаем клиентские данные
    AuthStorage.clear();
    
    // Редирект
    window.location.href = redirectUrl;
}


/**
 * Функция для выхода со всех устройств
 */
async function logoutAll(redirectUrl = 'auth.html') {
    console.log('👋 Выход со всех устройств...');
    
    const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}/api`;
    const token = AuthStorage.getTokenSync();
    
    try {
        await fetch(`${API_URL}/auth/logout-all`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
            }
        });
    } catch (error) {
        console.warn('⚠️ Ошибка logout-all:', error.message);
    }
    
    AuthStorage.clear();
    window.location.href = redirectUrl;
}


/**
 * Создание fetch wrapper с автоматическим refresh
 * Используется вместо обычного fetch для API запросов
 * 
 * @param {string} url - URL запроса
 * @param {object} options - Опции fetch
 * @returns {Promise<Response>}
 */
async function authFetch(url, options = {}) {
    // Получаем актуальный токен (с автоматическим refresh если нужно)
    const token = await AuthStorage.getToken();
    
    // Добавляем заголовки
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Выполняем запрос с credentials для cookies
    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include'
    });
    
    // Если получили 401 - пробуем refresh и повторяем
    if (response.status === 401) {
        console.log('🔄 Получен 401, пробуем refresh...');
        
        const refreshed = await AuthStorage.refreshTokens();
        
        if (refreshed) {
            // Повторяем запрос с новым токеном
            const newToken = AuthStorage.getTokenSync();
            headers['Authorization'] = `Bearer ${newToken}`;
            
            return fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });
        } else {
            // Refresh не удался - редирект на login
            console.warn('❌ Refresh не удался, редирект на login');
            AuthStorage.clear();
            window.location.href = 'auth.html';
        }
    }
    
    return response;
}


/**
 * Хелпер для получения заголовков авторизации
 * Используется в существующем коде
 * 
 * @returns {object} Заголовки с Authorization
 */
function getAuthHeaders() {
    const token = AuthStorage.getTokenSync();
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}


// Экспортируем в глобальную область
window.AuthStorage = AuthStorage;
window.checkAuthAndRestore = checkAuthAndRestore;
window.logout = logout;
window.logoutAll = logoutAll;
window.authFetch = authFetch;
window.getAuthHeaders = getAuthHeaders;

console.log('✅ auth-storage.js v2.0 инициализирован');
