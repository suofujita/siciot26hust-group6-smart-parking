from threading import Lock, Thread
from time import sleep

from gpiozero import AngularServo

PIN_GATE_IN = 12    # barie cổng vào  (chân vật lý 32)
PIN_GATE_OUT = 13   # barie cổng ra   (chân vật lý 33)

ANGLE_CLOSED = 0
ANGLE_OPEN = 90
MOVE_SECONDS = 0.6   # thời gian chờ servo quay xong
OPEN_SECONDS = 5     # barie giữ mở bao lâu


class Barrier:
    def __init__(self, pin, name="barrier"):
        self.name = name
        self._busy = Lock()
        self._servo = AngularServo(
            pin,
            initial_angle=None,          # không giật servo lúc khởi tạo
            min_angle=0,
            max_angle=180,
            min_pulse_width=0.0005,      # 0.5 ms
            max_pulse_width=0.0025,      # 2.5 ms (thu hẹp nếu servo kêu rít ở cuối góc)
        )
        self._go(ANGLE_CLOSED, release=True)   # đưa về vị trí đóng khi khởi động

    def _go(self, angle, release=False):
        self._servo.angle = angle
        sleep(MOVE_SECONDS)
        if release:
            self._servo.detach()   # tắt xung: hết rung, đỡ nóng, đỡ hút dòng

    def _cycle(self):
        try:
            self._go(ANGLE_OPEN)           # giữ xung khi mở để barie không sụp
            sleep(OPEN_SECONDS)
            self._go(ANGLE_CLOSED, release=True)
        finally:
            self._busy.release()

    def open_gate(self):
        """Mở barie rồi tự đóng. Không chặn (chạy thread riêng), nên không làm
        đứng vòng round-robin đọc RFID. Gọi lại khi đang mở thì bị bỏ qua."""
        if self._busy.acquire(blocking=False):
            Thread(target=self._cycle, daemon=True).start()
            return True
        return False

    def close(self):
        self._servo.close()


gate_in = Barrier(PIN_GATE_IN, "gate_in")
gate_out = Barrier(PIN_GATE_OUT, "gate_out")


if __name__ == "__main__":
    # Test nhanh: python3 servo.py
    gate_in.open_gate()
    sleep(0.2)
    gate_out.open_gate()
    sleep(OPEN_SECONDS + 2)