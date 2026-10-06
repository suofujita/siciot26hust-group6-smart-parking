import time

from RPLCD.i2c import CharLCD
from luma.core.error import DeviceNotFoundError
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

LCD_ADDR = 0x27
OLED_ADDR = 0x3C
SLOTS_PER_ZONE = 2
TOTAL_SLOTS = 4
REDRAW_EVERY = 3.0   # giây: vẽ lại LCD/OLED định kỳ để tự khỏi khi bị nhiễu / sụt nguồn


class LCDDisplay:
    """LCD ngoài cổng: chỉ hiển thị tổng số chỗ trống."""

    def __init__(self, addr=LCD_ADDR):
        self._addr = addr
        self._last = None
        self._last_draw = 0.0
        self._open()

    def _open(self):
        self.lcd = CharLCD("PCF8574", self._addr, cols=16, rows=2, charmap="A02")

    def show_total(self, free, total=TOTAL_SLOTS):
        now = time.time()
        # Số không đổi và mới vẽ gần đây thì bỏ qua (đỡ nhấp nháy)
        if (free, total) == self._last and now - self._last_draw < REDRAW_EVERY:
            return

        # LCD 16x2: mỗi dòng tối đa 16 ký tự, căn giữa cho dễ nhìn
        line1 = "TONG CHO TRONG"
        line2 = "DA HET CHO" if free == 0 else f"{free}/{total}"

        try:
            if (free, total) != self._last:
                self.lcd.clear()                       # chỉ xóa khi số đổi
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1.center(16))    # ghi đè đủ 16 ký tự mỗi dòng
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2.center(16))
            self._last = (free, total)
            self._last_draw = now
        except (OSError, ValueError):
            # Lỗi I2C (dây lỏng, nhiễu, LCD vừa mất nguồn): khởi tạo lại LCD,
            # lần cập nhật sau sẽ vẽ lại từ đầu. Không làm sập chương trình chính.
            try:
                self.lcd.close(clear=False)
            except Exception:
                pass
            time.sleep(0.2)
            try:
                self._open()
            except (OSError, ValueError):
                pass
            self._last = None

    def close(self):
        try:
            self.lcd.clear()
            self.lcd.close(clear=True)
        except (OSError, ValueError):
            pass                              # I2C đã chết: bỏ qua để các bước dọn dẹp sau vẫn chạy


class OLEDDisplay:
    """OLED trong bãi: 2 nửa màn hình, mỗi nửa là 1 khu (trái/phải) + mũi tên."""

    def __init__(self, addr=OLED_ADDR, width=128, height=64):
        self._addr = addr
        self.w, self.h = width, height
        self._last = None
        self._last_draw = 0.0
        self.device = None
        try:
            self._open()
        except (OSError, DeviceNotFoundError):
            print("OLED: chưa kết nối được, sẽ thử lại khi cập nhật")
        try:
            self.font_big = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except OSError:                       # không có font -> dùng font mặc định
            self.font_big = self.font_small = ImageFont.load_default()

    def _open(self):
        serial = i2c(port=1, address=self._addr)
        self.device = ssd1306(serial, width=self.w, height=self.h)

    def show_zones(self, left_free, right_free):
        now = time.time()
        # Số không đổi và mới vẽ gần đây thì bỏ qua
        if (left_free, right_free) == self._last and now - self._last_draw < REDRAW_EVERY:
            return

        try:
            if self.device is None:
                self._open()                   # lần trước lỗi I2C: mở lại màn hình
            mid = self.w // 2
            with canvas(self.device) as draw:
                draw.line((mid, 4, mid, self.h - 4), fill="white")   # vạch chia đôi
                self._draw_zone(draw, 0, mid, "KHU TRAI", left_free, "left")
                self._draw_zone(draw, mid, self.w, "KHU PHAI", right_free, "right")
            self._last = (left_free, right_free)
            self._last_draw = now
        except (OSError, DeviceNotFoundError):
            # Lỗi I2C (dây lỏng, nhiễu, mất nguồn thoáng qua): bỏ qua lần này,
            # lần cập nhật sau mở lại và vẽ lại từ đầu. Không làm sập chương trình chính.
            self.device = None
            self._last = None

    def _draw_zone(self, draw, x0, x1, title, free, direction):
        cx = (x0 + x1) // 2
        draw.text((x0 + 8, 2), title, font=self.font_small, fill="white")

        # Số chỗ trống (hoặc "X" nếu khu đã đầy)
        text = str(free) if free > 0 else "X"
        draw.text((cx - 8, 16), text, font=self.font_big, fill="white")

        # Mũi tên chỉ hướng, chỉ vẽ khi còn chỗ
        if free > 0:
            y = 54
            if direction == "left":
                draw.polygon([(cx - 14, y), (cx - 4, y - 6), (cx - 4, y + 6)], fill="white")
                draw.line((cx - 4, y, cx + 14, y), fill="white", width=2)
            else:
                draw.polygon([(cx + 14, y), (cx + 4, y - 6), (cx + 4, y + 6)], fill="white")
                draw.line((cx - 14, y, cx + 4, y), fill="white", width=2)
        else:
            draw.text((cx - 12, 48), "HET", font=self.font_small, fill="white")

    def clear(self):
        if self.device is None:
            return
        try:
            self.device.clear()
        except (OSError, DeviceNotFoundError):
            pass                              # I2C đã chết: bỏ qua để các bước dọn dẹp sau vẫn chạy


# ---------- Cập nhật từ database ----------
def get_free_counts(conn):
    """Trả về (left_free, right_free) từ bảng parking_slots."""
    rows = conn.execute(
        "SELECT zone_id, COUNT(*) AS n FROM parking_slots "
        "WHERE status = 'empty' GROUP BY zone_id"
    ).fetchall()
    counts = {r["zone_id"]: r["n"] for r in rows}
    return counts.get("left", 0), counts.get("right", 0)


def get_active_sessions(conn):
    """Số thẻ RFID đang ở trong bãi (đã quét vào, chưa quét ra)."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM parking_sessions WHERE status = 'active'"
    ).fetchone()
    return row["n"]


def refresh_displays(conn, lcd, oled):
    """Gọi khi quét thẻ vào/ra (cập nhật LCD) và định kỳ (cập nhật OLED theo cảm biến)."""
    left, right = get_free_counts(conn)                  # OLED: theo cảm biến từng khu
    free_total = max(TOTAL_SLOTS - get_active_sessions(conn), 0)   # LCD: tổng - số thẻ trong bãi
    lcd.show_total(free_total)
    oled.show_zones(left, right)
