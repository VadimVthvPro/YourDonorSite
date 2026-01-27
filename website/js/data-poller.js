/**
 * 🔄 АВТООБНОВЛЕНИЕ ДАННЫХ (POLLING)
 * Безопасное обновление данных без перезагрузки страницы
 */

class DataPoller {
    constructor() {
        this.intervals = {};
        this.isUserActive = true;
        this.lastUpdateTime = {};
        this.pausedUntil = null;
        
        // Отслеживаем активность пользователя
        this.initActivityTracking();
    }
    
    /**
     * Отслеживание активности пользователя
     */
    initActivityTracking() {
        // Пауза при фокусе на input/textarea
        document.addEventListener('focusin', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                console.log('⏸️ Polling приостановлен (пользователь печатает)');
                this.pauseAll(30000); // Пауза на 30 секунд
            }
        });
        
        // Возобновляем при потере фокуса
        document.addEventListener('focusout', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                console.log('▶️ Polling возобновлён');
                this.pausedUntil = null;
            }
        });
        
        // Останавливаем polling когда вкладка неактивна
        document.addEventListener('visibilitychange', () => {
            this.isUserActive = !document.hidden;
            console.log(document.hidden ? '👁️ Вкладка скрыта, polling замедлен' : '👁️ Вкладка активна');
        });
    }
    
    /**
     * Приостановить все polling на N миллисекунд
     */
    pauseAll(ms) {
        this.pausedUntil = Date.now() + ms;
    }
    
    /**
     * Проверка: можно ли обновлять?
     */
    canPoll() {
        if (this.pausedUntil && Date.now() < this.pausedUntil) {
            return false;
        }
        return true;
    }
    
    /**
     * Запустить периодическое обновление
     * @param {string} name - Уникальное имя polling
     * @param {function} callback - Функция обновления
     * @param {number} intervalMs - Интервал в миллисекундах
     * @param {boolean} runImmediately - Запустить сразу или ждать первого интервала
     */
    start(name, callback, intervalMs, runImmediately = false) {
        // Останавливаем если уже запущен
        this.stop(name);
        
        console.log(`🔄 Запуск polling: ${name} (каждые ${intervalMs / 1000} сек)`);
        
        // Запускаем сразу если нужно
        if (runImmediately) {
            this.executePoll(name, callback);
        }
        
        // Устанавливаем интервал
        this.intervals[name] = setInterval(() => {
            this.executePoll(name, callback);
        }, intervalMs);
        
        this.lastUpdateTime[name] = Date.now();
    }
    
    /**
     * Выполнить одно обновление
     */
    async executePoll(name, callback) {
        // Проверяем паузу
        if (!this.canPoll()) {
            console.log(`⏸️ Polling ${name} пропущен (пауза)`);
            return;
        }
        
        // Если вкладка неактивна, пропускаем некоторые обновления
        if (!this.isUserActive && Math.random() > 0.3) {
            console.log(`⏸️ Polling ${name} пропущен (вкладка неактивна)`);
            return;
        }
        
        try {
            const startTime = Date.now();
            await callback();
            const duration = Date.now() - startTime;
            
            this.lastUpdateTime[name] = Date.now();
            console.log(`✅ Polling ${name} завершён (${duration}ms)`);
        } catch (error) {
            console.error(`❌ Ошибка polling ${name}:`, error);
        }
    }
    
    /**
     * Остановить polling
     */
    stop(name) {
        if (this.intervals[name]) {
            clearInterval(this.intervals[name]);
            delete this.intervals[name];
            console.log(`⏹️ Остановлен polling: ${name}`);
        }
    }
    
    /**
     * Остановить все polling
     */
    stopAll() {
        Object.keys(this.intervals).forEach(name => this.stop(name));
        console.log('⏹️ Все polling остановлены');
    }
    
    /**
     * Показать статус всех polling
     */
    status() {
        console.log('📊 Статус polling:');
        Object.keys(this.intervals).forEach(name => {
            const lastUpdate = this.lastUpdateTime[name];
            const ago = lastUpdate ? Math.round((Date.now() - lastUpdate) / 1000) : '?';
            console.log(`  • ${name}: активен (последнее обновление ${ago}s назад)`);
        });
    }
}

// Глобальный экземпляр
window.dataPoller = window.dataPoller || new DataPoller();

console.log('✅ DataPoller инициализирован');
