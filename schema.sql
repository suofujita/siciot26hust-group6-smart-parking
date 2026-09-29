-- Bảng phiên gửi xe, theo dõi bằng RFID
CREATE TABLE IF NOT EXISTS parking_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfid_uid   TEXT NOT NULL,
    time_in    TEXT NOT NULL,
    time_out   TEXT,
    fee        INTEGER,
    status     TEXT NOT NULL CHECK (status IN ('active', 'completed'))
);

-- Ràng buộc: mỗi rfid_uid chỉ được có tối đa 1 session đang active tại một thời điểm
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_session
ON parking_sessions(rfid_uid)
WHERE status = 'active';

-- Index phụ trợ, tăng tốc tra cứu lịch sử theo rfid_uid
CREATE INDEX IF NOT EXISTS idx_sessions_rfid_uid
ON parking_sessions(rfid_uid);

-- Bảng trạng thái vật lý từng chỗ đỗ, theo dõi bằng IR sensor
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id      TEXT PRIMARY KEY,
    slot_code   TEXT NOT NULL UNIQUE,
    zone_id         TEXT NOT NULL CHECK (zone_id IN ('left', 'right')),
    status     TEXT NOT NULL CHECK (status IN ('occupied', 'empty')),
    updated_at   TEXT
);

-- Seed sẵn 4 chỗ cố định, không đổi qua thời gian sống của hệ thống
INSERT OR IGNORE INTO parking_slots (slot_id, slot_code, zone_id, status, updated_at) VALUES
    ('1', 'A1', 'left', 'empty', NULL),
    ('2', 'A2', 'left', 'empty', NULL),
    ('3', 'B1', 'right', 'empty', NULL),
    ('4', 'B2', 'right', 'empty', NULL);

