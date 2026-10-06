import time
from datetime import datetime

from gpiozero import DistanceSensor

FMT = "%Y-%m-%d %H:%M:%S"

# (slot_id, zone, TRIG, ECHO) — số chân là GPIO (BCM). slot_id là TEXT trong parking_slots.
# TODO: sửa theo chân bạn đã nối và ô mà mỗi cảm biến giám sát.
SENSOR_CONFIG = [
    ("1", "left",  5,  6),    # A1
    ("3", "right", 21, 26),   # B1
]

# TODO: đo thực tế bằng `python -m hardware.sensors` rồi chỉnh 2 ngưỡng này
OCCUPIED_BELOW_CM = 8   # nhỏ hơn mức này -> có xe
FREE_ABOVE_CM = 9       # lớn hơn mức này -> trống (ở giữa: giữ trạng thái cũ)
CONFIRM_SECONDS = 1.0     # trạng thái mới phải giữ ổn định ngần này giây mới được chấp nhận
MAX_DISTANCE_M = 1.0


class SlotSensor:
    def __init__(self, slot_id, zone, trig, echo):
        self.slot_id, self.zone = slot_id, zone
        self.dev = DistanceSensor(echo=echo, trigger=trig, max_distance=MAX_DISTANCE_M)
        self.status = None          # trạng thái đã xác nhận: "occupied" / "empty"
        self._pending = None        # trạng thái mới đang chờ xác nhận
        self._since = 0.0

    def distance_cm(self):
        return self.dev.distance * 100

    def read(self):
        """Trả về trạng thái mới nếu vừa đổi (đã qua lọc), ngược lại trả None."""
        d = self.distance_cm()
        if d < OCCUPIED_BELOW_CM:
            seen = "occupied"
        elif d > FREE_ABOVE_CM:
            seen = "empty"
        else:
            return None             # vùng đệm: giữ nguyên

        now = time.monotonic()
        if seen == self.status:
            self._pending = None
            return None
        if seen != self._pending:   # vừa thấy trạng thái khác -> bắt đầu đếm giờ
            self._pending, self._since = seen, now
            return None
        if now - self._since >= CONFIRM_SECONDS:
            self.status, self._pending = seen, None
            return seen
        return None


def create_sensors():
    """Tạo các cảm biến. Gọi SAU khi đã tạo đầu đọc RFID (tránh xung đột GPIO)."""
    return [SlotSensor(*cfg) for cfg in SENSOR_CONFIG]


def save_status(conn, slot_id, status):
    conn.execute(
        "UPDATE parking_slots SET status = ?, updated_at = ? WHERE slot_id = ?",
        (status, datetime.now().strftime(FMT), slot_id),
    )
    conn.commit()


def poll(conn, sensors):
    """Gọi trong vòng lặp chính. Trả về True nếu có ô đổi trạng thái."""
    changed = False
    for s in sensors:
        new = s.read()
        if new:
            save_status(conn, s.slot_id, new)
            print(f"SLOT {s.slot_id} ({s.zone}): {new}")
            changed = True
    return changed


if __name__ == "__main__":
    sensors = create_sensors()
    print("Đo khoảng cách (Ctrl+C để thoát)")
    try:
        while True:
            print({s.slot_id: round(s.distance_cm()) for s in sensors}, "cm")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass