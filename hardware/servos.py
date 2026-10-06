from threading import Lock, Thread
from time import sleep

from gpiozero import AngularServo

PIN_GATE_IN = 12    # barie cổng vào  (chân vật lý 32)
PIN_GATE_OUT = 13   # barie cổng ra   (chân vật lý 33)

ANGLE_CLOSED = 0
ANGLE_OPEN = 90
OPEN_SECONDS = 2     # barie giữ mở bao lâu

# Chuyển động mượt: quay từng bước nhỏ thay vì nhảy thẳng tới góc đích
STEP_DEG = 3          # mỗi bước quay 3° (nhỏ hơn = mượt hơn, chậm hơn)
STEP_DELAY = 0.015    # giây giữa các bước (90° ≈ 30 bước ≈ 0.45 s)
SETTLE_SECONDS = 0.25 # chờ servo ổn định sau khi tới đích


class Barrier:
    # Chỉ cho 1 servo chuyển động tại một thời điểm -> tránh 2 servo cùng
    # khởi động một lúc làm dòng tăng vọt, sụt nguồn.
    _move_lock = Lock()

    def __init__(self, pin, name="barrier"):
        self.name = name
        self._busy = Lock()
        self._angle = None           # góc hiện tại (chưa biết lúc khởi động)
        self._servo = AngularServo(
            pin,
            initial_angle=None,          # không giật servo lúc khởi tạo
            min_angle=0,
            max_angle=180,
            min_pulse_width=0.0005,      # 0.5 ms
            max_pulse_width=0.0025,      # 2.5 ms (thu hẹp nếu servo kêu rít ở cuối góc)
        )
        self._go(ANGLE_CLOSED, release=True)   # đưa về vị trí đóng khi khởi động

    def _go(self, target, release=False):
        """Quay tới góc target theo từng bước nhỏ cho mượt."""
        with Barrier._move_lock:
            if self._angle is None:
                # Chưa biết đang ở góc nào -> đưa thẳng về góc đích
                self._servo.angle = target
            else:
                angle = self._angle
                step = STEP_DEG if target > angle else -STEP_DEG
                while abs(target - angle) > STEP_DEG:
                    angle += step
                    self._servo.angle = angle
                    sleep(STEP_DELAY)
                self._servo.angle = target
            self._angle = target
            sleep(SETTLE_SECONDS)
            if release:
                self._servo.detach()   # tắt xung: hết rung, đỡ nóng, đỡ hút dòng

    def _cycle(self):
        try:
            self._go(ANGLE_OPEN)           # giữ xung khi mở để barie không sụp
            sleep(OPEN_SECONDS)
            self._go(ANGLE_CLOSED, release=True)
        finally:
            self._busy.release()

    @property
    def is_busy(self):
        """True khi barie đang trong chu trình mở/đóng."""
        return self._busy.locked()

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