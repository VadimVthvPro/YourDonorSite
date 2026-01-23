-- Создание таблицы истории донаций
CREATE TABLE IF NOT EXISTS donation_history (
    id SERIAL PRIMARY KEY,
    donor_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medical_center_id INT NOT NULL REFERENCES medical_centers(id) ON DELETE CASCADE,
    donation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    blood_type VARCHAR(5) NOT NULL,
    volume_ml INT DEFAULT 450,
    status VARCHAR(50) DEFAULT 'completed',
    notes TEXT,
    response_id INT REFERENCES donation_responses(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donation_history_donor_id ON donation_history(donor_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_medical_center_id ON donation_history(medical_center_id);
CREATE INDEX IF NOT EXISTS idx_donation_history_donation_date ON donation_history(donation_date);

COMMENT ON TABLE donation_history IS 'История сдачи крови донорами';
COMMENT ON COLUMN donation_history.donor_id IS 'ID донора';
COMMENT ON COLUMN donation_history.medical_center_id IS 'ID медицинского центра';
COMMENT ON COLUMN donation_history.donation_date IS 'Дата сдачи крови';
COMMENT ON COLUMN donation_history.blood_type IS 'Группа крови';
COMMENT ON COLUMN donation_history.volume_ml IS 'Объём сданной крови в мл';
COMMENT ON COLUMN donation_history.status IS 'Статус донации';
COMMENT ON COLUMN donation_history.notes IS 'Заметки';
COMMENT ON COLUMN donation_history.response_id IS 'ID отклика, связанного с донацией';
