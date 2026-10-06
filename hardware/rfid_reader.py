import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522, MFRC522
import database
database.init_db()
import services
from hardware.display import LCDDisplay, OLEDDisplay, refresh_displays

DEBOUNCE = 3.0        # giây, xử lý lỡ tay quẹt nhiều lần
REFRESH_EVERY = 1.0   # giây, cập nhật định kỳ (chủ yếu cho OLED theo cảm biến)


class Reader(SimpleMFRC522):
    def __init__(self, device, pin_rst):
        self.READER = MFRC522(device=device, pin_rst=pin_rst)


# pin_rst dùng số chân VẬT LÝ (BOARD) của thư viện mfrc522
entry_reader = Reader(device=0, pin_rst=22)   # CE0, chân vật lý 22 = GPIO25
exit_reader = Reader(device=1, pin_rst=18)    # CE1, chân vật lý 18 = GPIO24

# Import servo SAU khi đã tạo đầu đọc RFID (tránh xung đột gpiozero với RPi.GPIO)
from hardware.servos import gate_in, gate_out
from hardware.sensors import create_sensors, poll

# Màn hình: LCD (tổng chỗ trống = tổng - số thẻ trong bãi), OLED (từng khu theo cảm biến)
conn = database.get_connection()
lcd = LCDDisplay()
oled = OLEDDisplay()
slot_sensors = create_sensors()
refresh_displays(conn, lcd, oled)     # hiện ngay khi vừa cấp nguồn
last_refresh = time.time()

last_entry = (None, 0)   # (uid, thời điểm)
last_exit = (None, 0)

try:
    print("Waiting for cards...")
    while True:
        now = time.time()

        # Cổng vào: chỉ đọc thẻ khi barie không bận
        if not gate_in.is_busy:
            rfid_uid = entry_reader.read_id_no_block()
            if rfid_uid and not (rfid_uid == last_entry[0] and now - last_entry[1] < DEBOUNCE):
                last_entry = (rfid_uid, now)
                ok, msg = services.handle_entry(rfid_uid)   # handle_entry trả về (ok, msg)
                if ok:
                    gate_in.open_gate()
                    refresh_displays(conn, lcd, oled)  # cập nhật LCD ngay
                    last_refresh = now
                    print("ENTRY OK:", msg)
                else:
                    print("ENTRY REJECTED:", msg)

        # Cổng ra
        if not gate_out.is_busy:
            rfid_uid = exit_reader.read_id_no_block()
            if rfid_uid and not (rfid_uid == last_exit[0] and now - last_exit[1] < DEBOUNCE):
                last_exit = (rfid_uid, now)
                ok, msg, fee = services.handle_exit(rfid_uid)    # giả định cũng trả về (ok, msg)
                if ok:
                    gate_out.open_gate()
                    refresh_displays(conn, lcd, oled)  # cập nhật LCD ngay
                    last_refresh = now
                    print("EXIT OK:", msg)
                else:
                    print("EXIT REJECTED:", msg)

        if poll(conn, slot_sensors):
            refresh_displays(conn, lcd, oled)
            last_refresh = now

        # Cập nhật định kỳ (bắt kịp thay đổi của cảm biến cho OLED)
        if now - last_refresh >= REFRESH_EVERY:
            refresh_displays(conn, lcd, oled)
            last_refresh = now

        time.sleep(0.1)
finally:
    for s in slot_sensors:
        s.dev.close()
    gate_in.close()
    gate_out.close()
    lcd.close()
    oled.clear()
    conn.close()
    GPIO.cleanup()