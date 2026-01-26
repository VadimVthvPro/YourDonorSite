#!/bin/bash
echo "========================================="
echo "🎨 ПОЛНОЕ ИСПРАВЛЕНИЕ МОБИЛЬНОГО ДИЗАЙНА"
echo "========================================="

# Список всех проблем мобильного дизайна:
# 1. Противопоказания - вертикальные → горизонтальные
# 2. Таблица интервалов - не влезает
# 3. Формы регистрации - плохо масштабируются
# 4. Навигация - слишком плотная
# 5. Карточки - обрезаются

echo ""
echo "Создаю полностью адаптивный CSS..."
echo ""

cat > mobile_fixes.css << 'EOF'
/* ============================================
   МОБИЛЬНАЯ АДАПТАЦИЯ - ГЛОБАЛЬНЫЕ ИСПРАВЛЕНИЯ
   ============================================ */

/* Базовые настройки для мобильных */
@media (max-width: 768px) {
    /* Отступы контейнеров */
    .container {
        padding-left: 16px !important;
        padding-right: 16px !important;
    }
    
    /* Секции */
    .section {
        padding: 40px 0 !important;
    }
    
    /* Заголовки */
    .section-title {
        font-size: 1.75rem !important;
        line-height: 1.3 !important;
    }
    
    .section-subtitle {
        font-size: 0.95rem !important;
    }
}

/* ============================================
   ПРОТИВОПОКАЗАНИЯ - ГОРИЗОНТАЛЬНЫЕ ПЛАШКИ
   ============================================ */
@media (max-width: 768px) {
    /* Сетка становится одноколоночной */
    .contra-grid {
        grid-template-columns: 1fr !important;
        gap: 16px !important;
    }
    
    /* Карточки становятся горизонтальными */
    .contra-card {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-start !important;
        padding: 16px !important;
        min-height: auto !important;
    }
    
    /* Хедер карточки - горизонтально */
    .contra-card-header {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 0 !important;
        flex-shrink: 0 !important;
        width: auto !important;
    }
    
    /* Иконка компактнее */
    .contra-icon-wrapper {
        width: 40px !important;
        height: 40px !important;
        flex-shrink: 0 !important;
    }
    
    .contra-icon {
        width: 20px !important;
        height: 20px !important;
    }
    
    /* Текст заголовка */
    .contra-header-text {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
    }
    
    .contra-title {
        font-size: 0.95rem !important;
        margin: 0 !important;
    }
    
    .contra-subtitle {
        font-size: 0.75rem !important;
    }
    
    /* Список - справа от заголовка */
    .contra-list {
        padding: 0 !important;
        margin: 0 0 0 12px !important;
        flex: 1 !important;
    }
    
    .contra-list li {
        font-size: 0.85rem !important;
        padding: 6px 0 !important;
    }
    
    .period-badge {
        font-size: 0.7rem !important;
        padding: 2px 6px !important;
    }
    
    /* Убираем hover на мобильных */
    .contra-card:hover {
        transform: none !important;
    }
}

/* Очень маленькие экраны */
@media (max-width: 480px) {
    /* Возвращаем вертикальную раскладку на очень маленьких */
    .contra-card {
        flex-direction: column !important;
    }
    
    .contra-card-header {
        width: 100% !important;
    }
    
    .contra-list {
        margin: 12px 0 0 0 !important;
        width: 100% !important;
    }
}

/* ============================================
   ТАБЛИЦА ИНТЕРВАЛОВ - ГОРИЗОНТАЛЬНЫЙ СКРОЛЛ
   ============================================ */
@media (max-width: 768px) {
    .intervals-table {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        border-radius: 12px !important;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.1) !important;
    }
    
    .intervals-table table {
        min-width: 600px !important;
        font-size: 0.85rem !important;
    }
    
    .intervals-table th,
    .intervals-table td {
        padding: 10px 8px !important;
        white-space: nowrap !important;
    }
    
    /* Индикатор прокрутки */
    .intervals-table::after {
        content: '← Прокрутите →';
        position: sticky;
        right: 8px;
        bottom: 8px;
        background: rgba(220, 38, 38, 0.9);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        pointer-events: none;
        opacity: 0.9;
        animation: pulse 2s infinite;
        z-index: 10;
        float: right;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.9; }
        50% { opacity: 1; }
    }
}

/* ============================================
   ФОРМЫ РЕГИСТРАЦИИ/ВХОДА - АДАПТАЦИЯ
   ============================================ */
@media (max-width: 768px) {
    .auth-container {
        padding: 20px 16px !important;
        margin: 20px 16px !important;
        max-width: 100% !important;
    }
    
    .auth-form {
        padding: 0 !important;
    }
    
    .form-group {
        margin-bottom: 20px !important;
    }
    
    .form-group label {
        font-size: 0.9rem !important;
        margin-bottom: 6px !important;
    }
    
    .form-control {
        font-size: 16px !important; /* Предотвращает зум на iOS */
        padding: 12px 14px !important;
        height: 48px !important;
    }
    
    textarea.form-control {
        height: auto !important;
        min-height: 100px !important;
    }
    
    /* Кнопки */
    .btn {
        padding: 12px 20px !important;
        font-size: 0.95rem !important;
        min-height: 48px !important; /* Удобно для тапа */
    }
    
    .btn-block {
        width: 100% !important;
        display: block !important;
    }
}

/* ============================================
   НАВИГАЦИЯ - МОБИЛЬНАЯ
   ============================================ */
@media (max-width: 768px) {
    .nav-menu {
        display: none !important; /* Скрываем на мобильных */
    }
    
    .nav-buttons {
        display: flex !important;
        gap: 8px !important;
    }
    
    .nav-buttons .btn {
        padding: 8px 12px !important;
        font-size: 0.85rem !important;
    }
    
    .mobile-menu-btn {
        display: block !important;
        width: 40px !important;
        height: 40px !important;
        padding: 8px !important;
    }
}

/* ============================================
   КАРТОЧКИ - АДАПТАЦИЯ
   ============================================ */
@media (max-width: 768px) {
    .card,
    .about-card,
    .reason-card,
    .right-card {
        margin-bottom: 16px !important;
        padding: 16px !important;
    }
    
    /* Грид-раскладки становятся одноколоночными */
    .about-grid,
    .reasons-grid,
    .rights-grid {
        grid-template-columns: 1fr !important;
        gap: 16px !important;
    }
}

/* ============================================
   ДАШБОРДЫ ДОНОРА/МЕДЦЕНТРА
   ============================================ */
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr !important;
        gap: 16px !important;
    }
    
    .stat-card {
        padding: 16px !important;
    }
    
    .stat-value {
        font-size: 1.75rem !important;
    }
    
    .stat-label {
        font-size: 0.85rem !important;
    }
}

/* ============================================
   МОДАЛЬНЫЕ ОКНА
   ============================================ */
@media (max-width: 768px) {
    .modal-content {
        margin: 16px !important;
        max-width: calc(100% - 32px) !important;
        max-height: calc(100vh - 32px) !important;
        overflow-y: auto !important;
    }
    
    .modal-header {
        padding: 16px !important;
    }
    
    .modal-body {
        padding: 16px !important;
    }
    
    .modal-footer {
        padding: 16px !important;
        flex-direction: column !important;
        gap: 8px !important;
    }
    
    .modal-footer .btn {
        width: 100% !important;
    }
}

/* ============================================
   HERO-СЕКЦИЯ
   ============================================ */
@media (max-width: 768px) {
    .hero {
        min-height: auto !important;
        padding: 60px 0 40px !important;
    }
    
    .hero-content {
        text-align: center !important;
        padding: 0 16px !important;
    }
    
    .hero-title {
        font-size: 1.75rem !important;
        line-height: 1.3 !important;
    }
    
    .hero-subtitle {
        font-size: 0.95rem !important;
    }
    
    .hero-buttons {
        flex-direction: column !important;
        gap: 12px !important;
    }
    
    .hero-card {
        display: none !important; /* Скрываем декоративную карточку */
    }
}

/* ============================================
   МЕССЕНДЖЕР
   ============================================ */
@media (max-width: 768px) {
    .messenger-container {
        height: calc(100vh - 60px) !important;
        border-radius: 0 !important;
    }
    
    .messenger-sidebar {
        width: 100% !important;
    }
    
    .messenger-main {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
        width: 100% !important;
        height: 100% !important;
        z-index: 10 !important;
    }
    
    .conversation-header .back-btn {
        display: flex !important;
    }
}

/* ============================================
   УТИЛИТЫ
   ============================================ */
@media (max-width: 768px) {
    .hide-mobile {
        display: none !important;
    }
    
    .show-mobile {
        display: block !important;
    }
    
    .text-center-mobile {
        text-align: center !important;
    }
}
EOF

echo "✅ CSS исправления созданы"
echo ""

