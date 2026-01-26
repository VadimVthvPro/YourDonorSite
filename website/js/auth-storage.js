/**
 * ============================================
 * Твой Донор - Auth Storage Adapter
 * ============================================
 * 
 * Универсальный адаптер для управления сессией пользователя.
 * Обеспечивает:
 * - Сохранение и загрузку токенов
 * - Валидацию токена на backend
 * - Поддержку offline mode
 * - Единый API для всех компонентов
 * 
 * @version 1.0.0
 * @date 2026-01-26
 */

console.log('🔐 auth-storage.js ЗАГРУЖЕН');

/**
 * Storage Adapter для работы с авторизацией
 */
class AuthStorage {
    /**
     * Сохранить токен и данные пользователя после успешного логина
     * 
     * @param {string} token - Auth token из backend
     * @param {string} userType - Тип пользователя ('donor' | 'medcenter')
     * @param {object} userData - Данные пользователя из backend
     * @returns {boolean} true если сохранение успешно
     */
    static save(token, userType, userData) {
        try {
            localStorage.setItem('auth_token', token);
            localStorage.setItem('user_type', userType);
            localStorage.setItem(`${userType}_user`, JSON.stringify(userData));
            console.log(`✅ Сессия сохранена: ${userType}`);
            return true;
        } catch (error) {
            console.error('❌ Ошибка сохранения сессии:', error);
            return false;
        }
    }
    
    /**
     * Получить auth токен
     * 
     * @returns {string|null} Токен или null
     */
    static getToken() {
        return localStorage.getItem('auth_token');
    }
    
    /**
     * Получить тип пользователя
     * 
     * @returns {string|null} 'donor' | 'medcenter' | null
     */
    static getUserType() {
        return localStorage.getItem('user_type');
    }
    
    /**
     * Получить данные пользователя из localStorage
     * 
     * @returns {object|null} Объект с данными или null
     */
    static getUserData() {
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
     * Обновить данные пользователя в localStorage
     * Используется после получения свежих данных с backend
     * 
     * @param {object} userData - Новые данные пользователя
     */
    static updateUserData(userData) {
        const userType = this.getUserType();
        if (!userType) {
            console.warn('⚠️ Нельзя обновить данные: нет user_type');
            return;
        }
        
        const key = `${userType}_user`;
        localStorage.setItem(key, JSON.stringify(userData));
        console.log(`✅ Данные пользователя обновлены: ${userType}`);
    }
    
    /**
     * Проверить наличие сохранённой сессии
     * Проверяет только наличие, НЕ валидность
     * 
     * @returns {boolean} true если есть токен и user_type
     */
    static hasSession() {
        return !!(this.getToken() && this.getUserType());
    }
    
    /**
     * Полная очистка сессии
     * Удаляет все данные авторизации из localStorage
     */
    static clear() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('donor_user');
        localStorage.removeItem('medcenter_user');
        console.log('🗑️ Сессия полностью очищена');
    }
    
    /**
     * 🔥 ГЛАВНАЯ ФИЧА: Валидация токена на backend
     * 
     * Проверяет, что:
     * - Токен существует
     * - Токен действителен на backend
     * - Токен не истёк (expires_at)
     * - Сессия активна (is_active)
     * 
     * Если токен валиден → обновляет данные пользователя из backend
     * Если невалиден → возвращает { valid: false }
     * Если сервер недоступен → возвращает { valid: true, offline: true }
     * 
     * @returns {Promise<object>} Результат валидации
     *   - { valid: true, userData: {...} } — токен валиден
     *   - { valid: true, offline: true } — сервер недоступен, используем кэш
     *   - { valid: false, reason: 'no_token' | 'token_expired' } — токен невалиден
     */
    static async validate() {
        const token = this.getToken();
        const userType = this.getUserType();
        
        // 1. Проверяем наличие токена
        if (!token || !userType) {
            console.warn('⚠️ Нет сохранённого токена или user_type');
            return { valid: false, reason: 'no_token' };
        }
        
        console.log(`🔍 Валидация токена для: ${userType}`);
        
        try {
            // 2. Определяем endpoint для проверки
            const API_URL = window.API_URL || `${window.location.protocol}//${window.location.hostname}:5001/api`;
            const endpoint = userType === 'donor' 
                ? `${API_URL}/donor/profile`
                : `${API_URL}/medcenter/profile`;
            
            // 3. Запрашиваем профиль (это проверит токен через @require_auth)
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            // 4. Анализируем ответ
            if (response.ok) {
                // ✅ Токен валиден!
                const userData = await response.json();
                
                // Обновляем данные пользователя в localStorage
                this.updateUserData(userData);
                
                console.log('✅ Токен валиден, данные обновлены');
                return { valid: true, userData };
                
            } else if (response.status === 401 || response.status === 403) {
                // ❌ Токен истёк или невалиден
                console.warn(`⚠️ Токен невалиден (HTTP ${response.status})`);
                
                try {
                    const error = await response.json();
                    console.warn('Причина:', error.error || 'Неизвестно');
                } catch (e) {
                    // Игнорируем ошибки парсинга
                }
                
                return { valid: false, reason: 'token_expired' };
                
            } else {
                // ⚠️ Другая ошибка сервера (5xx, и т.д.)
                console.warn(`⚠️ Ошибка сервера (HTTP ${response.status}), работаем оффлайн`);
                
                // Оставляем пользователя залогиненным (offline mode)
                return { valid: true, offline: true };
            }
            
        } catch (error) {
            // 🌐 Сетевая ошибка (нет интернета, сервер недоступен)
            console.error('❌ Ошибка валидации токена:', error.message);
            
            // Оставляем пользователя залогиненным (offline mode)
            // Будет работать с кэшированными данными
            return { valid: true, offline: true };
        }
    }
}

/**
 * Улучшенная функция проверки авторизации
 * Вызывается при загрузке dashboard
 * 
 * Выполняет:
 * 1. Проверку наличия сохранённой сессии
 * 2. Валидацию токена на backend
 * 3. Очистку при невалидном токене
 * 4. Поддержку offline mode
 * 
 * @returns {Promise<boolean>} true если пользователь авторизован
 */
async function checkAuthAndRestore() {
    console.log('🔐 Проверка авторизации...');
    
    // 1. Быстрая проверка: есть ли вообще сохранённая сессия?
    if (!AuthStorage.hasSession()) {
        console.warn('⚠️ Нет сохранённой сессии в localStorage');
        return false;
    }
    
    console.log(`📦 Найдена сессия: ${AuthStorage.getUserType()}`);
    
    // 2. Валидируем токен на backend
    const validation = await AuthStorage.validate();
    
    if (validation.valid) {
        // ✅ Токен валиден
        console.log('✅ Токен валиден, сессия восстановлена');
        
        if (validation.offline) {
            // Показываем пользователю что работаем оффлайн
            console.warn('⚠️ Режим оффлайн: сервер недоступен, используем кэш');
            
            // Если есть функция showNotification (из dashboards)
            if (typeof showNotification === 'function') {
                showNotification('Работаем в оффлайн режиме', 'info');
            }
        }
        
        return true;
        
    } else {
        // ❌ Токен невалиден или истёк
        console.warn('❌ Токен невалиден, очищаем сессию');
        
        // Очищаем всё из localStorage
        AuthStorage.clear();
        
        return false;
    }
}

/**
 * Функция logout
 * Очищает сессию и перенаправляет на страницу авторизации
 * 
 * @param {string} redirectUrl - URL для редиректа (по умолчанию 'auth.html')
 */
function logout(redirectUrl = 'auth.html') {
    console.log('👋 Выход из аккаунта...');
    
    // Очищаем всё
    AuthStorage.clear();
    
    // Редирект
    window.location.href = redirectUrl;
}

// Экспортируем в глобальную область для использования в других скриптах
window.AuthStorage = AuthStorage;
window.checkAuthAndRestore = checkAuthAndRestore;
window.logout = logout;

console.log('✅ auth-storage.js инициализирован');
