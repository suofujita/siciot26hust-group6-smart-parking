"""hardware/display.py
LCD 16x2 I2C (ngoài cổng)  -> tổng số chỗ trống
OLED SSD1306 I2C (trong bãi) -> số chỗ trống từng khu + mũi tên chỉ hướng

Cài thư viện:
    pip install RPLCD luma.oled smbus2 pillow
Bật I2C:  sudo raspi-config -> Interface Options -> I2C
Kiểm tra địa chỉ:  i2cdetect -y 1   (LCD thường 0x27 hoặc 0x3F, OLED thường 0x3C)
"""
from RPLCD.i2c import CharLCD
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

LCD_ADDR = 0x27
OLED_ADDR = 0x3C
SLOTS_PER_ZONE = 2
TOTAL_SLOTS = 4


class LCDDisplay:
    """LCD ngoài cổng: chỉ hiển thị tổng số chỗ trống."""

    def __init__(self, addr=LCD_ADDR):
        self.lcd = CharLCD("PCF8574", addr, cols=16, rows=2, charmap="A02")
        self._last = None

    def show_total(self, free, total=TOTAL_SLOTS):
        if (free, total) == self._last:      # không đổi thì khỏi ghi lại -> đỡ nhấp nháy
            return
        self._last = (free, total)

        self.lcd.clear()
        self.lcd.write_string("BAI XE THONG MINH"[:16])
        self.lcd.cursor_pos = (1, 0)
        if free == 0:
            self.lcd.write_string("DA HET CHO")
        else:
            self.lcd.write_string(f"CON TRONG: {free}/{total}")

    def close(self):
        self.lcd.clear()
        self.lcd.close(clear=True)


class OLEDDisplay:
    """OLED trong bãi: 2 nửa màn hình, mỗi nửa là 1 khu (trái/phải) + mũi tên."""

    def __init__(self, addr=OLED_ADDR, width=128, height=64):
        serial = i2c(port=1, address=addr)
        self.device = ssd1306(serial, width=width, height=height)
        self.w, self.h = width, height
        self._last = None
        try:
            self.font_big = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except OSError:                       # không có font -> dùng font mặc định
            self.font_big = self.font_small = ImageFont.load_default()

    def show_zones(self, left_free, right_free):
        if (left_free, right_free) == self._last:
            return
        self._last = (left_free, right_free)

        mid = self.w // 2
        with canvas(self.device) as draw:
            draw.line((mid, 4, mid, self.h - 4), fill="white")   # vạch chia đôi
            self._draw_zone(draw, 0, mid, "KHU TRAI", left_free, "left")
            self._draw_zone(draw, mid, self.w, "KHU PHAI", right_free, "right")

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
        self.device.clear()


# ---------- Cập nhật từ database ----------
def get_free_counts(conn):
    """Trả về (left_free, right_free) từ bảng slots."""
    rows = conn.execute(
        "SELECT zone_id, COUNT(*) AS n FROM slots "
        "WHERE status = 'empty' GROUP BY zone_id"
    ).fetchall()
    counts = {r["zone_id"]: r["n"] for r in rows}
    return counts.get("left", 0), counts.get("right", 0)


def refresh_displays(conn, lcd, oled):
    """Gọi hàm này mỗi khi trạng thái slot thay đổi (hoặc trong vòng lặp polling)."""
    left, right = get_free_counts(conn)
    lcd.show_total(left + right)
    oled.show_zones(left, right)


# ---------- Chạy thử độc lập ----------
if __name__ == "__main__":
    import time

    lcd = LCDDisplay()
    #oled = OLEDDisplay()
    try:
        for left, right in [(2, 2), (1, 2), (0, 2), (0, 1), (0, 0)]:
            lcd.show_total(left + right)
           # oled.show_zones(left, right)
            time.sleep(2)
    finally:
        lcd.close()
       # oled.clear()