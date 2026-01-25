-- ============================================
-- Твой Донор - База данных веб-платформы
-- PostgreSQL
-- ============================================

-- ============================================
-- Справочник областей
-- ============================================
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Заполняем области Беларуси
INSERT INTO regions (name) VALUES
    ('город Минск'),
    ('Минская область'),
    ('Брестская область'),
    ('Гомельская область'),
    ('Гродненская область'),
    ('Витебская область'),
    ('Могилёвская область')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- Справочник районов
-- ============================================
CREATE TABLE IF NOT EXISTS districts (
    id SERIAL PRIMARY KEY,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_id, name)
);

-- город Минск (region_id = 1)
INSERT INTO districts (region_id, name) VALUES
    (1, 'Центральный район'),
    (1, 'Советский район'),
    (1, 'Московский район'),
    (1, 'Октябрьский район'),
    (1, 'Фрунзенский район'),
    (1, 'Первомайский район'),
    (1, 'Партизанский район'),
    (1, 'Заводской район'),
    (1, 'Ленинский район')
ON CONFLICT DO NOTHING;

-- Минская область (region_id = 2)
INSERT INTO districts (region_id, name) VALUES
    (2, 'Борисовский район'),
    (2, 'Солигорский район'),
    (2, 'Молодечненский район'),
    (2, 'Слуцкий район'),
    (2, 'Жодинский район'),
    (2, 'Минский район')
ON CONFLICT DO NOTHING;

-- Брестская область (region_id = 3)
INSERT INTO districts (region_id, name) VALUES
    (3, 'город Брест'),
    (3, 'Барановичский район'),
    (3, 'Пинский район'),
    (3, 'Кобринский район')
ON CONFLICT DO NOTHING;

-- Гомельская область (region_id = 4)
INSERT INTO districts (region_id, name) VALUES
    (4, 'город Гомель'),
    (4, 'Мозырский район'),
    (4, 'Жлобинский район'),
    (4, 'Речицкий район'),
    (4, 'Светлогорский район')
ON CONFLICT DO NOTHING;

-- Гродненская область (region_id = 5)
INSERT INTO districts (region_id, name) VALUES
    (5, 'город Гродно'),
    (5, 'Лидский район'),
    (5, 'Волковысский район'),
    (5, 'Слонимский район')
ON CONFLICT DO NOTHING;

-- Витебская область (region_id = 6)
INSERT INTO districts (region_id, name) VALUES
    (6, 'город Витебск'),
    (6, 'Оршанский район'),
    (6, 'Полоцкий район'),
    (6, 'Новополоцкий район')
ON CONFLICT DO NOTHING;

-- Могилёвская область (region_id = 7)
INSERT INTO districts (region_id, name) VALUES
    (7, 'город Могилёв'),
    (7, 'Бобруйский район'),
    (7, 'Горецкий район'),
    (7, 'Кричевский район')
ON CONFLICT DO NOTHING;

-- ============================================
-- Медицинские центры
-- ============================================
CREATE TABLE IF NOT EXISTS medical_centers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    district_id INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    address VARCHAR(300),
    phone VARCHAR(50),
    email VARCHAR(100),
    is_blood_center BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    master_password VARCHAR(100) DEFAULT 'doctor2024',
    approval_status VARCHAR(20) DEFAULT 'approved',
    created_by_telegram_id BIGINT,
    approved_by_telegram_id BIGINT,
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mc_district ON medical_centers(district_id);
CREATE INDEX IF NOT EXISTS idx_mc_active ON medical_centers(is_active);
CREATE INDEX IF NOT EXISTS idx_mc_approval_status ON medical_centers(approval_status);

-- ============================================
-- Потребность в крови (Донорский светофор)
-- ============================================
CREATE TABLE IF NOT EXISTS blood_needs (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    blood_type VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'normal',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(medical_center_id, blood_type)
);

CREATE INDEX IF NOT EXISTS idx_bn_mc ON blood_needs(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_bn_status ON blood_needs(status);

-- ============================================
-- Пользователи (Доноры)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    birth_year INTEGER NOT NULL,
    blood_type VARCHAR(10) NOT NULL,
    
    region_id INTEGER REFERENCES regions(id),
    district_id INTEGER REFERENCES districts(id),
    city VARCHAR(100),
    medical_center_id INTEGER REFERENCES medical_centers(id),
    
    phone VARCHAR(50),
    email VARCHAR(100),
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(100),
    password_hash VARCHAR(255),
    
    last_donation_date DATE,
    total_donations INTEGER DEFAULT 0,
    donated_count INTEGER DEFAULT 0,
    is_honorary_donor BOOLEAN DEFAULT FALSE,
    last_response_date TIMESTAMP,
    
    notify_urgent BOOLEAN DEFAULT TRUE,
    notify_low BOOLEAN DEFAULT TRUE,
    
    is_active BOOLEAN DEFAULT TRUE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(full_name, birth_year, medical_center_id)
);

CREATE INDEX IF NOT EXISTS idx_users_blood_type ON users(blood_type);
CREATE INDEX IF NOT EXISTS idx_users_mc ON users(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_users_district ON users(district_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);

-- ============================================
-- Запросы на донацию (blood_requests)
-- ============================================
CREATE TABLE IF NOT EXISTS blood_requests (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    blood_type VARCHAR(10) NOT NULL,
    urgency VARCHAR(20) NOT NULL DEFAULT 'normal',
    needed_amount INTEGER DEFAULT 1,
    description TEXT,
    contact_info VARCHAR(300),
    target_district_id INTEGER REFERENCES districts(id),
    source VARCHAR(50) DEFAULT 'web',
    
    valid_until TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    responses_count INTEGER DEFAULT 0,
    donor_count INTEGER DEFAULT 0,
    
    telegram_sent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_br_mc ON blood_requests(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_br_status ON blood_requests(status);
CREATE INDEX IF NOT EXISTS idx_br_blood_type ON blood_requests(blood_type);
CREATE INDEX IF NOT EXISTS idx_br_source ON blood_requests(source);

-- Создаём VIEW donation_requests для обратной совместимости
CREATE OR REPLACE VIEW donation_requests AS SELECT * FROM blood_requests;

-- ============================================
-- Отклики доноров
-- ============================================
CREATE TABLE IF NOT EXISTS donation_responses (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id),
    
    status VARCHAR(20) DEFAULT 'pending',
    planned_date DATE,
    planned_time TIME,
    hidden BOOLEAN DEFAULT FALSE,
    
    actual_donation_date TIMESTAMP,
    donation_completed BOOLEAN DEFAULT FALSE,
    
    donor_comment TEXT,
    medcenter_comment TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(request_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_resp_request ON donation_responses(request_id);
CREATE INDEX IF NOT EXISTS idx_resp_user ON donation_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_resp_status ON donation_responses(status);

-- ============================================
-- Диалоги (Conversations)
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    subject VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, medical_center_id)
);

CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_mc ON conversations(medical_center_id);

-- ============================================
-- Сообщения/консультации
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    from_medcenter_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    to_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    to_medcenter_id INTEGER REFERENCES medical_centers(id) ON DELETE SET NULL,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    
    subject VARCHAR(200),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_msg_to_user ON messages(to_user_id);
CREATE INDEX IF NOT EXISTS idx_msg_to_mc ON messages(to_medcenter_id);
CREATE INDEX IF NOT EXISTS idx_msg_conversation ON messages(conversation_id);

-- ============================================
-- Сообщения в чате (Chat Messages)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER,
    sender_role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_conv ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_sender ON chat_messages(sender_id);

-- ============================================
-- Шаблоны сообщений
-- ============================================
CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_mc ON message_templates(medical_center_id);

-- ============================================
-- История донаций
-- ============================================
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    donation_date DATE NOT NULL,
    blood_center_id INTEGER REFERENCES medical_centers(id),
    donation_type VARCHAR(50),
    volume_ml INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donation_history_user ON donation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_date ON donation_history(donation_date);

-- ============================================
-- Администраторы
-- ============================================
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(100),
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'super_admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_telegram ON admin_users(telegram_id);

-- ============================================
-- Коды привязки Telegram
-- ============================================
CREATE TABLE IF NOT EXISTS telegram_link_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(10) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_tg_codes_user ON telegram_link_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_tg_codes_code ON telegram_link_codes(code);

-- ============================================
-- Сессии
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INTEGER REFERENCES medical_centers(id) ON DELETE CASCADE,
    
    session_token VARCHAR(256) NOT NULL UNIQUE,
    user_type VARCHAR(20) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sess_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sess_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sess_mc ON user_sessions(medical_center_id);

-- ============================================
-- Тестовые медцентры
-- ============================================
INSERT INTO medical_centers (name, district_id, address, email, is_blood_center) VALUES
    ('Республиканский центр трансфузиологии', 1, 'ул. Долгиновский тракт, 160', 'rcpt@mail.by', TRUE),
    ('Городская станция переливания крови', 1, 'ул. Уральская, 5', 'gspc@mail.by', TRUE),
    ('1-я городская клиническая больница', 1, 'пр. Независимости, 64', 'gkb1@mail.by', FALSE),
    ('Минская областная клиническая больница', 3, 'ул. Жуковского, 1', 'mokb@mail.by', FALSE),
    ('Брестская областная станция переливания крови', 15, 'г. Брест, ул. Мицкевича, 21', 'brest-blood@mail.by', TRUE),
    ('Гомельская областная станция переливания крови', 19, 'г. Гомель, ул. Пролетарская, 11', 'gomel-blood@mail.by', TRUE),
    ('Гродненская областная станция переливания крови', 24, 'г. Гродно, ул. Ожешко, 9', 'grodno-blood@mail.by', TRUE),
    ('Витебская областная станция переливания крови', 28, 'г. Витебск, ул. Чкалова, 14В', 'vitebsk-blood@mail.by', TRUE),
    ('Могилёвская областная станция переливания крови', 32, 'г. Могилёв, ул. Чехова, 2', 'mogilev-blood@mail.by', TRUE)
ON CONFLICT DO NOTHING;

-- Инициализируем светофор для первого медцентра
INSERT INTO blood_needs (medical_center_id, blood_type, status) VALUES
    (1, 'O+', 'normal'),
    (1, 'O-', 'low'),
    (1, 'A+', 'normal'),
    (1, 'A-', 'critical'),
    (1, 'B+', 'normal'),
    (1, 'B-', 'low'),
    (1, 'AB+', 'normal'),
    (1, 'AB-', 'normal')
ON CONFLICT DO NOTHING;

SELECT 'База данных Твой Донор создана!' as message;
